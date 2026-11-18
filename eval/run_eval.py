#!/usr/bin/env python3
"""
Evaluation Runner for Logistics Automation extraction pipelines.
Evaluates Gemini vs Regex extraction on synthetic/real invoice datasets.
Measures per-field accuracy (Wilson 95% CI), document-level accuracy, and latency.
"""

import argparse
import hashlib
import json
import math
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add paths to enable imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")

if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if "/app" not in sys.path and os.path.exists("/app"):
    sys.path.insert(0, "/app")

import scoring
from app import ocr, nlp


def compute_p50(vals: List[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return round(s[mid], 4)
    return round((s[mid - 1] + s[mid]) / 2.0, 4)


def compute_p95(vals: List[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    idx = int(math.ceil(0.95 * len(s))) - 1
    idx = max(0, min(len(s) - 1, idx))
    return round(s[idx], 4)


class EvalRunner:
    def __init__(
        self,
        labels_path: str,
        split: str = "test",
        method: str = "regex",
        limit: Optional[int] = None,
        cache_dir: Optional[str] = None,
        no_cache: bool = False,
        gemini_delay: float = 4.0,
    ):
        self.labels_path = labels_path
        self.data_dir = os.path.dirname(labels_path)
        self.split = split
        self.method = method
        self.limit = limit
        self.no_cache = no_cache
        self.gemini_delay = gemini_delay

        if cache_dir is None:
            self.cache_dir = os.path.join(CURRENT_DIR, ".cache")
        else:
            self.cache_dir = cache_dir

        self.ocr_cache_dir = os.path.join(self.cache_dir, "ocr")
        self.gemini_cache_dir = os.path.join(self.cache_dir, "gemini")
        os.makedirs(self.ocr_cache_dir, exist_ok=True)
        os.makedirs(self.gemini_cache_dir, exist_ok=True)

    def load_dataset(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.labels_path):
            raise FileNotFoundError(f"Labels file not found: {self.labels_path}")

        records = []
        with open(self.labels_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    if self.split == "all" or rec.get("split") == self.split:
                        records.append(rec)

        if self.limit and self.limit > 0:
            records = records[: self.limit]

        return records

    def run_ocr(self, img_path: str, img_bytes: bytes) -> Tuple[str, float, bool]:
        img_hash = hashlib.sha256(img_bytes).hexdigest()
        cache_file = os.path.join(self.ocr_cache_dir, f"{img_hash}.txt")

        if not self.no_cache and os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                text = f.read()
            return text, 0.0, True

        t0 = time.perf_counter()
        text, _ = ocr.extract_text_from_image_bytes(img_bytes)
        elapsed = time.perf_counter() - t0

        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(text)

        return text, elapsed, False

    def parse_document(self, text: str) -> Tuple[Dict[str, Any], float, Optional[str]]:
        t0 = time.perf_counter()

        if self.method == "regex":
            pred = nlp.parse_with_regex(text)
            elapsed = time.perf_counter() - t0
            return pred, elapsed, None

        elif self.method == "gemini":
            text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            cache_file = os.path.join(self.gemini_cache_dir, f"{text_hash}.json")

            if not self.no_cache and os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    pred = json.load(f)
                return pred, 0.0, None

            # Rate limit throttle
            if self.gemini_delay > 0:
                time.sleep(self.gemini_delay)

            # Retry on 429
            max_retries = 3
            backoff = 4.0
            last_err = None

            for attempt in range(max_retries):
                try:
                    pred = nlp.parse_with_gemini(text)
                    elapsed = time.perf_counter() - t0
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(pred, f, indent=2)
                    return pred, elapsed, None
                except Exception as e:
                    last_err = e
                    err_msg = str(e)
                    if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                        time.sleep(backoff)
                        backoff *= 2.0
                        continue
                    break

            elapsed = time.perf_counter() - t0
            clean_err = f"{last_err.__class__.__name__}: {str(last_err).splitlines()[0][:150]}"
            return {}, elapsed, clean_err

        else:
            raise ValueError(f"Unknown extraction method: {self.method}")

    def run(self) -> Dict[str, Any]:
        records = self.load_dataset()
        print(f"Loaded {len(records)} items for split='{self.split}', method='{self.method}'")

        doc_scores = []
        ocr_times = []
        parse_times = []
        error_count = 0
        error_details = []

        for idx, rec in enumerate(records, 1):
            file_name = rec.get("file")
            img_path = os.path.join(self.data_dir, file_name)
            if not os.path.exists(img_path):
                print(f"[{idx}/{len(records)}] Warning: Image not found: {img_path}")
                continue

            with open(img_path, "rb") as f:
                img_bytes = f.read()

            text, ocr_time, ocr_cached = self.run_ocr(img_path, img_bytes)
            if not ocr_cached:
                ocr_times.append(ocr_time)

            pred, parse_time, err = self.parse_document(text)
            parse_times.append(parse_time)

            if err:
                error_count += 1
                error_details.append({"file": file_name, "error": err})

            doc_res = scoring.score_document(pred, rec, method=self.method)
            doc_res["ocr_time_seconds"] = round(ocr_time, 4)
            doc_res["parse_time_seconds"] = round(parse_time, 4)
            doc_res["ocr_cached"] = ocr_cached
            if err:
                doc_res["error"] = err
            doc_scores.append(doc_res)

            status = "ALL_CORRECT" if doc_res["all_correct"] else "MISMATCH"
            print(f"[{idx}/{len(records)}] {file_name}: {status} (OCR={ocr_time:.2f}s, Parse={parse_time:.2f}s)")

        summary_metrics = scoring.compute_metrics(doc_scores)

        results = {
            "metadata": {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "method": self.method,
                "split": self.split,
                "dataset_count": len(doc_scores),
                "labels_path": self.labels_path,
                "python_version": sys.version.split()[0],
                "platform": sys.platform,
            },
            "metrics": summary_metrics,
            "timing": {
                "ocr_p50": compute_p50(ocr_times),
                "ocr_p95": compute_p95(ocr_times),
                "parse_p50": compute_p50(parse_times),
                "parse_p95": compute_p95(parse_times),
                "measured_ocr_runs": len(ocr_times),
                "measured_parse_runs": len(parse_times),
            },
            "errors": {
                "count": error_count,
                "details": error_details,
            },
            "document_results": doc_scores,
        }

        # Write output file
        results_dir = os.path.join(CURRENT_DIR, "results")
        os.makedirs(results_dir, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        out_filename = f"{date_str}_{self.method}_{self.split}.json"
        out_path = os.path.join(results_dir, out_filename)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        print(f"\nEvaluation Complete!")
        print(f"Results written to: {out_path}")
        print(f"Document Accuracy: {summary_metrics['document_level']['accuracy'] * 100:.1f}%")
        for f, m in summary_metrics["field_metrics"].items():
            print(f"  - {f}: {m['accuracy'] * 100:.1f}% ({m['ci_95']})")

        return results


def main():
    parser = argparse.ArgumentParser(description="Run Extraction Accuracy Evaluation")
    parser.add_argument("--split", choices=["dev", "test", "holdout", "all"], default="test", help="Dataset split to evaluate")
    parser.add_argument("--method", choices=["gemini", "regex"], default="regex", help="Extraction method to evaluate")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of documents to evaluate")
    parser.add_argument(
        "--labels",
        type=str,
        default=os.path.join(CURRENT_DIR, "data", "synthetic", "labels.jsonl"),
        help="Path to labels.jsonl",
    )
    parser.add_argument("--no-cache", action="store_true", help="Force fresh OCR and parser calls without using cache")
    parser.add_argument("--gemini-delay", type=float, default=4.0, help="Delay in seconds between Gemini API calls")

    args = parser.parse_args()

    runner = EvalRunner(
        labels_path=args.labels,
        split=args.split,
        method=args.method,
        limit=args.limit,
        no_cache=args.no_cache,
        gemini_delay=args.gemini_delay,
    )
    runner.run()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Per-layout accuracy breakdown of an eval results file.

Layout is derived from the file number for the synthetic set (see
generate_invoices.py: test files inv_021..inv_060 cycle layouts 1, 2, 3) and
read from the label for the hold-out set (layout 4).

Usage: python eval/layout_breakdown.py eval/results/<file>.json
"""

import json
import math
import sys

FIELDS = ["invoice_no", "total_amount", "party_strict", "party_lenient"]


def layout_of(doc):
    gt = doc["ground_truth"]
    if "layout" in gt:
        return gt["layout"]
    n = int(doc["file"].split("_")[1].split(".")[0])
    if n <= 20:
        return 1 if n % 2 else 2
    return (n - 21) % 3 + 1


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main(path):
    docs = json.load(open(path, encoding="utf-8"))["document_results"]
    groups = {}
    for d in docs:
        groups.setdefault(layout_of(d), []).append(d)
    out = {}
    for lay in sorted(groups):
        g = groups[lay]
        row = {"n": len(g)}
        for f in FIELDS:
            k = sum(1 for d in g if d["field_scores"].get(f))
            lo, hi = wilson(k, len(g))
            row[f] = {"correct": k, "acc": round(k / len(g), 4), "ci95": [round(lo, 4), round(hi, 4)]}
        out[f"layout_{lay}"] = row
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])

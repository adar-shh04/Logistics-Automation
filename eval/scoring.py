"""
Scoring and normalization logic for invoice extraction evaluation.
This module has zero dependencies on EasyOCR, PyTorch, or Google GenAI,
allowing it to run in lightweight CI environments and unit tests.
"""

import math
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def normalize_string(val: Any) -> str:
    """Trim, collapse multiple whitespace characters, and lowercase."""
    if val is None:
        return ""
    s = str(val).strip()
    return re.sub(r"\s+", " ", s).lower()


def normalize_amount(val: Any) -> Optional[float]:
    """Parse numeric amount from float, int, or currency-formatted string."""
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).strip()
    # Strip common currency symbols and labels
    s = re.sub(r"(₹|Rs\.?|INR|\$|\€)", "", s, flags=re.I).strip()
    s = s.replace(",", "")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def amounts_match(pred: Any, gt: Any, tolerance: float = 0.01) -> bool:
    """Check if prediction matches ground truth within numerical tolerance."""
    p_amt = normalize_amount(pred)
    g_amt = normalize_amount(gt)
    if p_amt is None or g_amt is None:
        return False
    return abs(p_amt - g_amt) <= tolerance


def normalize_date(val: Any) -> Optional[str]:
    """
    Parse date to ISO format YYYY-MM-DD.
    Supports day-first Indian formats: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY,
    as well as standard ISO YYYY-MM-DD.
    """
    if val is None or not str(val).strip():
        return None
    s = str(val).strip()

    # If already ISO YYYY-MM-DD
    m_iso = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", s)
    if m_iso:
        try:
            dt = datetime(int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None

    # Day-first formats: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
    for sep in ["/", "-", "."]:
        parts = s.split(sep)
        if len(parts) == 3:
            try:
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                if year < 100:
                    year += 2000
                dt = datetime(year, month, day)
                return dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                continue

    return None


def dates_match(pred: Any, gt: Any) -> bool:
    """Check if normalized dates match."""
    p_date = normalize_date(pred)
    g_date = normalize_date(gt)
    if not p_date or not g_date:
        return False
    return p_date == g_date


def exact_match(pred: Any, gt: Any) -> bool:
    """Exact string match after trimming, collapsing whitespace, and lowercasing."""
    p_str = normalize_string(pred)
    g_str = normalize_string(gt)
    if not p_str or not g_str:
        return False
    return p_str == g_str


def party_match(pred: Any, gt: Any) -> Tuple[bool, bool]:
    """
    Returns (strict_match, lenient_match).
    Strict: exact string equality after normalization.
    Lenient: substring containment in either direction if length >= 4.
    """
    p_str = normalize_string(pred)
    g_str = normalize_string(gt)
    if not p_str or not g_str:
        return (False, False)

    strict = (p_str == g_str)
    lenient = strict or (len(p_str) >= 4 and p_str in g_str) or (len(g_str) >= 4 and g_str in p_str)
    return (strict, lenient)


def wilson_confidence_interval(k: int, n: int, confidence: float = 0.95) -> Tuple[float, float]:
    """
    Compute 95% Wilson score interval for binomial proportion k/n.
    Returns (lower_bound, upper_bound) rounded to 4 decimals.
    """
    if n <= 0:
        return (0.0, 0.0)

    z = 1.95996  # 95% two-sided normal quantile
    p = k / n
    denominator = 1.0 + (z**2) / n
    center = (p + (z**2) / (2.0 * n)) / denominator
    margin = (z * math.sqrt((p * (1.0 - p) / n) + ((z**2) / (4.0 * (n**2))))) / denominator

    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)
    return (round(lower, 4), round(upper, 4))


def score_document(prediction: Dict[str, Any], ground_truth: Dict[str, Any], method: str) -> Dict[str, Any]:
    """
    Score predictions for a single invoice against ground truth.
    Fields evaluated: invoice_no, invoice_date, total_amount, gstin, hs_code, party.
    """
    field_scores: Dict[str, bool] = {}

    # invoice_no
    field_scores["invoice_no"] = exact_match(prediction.get("invoice_no"), ground_truth.get("invoice_no"))

    # invoice_date
    field_scores["invoice_date"] = dates_match(prediction.get("invoice_date"), ground_truth.get("invoice_date"))

    # total_amount
    field_scores["total_amount"] = amounts_match(prediction.get("total_amount"), ground_truth.get("total_amount"))

    # gstin
    field_scores["gstin"] = exact_match(prediction.get("gstin"), ground_truth.get("gstin"))

    # hs_code
    field_scores["hs_code"] = exact_match(prediction.get("hs_code"), ground_truth.get("hs_code"))

    # party
    strict_party, lenient_party = party_match(prediction.get("party"), ground_truth.get("party"))
    field_scores["party_strict"] = strict_party
    field_scores["party_lenient"] = lenient_party

    # Document-level accuracy: all 6 fields correct (using strict party)
    all_correct = (
        field_scores["invoice_no"]
        and field_scores["invoice_date"]
        and field_scores["total_amount"]
        and field_scores["gstin"]
        and field_scores["hs_code"]
        and field_scores["party_strict"]
    )

    return {
        "file": ground_truth.get("file"),
        "method": method,
        "prediction": prediction,
        "ground_truth": ground_truth,
        "field_scores": field_scores,
        "all_correct": all_correct,
    }


def compute_metrics(doc_scores: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate evaluation scores across documents.
    Computes per-field accuracies, Wilson 95% confidence intervals, and document-level accuracy.
    """
    n = len(doc_scores)
    if n == 0:
        return {"count": 0}

    fields = ["invoice_no", "invoice_date", "total_amount", "gstin", "hs_code", "party_strict", "party_lenient"]
    field_results = {}

    for f in fields:
        correct_count = sum(1 for s in doc_scores if s["field_scores"].get(f, False))
        acc = round(correct_count / n, 4)
        ci_low, ci_high = wilson_confidence_interval(correct_count, n)
        field_results[f] = {
            "correct": correct_count,
            "total": n,
            "accuracy": acc,
            "ci_95": [ci_low, ci_high],
        }

    doc_correct = sum(1 for s in doc_scores if s["all_correct"])
    doc_acc = round(doc_correct / n, 4)
    doc_ci_low, doc_ci_high = wilson_confidence_interval(doc_correct, n)

    return {
        "count": n,
        "field_metrics": field_results,
        "document_level": {
            "correct": doc_correct,
            "total": n,
            "accuracy": doc_acc,
            "ci_95": [doc_ci_low, doc_ci_high],
        },
    }

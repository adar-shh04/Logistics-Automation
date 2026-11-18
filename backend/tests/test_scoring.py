import sys
import os
import pytest

# Ensure eval directory is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "eval")))
import scoring


def test_normalize_string():
    assert scoring.normalize_string("  TAX   INVOICE  \n") == "tax invoice"
    assert scoring.normalize_string(None) == ""
    assert scoring.normalize_string("INV-2026-001") == "inv-2026-001"


def test_normalize_amount():
    assert scoring.normalize_amount(12345.5) == 12345.5
    assert scoring.normalize_amount("12,345.50") == 12345.5
    assert scoring.normalize_amount("₹ 1,25,000.00") == 125000.0
    assert scoring.normalize_amount("Rs. 450.75") == 450.75
    assert scoring.normalize_amount("INR 999.00") == 999.0
    assert scoring.normalize_amount("invalid_amount") is None
    assert scoring.normalize_amount(None) is None


def test_amounts_match_tolerance():
    assert scoring.amounts_match(123.45, 123.45) is True
    assert scoring.amounts_match("123.45", "123.455", tolerance=0.01) is True
    assert scoring.amounts_match("123.45", "123.50", tolerance=0.01) is False
    assert scoring.amounts_match(None, 100.0) is False
    assert scoring.amounts_match(100.0, None) is False


def test_normalize_date_day_first():
    assert scoring.normalize_date("15/03/2026") == "2026-03-15"
    assert scoring.normalize_date("05-11-2026") == "2026-11-05"
    assert scoring.normalize_date("28.02.2026") == "2026-02-28"
    assert scoring.normalize_date("2026-03-15") == "2026-03-15"
    assert scoring.normalize_date("not-a-date") is None
    assert scoring.normalize_date("") is None
    assert scoring.normalize_date(None) is None


def test_dates_match():
    assert scoring.dates_match("15/03/2026", "2026-03-15") is True
    assert scoring.dates_match("2026-03-15", "15-03-2026") is True
    assert scoring.dates_match("14/03/2026", "2026-03-15") is False
    assert scoring.dates_match("invalid", "2026-03-15") is False


def test_party_match_strict_and_lenient():
    # Exact match
    strict, lenient = scoring.party_match("Acme Logistics Pvt Ltd", "Acme Logistics Pvt Ltd")
    assert strict is True
    assert lenient is True

    # Case & whitespace normalized match
    strict, lenient = scoring.party_match(" acme   LOGISTICS pvt ltd ", "Acme Logistics Pvt Ltd")
    assert strict is True
    assert lenient is True

    # Substring match (lenient only)
    strict, lenient = scoring.party_match("Acme Logistics", "Acme Logistics Private Limited")
    assert strict is False
    assert lenient is True

    # Complete mismatch
    strict, lenient = scoring.party_match("Beta Motors", "Acme Logistics")
    assert strict is False
    assert lenient is False


def test_wilson_confidence_interval():
    # 0 out of 40
    low, high = scoring.wilson_confidence_interval(0, 40)
    assert low == 0.0
    assert 0.0 < high < 0.15

    # 40 out of 40
    low, high = scoring.wilson_confidence_interval(40, 40)
    assert 0.85 < low < 1.0
    assert high == 1.0

    # 20 out of 40 (50%)
    low, high = scoring.wilson_confidence_interval(20, 40)
    assert 0.30 < low < 0.40
    assert 0.60 < high < 0.70


def test_score_document_and_missing_fields():
    gt = {
        "file": "inv_001.png",
        "invoice_no": "INV-2026-001",
        "invoice_date": "2026-03-15",
        "total_amount": 125000.50,
        "gstin": "27AABCU9603R1ZM",
        "hs_code": "8471",
        "party": "Acme Logistics Pvt Ltd",
    }

    # Perfect prediction
    perfect_pred = dict(gt)
    res = scoring.score_document(perfect_pred, gt, method="gemini")
    assert res["all_correct"] is True
    assert res["field_scores"]["invoice_no"] is True
    assert res["field_scores"]["party_strict"] is True

    # Regex prediction: missing gstin, hs_code, invoice_date
    regex_pred = {
        "invoice_no": "INV-2026-001",
        "total_amount": 125000.50,
        "party": "Acme Logistics Pvt Ltd",
    }
    res_regex = scoring.score_document(regex_pred, gt, method="regex")
    assert res_regex["all_correct"] is False
    assert res_regex["field_scores"]["invoice_no"] is True
    assert res_regex["field_scores"]["total_amount"] is True
    assert res_regex["field_scores"]["party_strict"] is True
    assert res_regex["field_scores"]["gstin"] is False
    assert res_regex["field_scores"]["hs_code"] is False
    assert res_regex["field_scores"]["invoice_date"] is False

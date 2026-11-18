import pytest
from app import nlp

def test_parse_with_regex_standard_invoice():
    sample_text = """
    TAX INVOICE
    Invoice Number: INV/2026/001
    Date: 15/03/2026
    
    Bill To: Acme Logistics Private Limited
    GSTIN: 27AABCU9603R1ZM
    
    Description: Logistics Services
    HSN/SAC: 9965
    
    Grand Total: ₹ 1,25,000.50
    """
    result = nlp.parse_with_regex(sample_text)
    assert result.get("invoice_no") == "INV/2026/001"
    assert result.get("total_amount") == 125000.50
    assert result.get("party") == "Acme Logistics Private Limited"
    # Regex does not extract gstin or hs_code
    assert "gstin" not in result
    assert "hs_code" not in result

def test_parse_with_regex_alternative_keywords():
    sample_text = """
    Tax Invoice # TXN-8849
    Consignee: Globex Freight Ltd.
    Total Amount: 45,670.00
    """
    result = nlp.parse_with_regex(sample_text)
    assert result.get("invoice_no") == "TXN-8849"
    assert result.get("total_amount") == 45670.00
    assert result.get("party") == "Globex Freight Ltd."

def test_parse_with_regex_empty_or_malformed():
    result = nlp.parse_with_regex("")
    assert result == {}

def test_parse_with_gemini_raises_on_missing_key(monkeypatch):
    monkeypatch.setattr(nlp.settings, "gemini_api_key", "")
    with pytest.raises(ValueError, match="Gemini API key is not configured"):
        nlp.parse_with_gemini("Any invoice text")

    monkeypatch.setattr(nlp.settings, "gemini_api_key", "your_gemini_api_key_here")
    with pytest.raises(ValueError, match="Gemini API key is not configured"):
        nlp.parse_with_gemini("Any invoice text")

def test_parse_invoice_text_fallback_on_error(monkeypatch, caplog):
    def fake_gemini_failure(text):
        raise RuntimeError("Simulated upstream quota or connection error")

    monkeypatch.setattr(nlp, "parse_with_gemini", fake_gemini_failure)

    sample_text = """
    Invoice No: INV-FALLBACK-101
    Total Amount: 5000.00
    Buyer: Alpha Traders
    """
    res = nlp.parse_invoice_text(sample_text)
    assert res.get("extraction_method") == "regex"
    assert res.get("invoice_no") == "INV-FALLBACK-101"
    assert res.get("total_amount") == 5000.0
    assert res.get("party") == "Alpha Traders"

    # Verify warning was logged without sensitive credentials
    warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
    assert any("Gemini parsing failed (RuntimeError:" in r.message for r in warning_records)

def test_parse_invoice_text_success_tagged(monkeypatch):
    def fake_gemini_success(text):
        return {
            "invoice_no": "INV-GEMINI-202",
            "invoice_date": "2026-03-15",
            "total_amount": 9999.0,
            "gstin": "27AABCU9603R1ZM",
            "hs_code": "8708",
            "party": "Beta Motors"
        }

    monkeypatch.setattr(nlp, "parse_with_gemini", fake_gemini_success)

    res = nlp.parse_invoice_text("Some OCR text")
    assert res.get("extraction_method") == "gemini"
    assert res.get("invoice_no") == "INV-GEMINI-202"
    assert res.get("gstin") == "27AABCU9603R1ZM"

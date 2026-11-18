import json
import logging
import re
from typing import Dict
from google import genai
from pydantic import BaseModel, Field
from app.config import settings

logger = logging.getLogger(__name__)

class InvoiceFields(BaseModel):
    invoice_no: str = Field(default="", description="The invoice number")
    invoice_date: str = Field(default="", description="The date of the invoice")
    total_amount: float = Field(default=0.0, description="The total amount of the invoice")
    gstin: str = Field(default="", description="The GSTIN of the buyer/party")
    hs_code: str = Field(default="", description="The main HS Code found")
    party: str = Field(default="", description="The name of the buyer/consignee party")

def parse_with_gemini(text: str) -> Dict:
    """
    Uses Gemini to extract structured data from OCR text.
    Raises on any error (API failure, missing key, invalid JSON).
    """
    if not settings.gemini_api_key or settings.gemini_api_key == "your_gemini_api_key_here":
        raise ValueError("Gemini API key is not configured or is a placeholder")

    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = f"""
    Extract the following information from the invoice text below.
    Return the result as a JSON object matching this schema:
    {{
        "invoice_no": "string",
        "invoice_date": "string",
        "total_amount": number,
        "gstin": "string",
        "hs_code": "string",
        "party": "string"
    }}
    
    Invoice Text:
    {text}
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=InvoiceFields,
            temperature=0.1
        ),
    )
    
    if not response.text:
        raise ValueError("Empty response received from Gemini")
    
    return json.loads(response.text)

def parse_with_regex(text: str) -> Dict:
    """
    Extracts invoice fields using regex heuristics.
    Extracts invoice_no, total_amount, and party.
    Tuned on dev split to handle common OCR noise (e.g. ₹ read as {),
    currency prefixes (Rs., INR), and multi-line party blocks.
    """
    fields: Dict = {}
    normalized_text = text.replace("\r", "\n")
    lines = [l.strip() for l in normalized_text.splitlines() if l.strip()]

    # 1. Invoice Number (require delimiter like ':', '#', or '.')
    m = re.search(
        r'(?:Invoice|Inv\.?|Tax\s*Invoice|Bill)\s*(?:No\.?|#|Number)?\s*[:#\.]\s*([A-Za-z0-9\/\-\._]+)',
        normalized_text,
        re.I
    )
    if not m:
        m = re.search(r'(?:Invoice|Inv\.?|Tax\s*Invoice)\s*(?:No|#|Number)[:\s]+([A-Za-z0-9\/\-\._]+)', normalized_text, re.I)
    if m:
        fields['invoice_no'] = m.group(1).strip()

    # 2. Total Amount (handles ₹, Rs., INR, or OCR-corrupted { /[ currency symbols)
    m = re.search(
        r'(?:Total\s*Amount|Invoice\s*Total|Amount\s*Due|Grand\s*Total|Amount\s*Payable|Total)[:\s]*\n?\s*(?:₹|Rs\.?|INR|\$|{|\[)?\s*([0-9\.,]+)',
        normalized_text,
        re.I
    )
    if m:
        amt_str = m.group(1).replace(",", "").strip()
        try:
            fields['total_amount'] = float(amt_str)
        except (ValueError, TypeError):
            pass

    # 3. Party extraction: look for party after Bill To / Buyer / Consignee header
    for idx, line in enumerate(lines):
        if re.search(r'^(?:Bill To|Buyer|Consignee|Customer Name|Party)[\s/:]*$', line, re.I):
            # Inspect following lines to find actual company name
            for next_line in lines[idx + 1: idx + 4]:
                if re.match(r'^(?:Consignee|GSTIN|Place of|Invoice|Date|Tax ID|Destination|Item)', next_line, re.I):
                    continue
                fields['party'] = next_line
                break
            if 'party' in fields:
                break

    # Fallback party lookup if structured block not found
    if 'party' not in fields:
        m = re.search(r'(?:Bill To|Buyer|Consignee|Customer Name)(?::|\s+)\n?(.{2,120})', normalized_text, re.I)
        if m:
            candidate = m.group(1).strip().split("\n")[0]
            if not re.match(r'^(?:Consignee|GSTIN|Invoice)', candidate, re.I):
                fields['party'] = candidate

    if 'party' not in fields and lines:
        fields['party'] = lines[0][:150]

    return fields

# Backward-compatibility alias
_fallback_regex_parse = parse_with_regex

def parse_invoice_text(text: str) -> Dict:
    """
    Tries Gemini extraction; falls back to regex if Gemini fails.
    Attaches extraction_method ('gemini' or 'regex') to the result.
    """
    try:
        data = parse_with_gemini(text)
        data["extraction_method"] = "gemini"
        return data
    except Exception as e:
        err_msg = str(e).split("\n")[0][:200]
        logger.warning("Gemini parsing failed (%s: %s); falling back to regex", e.__class__.__name__, err_msg)
        data = parse_with_regex(text)
        data["extraction_method"] = "regex"
        return data

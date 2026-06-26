import json
from typing import Dict
from google import genai
from pydantic import BaseModel, Field
from app.config import settings

class InvoiceFields(BaseModel):
    invoice_no: str = Field(default="", description="The invoice number")
    invoice_date: str = Field(default="", description="The date of the invoice")
    total_amount: float = Field(default=0.0, description="The total amount of the invoice")
    gstin: str = Field(default="", description="The GSTIN of the buyer/party")
    hs_code: str = Field(default="", description="The main HS Code found")
    party: str = Field(default="", description="The name of the buyer/consignee party")

def parse_invoice_text(text: str) -> Dict:
    """
    Uses Gemini to extract structured data from OCR text.
    Fallback to regex if Gemini fails or is not configured.
    """
    if not settings.gemini_api_key or settings.gemini_api_key == "your_gemini_api_key_here":
        return _fallback_regex_parse(text)

    try:
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
        
        if response.text:
            return json.loads(response.text)
    except Exception as e:
        print(f"Gemini Extraction Error: {e}")
        
    return _fallback_regex_parse(text)

def _fallback_regex_parse(text: str) -> Dict:
    import re
    fields = {}
    text = text.replace("\r", "\n")
    m = re.search(r'(Invoice|Inv\.?|Tax Invoice)\s*(No|#|Number)[:\s]*([A-Za-z0-9\/\-\._]+)', text, re.I)
    if m:
        fields['invoice_no'] = m.group(3).strip()
    
    m = re.search(r'(Total\s*Amount|Invoice\s*Total|Amount\s*Due|Grand Total|Total)[:\s]*₹?\s*([0-9\.,]+)', text, re.I)
    if m:
        amt = m.group(2).replace(",", "").strip()
        try:
            fields['total_amount'] = float(amt)
        except:
            pass
            
    m = re.search(r'(Bill To|Buyer|Consignee)(:|\s+)\n?(.{2,120})', text, re.I)
    if m:
        fields['party'] = m.group(3).strip().split("\n")[0]
        
    if 'party' not in fields:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if lines:
            fields.setdefault('party', lines[0][:150])
            
    return fields

import re
from typing import Dict

def parse_invoice_text(text: str) -> Dict:
    fields = {}
    text = text.replace("\r", "\n")
    # invoice no
    m = re.search(r'(Invoice|Inv\.?|Tax Invoice)\s*(No|#|Number)[:\s]*([A-Za-z0-9\/\-\._]+)', text, re.I)
    if m:
        fields['invoice_no'] = m.group(3).strip()
    else:
        m2 = re.search(r'Inv[:\s]*([A-Za-z0-9\-]+)', text, re.I)
        if m2:
            fields['invoice_no'] = m2.group(1).strip()
    # date
    m = re.search(r'(Invoice\s*Date|Date)[:\s]*([0-3]?\d[\/\-\.\s][0-1]?\d[\/\-\.\s][0-9]{2,4})', text, re.I)
    if m:
        fields['invoice_date'] = m.group(2).strip()
    # amount
    m = re.search(r'(Total\s*Amount|Invoice\s*Total|Amount\s*Due|Grand Total|Total)[:\s]*₹?\s*([0-9\.,]+)', text, re.I)
    if m:
        amt = m.group(2).replace(",", "").strip()
        try:
            fields['total_amount'] = float(amt)
        except:
            pass
    # GSTIN / Party
    m = re.search(r'GSTIN[:\s]*([0-9A-Z]{15})', text, re.I)
    if m:
        fields['gstin'] = m.group(1).strip()
    # HS code
    m = re.search(r'HS\s*Code[:\s]*([0-9]{4,10})', text, re.I)
    if m:
        fields['hs_code'] = m.group(1)
    # simple party name heuristic (line preceding invoice metadata)
    m = re.search(r'(Bill To|Buyer|Consignee)(:|\s+)\n?(.{2,120})', text, re.I)
    if m:
        fields['party'] = m.group(3).strip().split("\n")[0]
    # fallback: first non-empty line could be party
    if 'party' not in fields:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if lines:
            fields.setdefault('party', lines[0][:150])
    return fields

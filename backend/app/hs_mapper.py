import csv
import os

HS_CSV = os.getenv("HS_CSV", "/app/hsdata/hs_codes.csv")
hs_index = {}

def load_hs():
    global hs_index
    if hs_index:
        return
    if not os.path.exists(HS_CSV):
        print("HS CSV not found at", HS_CSV)
        return
    with open(HS_CSV, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            code = r.get('hs_code') or r.get('HS') or r.get('code')
            desc = r.get('description') or r.get('desc') or ''
            try:
                hs_index[code.strip()] = desc.strip()
            except:
                continue

def lookup(hs_code):
    load_hs()
    return hs_index.get(str(hs_code), None)

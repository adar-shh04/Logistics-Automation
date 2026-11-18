#!/usr/bin/env python3
"""
Generate a second, blind hold-out set (layout 4) for the extraction evaluation.

Why this exists: in the first evaluation the regex parser was tuned while its
author could see the test split, and the tuned patterns contain the exact
wording of the "held-out" layout 3 ("Bill No.", "Amount Payable",
"Customer Name"). Layout 3 results are therefore not a fair held-out score.

This set was added on 2026-11-19 AFTER the parser was frozen at
backend/app/nlp.py git blob 8b7fad22eb60baae8d24b2a8b0f2ec3e5380f7c8.
Rules for using it:
  - Run the parser on it once; do not change backend/app/nlp.py afterwards
    and re-report it as held-out.
  - The label wording below was fixed before the first run. Each invoice picks
    its labels at random from lists of common Indian invoice wording, some of
    which the regex knows and some it does not, the way a mixed real-world
    batch would look.

Layout 4 ("freight invoice"): seller block and invoice meta stacked on the
left, recipient block on the right, item table, and the total in a band at
the bottom left.

The original generator (generate_invoices.py) and its data are left untouched.
"""

import argparse
import json
import os
import random
from datetime import datetime, timedelta
from typing import Dict

from PIL import Image, ImageDraw

from generate_invoices import (
    DEFAULT_FONT_SANS,
    DEFAULT_FONT_SERIF,
    PARTIES,
    SELLERS,
    apply_scan_artifacts,
    format_indian_currency,
    generate_gstin,
    get_font,
    load_hs_codes,
)

NUMBER_LABELS = ["Document No:", "Ref. No.:", "Invoice #:", "Voucher No:"]
DATE_LABELS = ["Issue Date:", "Dated:", "Date of Issue:"]
PARTY_LABELS = ["Ship To:", "Sold To:", "Recipient:", "Billed To:"]
GSTIN_LABELS = ["GST No.:", "GSTIN/UIN:", "GST Reg. No.:"]
HS_LABELS = ["Tariff Code", "HSN Code", "Commodity Code"]
TOTAL_LABELS = ["Net Amount Due:", "Balance Due:", "TOTAL (INR):", "Invoice Value:"]
CURRENCY_PREFIX = ["₹ ", "Rs ", "INR ", ""]
NUMBER_FORMATS = ["FRT/{yy}-{n}", "{n}/{yy}-{yy2}", "FI{n}"]


def render_layout_4(f: Dict, labels: Dict, font_path: str) -> Image.Image:
    width, height = 900, 1200
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    f_title = get_font(font_path, 24)
    f_header = get_font(font_path, 17)
    f_bold = get_font(font_path, 15)
    f_body = get_font(font_path, 14)
    f_small = get_font(font_path, 12)

    # Title strip
    draw.text((50, 35), "FREIGHT INVOICE", fill=(30, 30, 30), font=f_title)
    draw.line([(50, 72), (850, 72)], fill=(90, 90, 90), width=1)

    # Left: seller, then invoice meta
    draw.text((50, 90), f["seller_name"], fill=(10, 10, 10), font=f_header)
    draw.text((50, 114), f["seller_addr"], fill=(70, 70, 70), font=f_small)
    draw.text((50, 150), f"{labels['number']} {f['invoice_no']}", fill=(10, 10, 10), font=f_bold)
    draw.text((50, 175), f"{labels['date']} {f['display_date']}", fill=(30, 30, 30), font=f_body)

    # Right: recipient block
    draw.rectangle([(470, 88), (850, 205)], outline=(170, 170, 170), width=1)
    draw.text((485, 98), labels["party"], fill=(60, 60, 60), font=f_bold)
    draw.text((485, 122), f["party"], fill=(10, 10, 10), font=f_header)
    draw.text((485, 150), f"{labels['gstin']} {f['gstin']}", fill=(40, 40, 40), font=f_body)
    draw.text((485, 175), f["place_of_supply"], fill=(80, 80, 80), font=f_small)

    # Item table
    draw.rectangle([(50, 240), (850, 272)], fill=(238, 238, 238), outline=(200, 200, 200), width=1)
    draw.text((60, 248), "Particulars", fill=(20, 20, 20), font=f_bold)
    draw.text((420, 248), labels["hs"], fill=(20, 20, 20), font=f_bold)
    draw.text((570, 248), "Units", fill=(20, 20, 20), font=f_bold)
    draw.text((680, 248), "Value", fill=(20, 20, 20), font=f_bold)
    draw.text((60, 290), f["item_desc"][:36], fill=(20, 20, 20), font=f_body)
    draw.text((420, 290), f["hs_code"], fill=(20, 20, 20), font=f_body)
    draw.text((570, 290), str(f["qty"]), fill=(20, 20, 20), font=f_body)
    draw.text((680, 290), f["formatted_subtotal"], fill=(20, 20, 20), font=f_body)
    draw.line([(50, 325), (850, 325)], fill=(210, 210, 210), width=1)
    draw.text((560, 345), f"GST @ {f['tax_pct']}%", fill=(60, 60, 60), font=f_body)
    draw.text((680, 345), f["formatted_tax"], fill=(60, 60, 60), font=f_body)

    # Total band (bottom left)
    draw.rectangle([(50, 400), (500, 450)], fill=(245, 245, 245), outline=(120, 120, 120), width=1)
    draw.text((65, 415), labels["total"], fill=(10, 10, 10), font=f_header)
    draw.text((280, 415), f"{labels['currency']}{f['formatted_total']}", fill=(10, 10, 10), font=f_header)

    draw.text((50, 760), "E. & O.E.  Subject to Mumbai jurisdiction.", fill=(100, 100, 100), font=f_small)
    draw.text((640, 790), "For the Company", fill=(60, 60, 60), font=f_body)
    return img


def generate(output_dir: str, seed: int, count: int):
    rng = random.Random(seed)
    hs_codes = load_hs_codes()
    os.makedirs(output_dir, exist_ok=True)
    fonts = [DEFAULT_FONT_SANS, DEFAULT_FONT_SERIF]
    base_date = datetime(2026, 5, 1)
    labels_out = []

    for i in range(1, count + 1):
        font_path = rng.choice(fonts)
        seller = rng.choice(SELLERS)
        party = rng.choice(PARTIES)
        gstin = generate_gstin(rng)
        hs_code, item_desc = rng.choice(hs_codes)
        inv_dt = base_date + timedelta(days=rng.randint(1, 90))
        display_date = inv_dt.strftime(rng.choice(["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"]))
        n = rng.randint(100, 9999)
        inv_no = rng.choice(NUMBER_FORMATS).format(yy="26", yy2="27", n=n)
        qty = rng.randint(1, 40)
        rate = rng.choice([180.0, 750.0, 2200.0, 6400.0, 12500.0, 38000.0])
        subtotal = round(qty * rate, 2)
        tax_pct = rng.choice([5, 12, 18])
        tax = round(subtotal * tax_pct / 100.0, 2)
        total = round(subtotal + tax, 2)

        fields = {
            "seller_name": seller[0],
            "seller_addr": seller[1],
            "party": party,
            "gstin": gstin,
            "hs_code": hs_code,
            "item_desc": item_desc,
            "invoice_no": inv_no,
            "display_date": display_date,
            "qty": qty,
            "tax_pct": tax_pct,
            "formatted_subtotal": format_indian_currency(subtotal),
            "formatted_tax": format_indian_currency(tax),
            "formatted_total": format_indian_currency(total),
            "place_of_supply": rng.choice(["Pune, Maharashtra", "Hyderabad, Telangana", "Kolkata, West Bengal", "Ahmedabad, Gujarat"]),
        }
        labels = {
            "number": rng.choice(NUMBER_LABELS),
            "date": rng.choice(DATE_LABELS),
            "party": rng.choice(PARTY_LABELS),
            "gstin": rng.choice(GSTIN_LABELS),
            "hs": rng.choice(HS_LABELS),
            "total": rng.choice(TOTAL_LABELS),
            "currency": rng.choice(CURRENCY_PREFIX),
        }

        img = render_layout_4(fields, labels, font_path)
        if rng.random() < 0.40:
            img = apply_scan_artifacts(img, rng)
        name = f"hold_{i:03d}.png"
        img.save(os.path.join(output_dir, name), format="PNG")
        labels_out.append({
            "file": name,
            "split": "holdout",
            "layout": 4,
            "label_wording": labels,
            "invoice_no": inv_no,
            "invoice_date": inv_dt.strftime("%Y-%m-%d"),
            "total_amount": total,
            "gstin": gstin,
            "hs_code": hs_code,
            "party": party,
        })

    with open(os.path.join(output_dir, "labels.jsonl"), "w", encoding="utf-8") as fh:
        for rec in labels_out:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Generated {len(labels_out)} hold-out invoices in {output_dir}")


def main():
    p = argparse.ArgumentParser(description="Generate the blind layout-4 hold-out set")
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--count", type=int, default=30)
    p.add_argument("--output-dir", default=os.path.join(os.path.dirname(__file__), "data", "holdout"))
    a = p.parse_args()
    generate(a.output_dir, a.seed, a.count)


if __name__ == "__main__":
    main()

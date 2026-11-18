#!/usr/bin/env python3
"""
Generate synthetic invoice dataset for extraction accuracy evaluation.
Deterministic generation controlled by --seed.
"""

import argparse
import csv
import io
import json
import os
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
DEFAULT_FONT_SANS = os.path.join(FONTS_DIR, "DejaVuSans.ttf")
DEFAULT_FONT_SERIF = os.path.join(FONTS_DIR, "DejaVuSerif.ttf")

HS_CODES_FILE = os.path.join(os.path.dirname(__file__), "..", "backend", "app", "hsdata", "hs_codes.csv")

PARTIES = [
    "Acme Industrial Logistics Pvt Ltd",
    "Vanguard Maritime Services",
    "Reliance Logistics & Distribution",
    "Mahindra Logistics Solutions",
    "Tata Steel Processing & Distribution Ltd",
    "Adani Ports & Special Economic Zone",
    "Blue Dart Express Cargo",
    "Delhivery Supply Chain Operations",
    "Larsen & Toubro Heavy Cargo",
    "Sundaram Fasteners Supply Chain",
    "Godrej Consumer Distribution Hub",
    "Infosys BPM Global Freight",
    "Wipro Infrastructure Supply",
    "Bajaj Auto Parts Logistics",
    "Hero FinCorp Freight Depot",
    "TVS Supply Chain Solutions",
    "Apollo Tyres National Depot",
    "ITC Agri Logistics Network",
    "Maruti Suzuki Central Spares",
    "Havells Electrical Logistics",
    "Bharat Heavy Electricals Freight",
    "Kalyani Steels Transport Division",
    "Thermax Industrial Shipping",
    "Voltas Commercial Cargo Hub",
    "Crompton Greaves Freight",
]

SELLERS = [
    ("Apex Global Logistics Ltd", "101 Harbor View, Marine Drive, Mumbai 400020", "27AAACA1234A1Z1"),
    ("Pacific Cargo Movers Pvt Ltd", "42 Ring Road, Indiranagar, Bengaluru 560038", "29BBBPM5678B1Z2"),
    ("Deccan Freight Forwarders", "88 Express Highway, Guindy, Chennai 600032", "33CCCFF9012C1Z3"),
    ("Northern Logistics Gateway", "12 Connaught Place, New Delhi 110001", "07DDDNW3456D1Z4"),
]

STATE_CODES = ["07", "27", "29", "33", "24", "19"]


def load_hs_codes() -> List[Tuple[str, str]]:
    codes = []
    if os.path.exists(HS_CODES_FILE):
        with open(HS_CODES_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                codes.append((row["hs_code"].strip(), row["description"].strip()))
    if not codes:
        codes = [
            ("8471", "Automatic data processing machines (computers)"),
            ("8542", "Electronic integrated circuits"),
            ("2710", "Petroleum oils and bituminous minerals"),
            ("1006", "Rice"),
            ("0101", "Live horses, asses, mules"),
        ]
    return codes


def format_indian_currency(amt: float) -> str:
    s = f"{amt:.2f}"
    parts = s.split(".")
    integer_part = parts[0]
    decimal_part = parts[1]
    if len(integer_part) <= 3:
        formatted = integer_part
    else:
        last3 = integer_part[-3:]
        rest = integer_part[:-3]
        groups = []
        while len(rest) > 2:
            groups.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.append(rest)
        groups.reverse()
        formatted = ",".join(groups) + "," + last3
    return f"{formatted}.{decimal_part}"


def generate_gstin(rng: random.Random) -> str:
    state = rng.choice(STATE_CODES)
    pan_letters = "".join(rng.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=5))
    pan_digits = "".join(rng.choices("0123456789", k=4))
    pan_last = rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ")
    return f"{state}{pan_letters}{pan_digits}{pan_last}1Z{rng.choice('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')}"


def get_font(path: str, size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def render_layout_1(fields: Dict, font_path: str) -> Image.Image:
    """Header-Table-Footer standard tax invoice layout."""
    width, height = 900, 1200
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    f_title = get_font(font_path, 26)
    f_header = get_font(font_path, 18)
    f_bold = get_font(font_path, 16)
    f_body = get_font(font_path, 14)
    f_small = get_font(font_path, 12)

    # Top banner / Title
    draw.rectangle([(40, 30), (860, 80)], fill=(240, 244, 248), outline=(200, 210, 220), width=1)
    draw.text((360, 42), "TAX INVOICE", fill=(20, 30, 60), font=f_title)

    # Seller & Invoice Details
    draw.text((50, 100), fields["seller_name"], fill=(10, 10, 10), font=f_header)
    draw.text((50, 125), fields["seller_addr"], fill=(60, 60, 60), font=f_small)
    draw.text((50, 145), f"GSTIN: {fields['seller_gstin']}", fill=(60, 60, 60), font=f_small)

    # Invoice Meta Box (Right)
    draw.rectangle([(550, 95), (850, 175)], outline=(180, 180, 180), width=1)
    draw.text((565, 105), f"Invoice No: {fields['invoice_no']}", fill=(10, 10, 10), font=f_bold)
    draw.text((565, 130), f"Date: {fields['display_date']}", fill=(10, 10, 10), font=f_body)
    draw.text((565, 152), f"Place of Supply: {fields['place_of_supply']}", fill=(60, 60, 60), font=f_small)

    # Bill To Box
    draw.rectangle([(40, 195), (860, 275)], fill=(250, 250, 250), outline=(200, 200, 200), width=1)
    draw.text((55, 205), "Bill To / Consignee:", fill=(40, 40, 40), font=f_bold)
    draw.text((55, 228), fields["party"], fill=(10, 10, 10), font=f_header)
    draw.text((55, 252), f"GSTIN: {fields['gstin']}", fill=(40, 40, 40), font=f_body)

    # Items Table Header
    draw.rectangle([(40, 300), (860, 335)], fill=(230, 235, 245), outline=(180, 190, 205), width=1)
    draw.text((50, 310), "S.No", fill=(20, 20, 20), font=f_bold)
    draw.text((120, 310), "Description of Goods / Services", fill=(20, 20, 20), font=f_bold)
    draw.text((480, 310), "HSN/SAC", fill=(20, 20, 20), font=f_bold)
    draw.text((620, 310), "Qty", fill=(20, 20, 20), font=f_bold)
    draw.text((720, 310), "Amount (INR)", fill=(20, 20, 20), font=f_bold)

    # Table Row
    draw.line([(40, 380), (860, 380)], fill=(220, 220, 220), width=1)
    draw.text((60, 350), "1", fill=(30, 30, 30), font=f_body)
    draw.text((120, 350), fields["item_desc"][:38], fill=(30, 30, 30), font=f_body)
    draw.text((490, 350), fields["hs_code"], fill=(30, 30, 30), font=f_body)
    draw.text((630, 350), str(fields["qty"]), fill=(30, 30, 30), font=f_body)
    draw.text((720, 350), fields["formatted_subtotal"], fill=(30, 30, 30), font=f_body)

    # Tax details
    draw.line([(40, 440), (860, 440)], fill=(180, 190, 205), width=1)
    draw.text((500, 455), "Taxable Amount:", fill=(50, 50, 50), font=f_body)
    draw.text((720, 455), fields["formatted_subtotal"], fill=(50, 50, 50), font=f_body)
    draw.text((500, 485), f"IGST ({fields['tax_pct']}%):", fill=(50, 50, 50), font=f_body)
    draw.text((720, 485), fields["formatted_tax"], fill=(50, 50, 50), font=f_body)

    # Total Box
    draw.rectangle([(460, 530), (860, 580)], fill=(240, 248, 255), outline=(100, 140, 200), width=2)
    draw.text((480, 545), "Grand Total:", fill=(10, 20, 50), font=f_header)
    draw.text((680, 545), f"₹ {fields['formatted_total']}", fill=(10, 20, 50), font=f_header)

    # Footer note
    draw.text((50, 800), "Declaration: We declare that this invoice shows the actual price of the goods described.", fill=(90, 90, 90), font=f_small)
    draw.text((650, 820), "Authorized Signatory", fill=(60, 60, 60), font=f_body)
    return img


def render_layout_2(fields: Dict, font_path: str) -> Image.Image:
    """Two-column commercial invoice layout."""
    width, height = 900, 1200
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    f_title = get_font(font_path, 24)
    f_header = get_font(font_path, 18)
    f_bold = get_font(font_path, 15)
    f_body = get_font(font_path, 14)
    f_small = get_font(font_path, 12)

    # Header title
    draw.text((50, 40), fields["seller_name"], fill=(20, 40, 80), font=f_title)
    draw.text((50, 75), "COMMERCIAL INVOICE", fill=(100, 100, 100), font=f_header)
    draw.line([(50, 105), (850, 105)], fill=(40, 60, 120), width=2)

    # Column 1 (Left): Buyer info
    draw.text((50, 125), "Buyer / Consignee:", fill=(60, 60, 60), font=f_bold)
    draw.text((50, 150), fields["party"], fill=(10, 10, 10), font=f_header)
    draw.text((50, 178), f"GSTIN: {fields['gstin']}", fill=(40, 40, 40), font=f_body)
    draw.text((50, 200), f"Destination: {fields['place_of_supply']}", fill=(80, 80, 80), font=f_small)

    # Column 2 (Right): Invoice reference
    draw.text((520, 125), f"Invoice Number: {fields['invoice_no']}", fill=(10, 10, 10), font=f_header)
    draw.text((520, 155), f"Invoice Date: {fields['display_date']}", fill=(30, 30, 30), font=f_body)
    draw.text((520, 180), f"Seller GSTIN: {fields['seller_gstin']}", fill=(80, 80, 80), font=f_small)

    # Items table
    draw.rectangle([(50, 260), (850, 295)], fill=(245, 245, 245), outline=(210, 210, 210), width=1)
    draw.text((60, 270), "Item / Commodity", fill=(20, 20, 20), font=f_bold)
    draw.text((380, 270), "HS Code", fill=(20, 20, 20), font=f_bold)
    draw.text((520, 270), "Quantity", fill=(20, 20, 20), font=f_bold)
    draw.text((680, 270), "Total Value", fill=(20, 20, 20), font=f_bold)

    draw.text((60, 320), fields["item_desc"][:34], fill=(20, 20, 20), font=f_body)
    draw.text((380, 320), fields["hs_code"], fill=(20, 20, 20), font=f_body)
    draw.text((520, 320), str(fields["qty"]), fill=(20, 20, 20), font=f_body)
    draw.text((680, 320), f"INR {fields['formatted_subtotal']}", fill=(20, 20, 20), font=f_body)
    draw.line([(50, 360), (850, 360)], fill=(220, 220, 220), width=1)

    # Summary
    draw.text((520, 400), "Net Value:", fill=(60, 60, 60), font=f_body)
    draw.text((700, 400), fields["formatted_subtotal"], fill=(40, 40, 40), font=f_body)
    draw.text((520, 430), "Applicable GST:", fill=(60, 60, 60), font=f_body)
    draw.text((700, 430), fields["formatted_tax"], fill=(40, 40, 40), font=f_body)
    draw.line([(500, 465), (850, 465)], fill=(150, 150, 150), width=1)

    draw.text((500, 485), "Total Amount:", fill=(10, 10, 10), font=f_header)
    draw.text((670, 485), f"Rs. {fields['formatted_total']}", fill=(10, 10, 10), font=f_header)

    return img


def render_layout_3(fields: Dict, font_path: str) -> Image.Image:
    """
    Held-out layout for test split only.
    Uses alternative terminology to test generalization:
    - 'Bill No.' instead of 'Invoice No.'
    - 'Billing Date:' instead of 'Date:'
    - 'Customer Name:' instead of 'Bill To:'
    - 'Tax ID (GST):' instead of 'GSTIN:'
    - 'HS Classification:' instead of 'HSN/SAC:'
    - 'Amount Payable:' instead of 'Grand Total:'
    """
    width, height = 900, 1200
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    f_title = get_font(font_path, 22)
    f_header = get_font(font_path, 17)
    f_bold = get_font(font_path, 15)
    f_body = get_font(font_path, 14)
    f_small = get_font(font_path, 12)

    # Header
    draw.rectangle([(40, 30), (860, 75)], fill=(235, 240, 235), outline=(190, 210, 190), width=1)
    draw.text((350, 40), "BILL OF SUPPLY", fill=(20, 60, 30), font=f_title)

    draw.text((50, 95), fields["seller_name"], fill=(20, 20, 20), font=f_header)
    draw.text((50, 120), fields["seller_addr"], fill=(80, 80, 80), font=f_small)

    # Reference box
    draw.rectangle([(520, 90), (850, 180)], outline=(190, 190, 190), width=1)
    draw.text((535, 100), f"Bill No. {fields['invoice_no']}", fill=(10, 10, 10), font=f_bold)
    draw.text((535, 125), f"Billing Date: {fields['display_date']}", fill=(40, 40, 40), font=f_body)
    draw.text((535, 150), f"Tax ID (GST): {fields['seller_gstin']}", fill=(80, 80, 80), font=f_small)

    # Customer section
    draw.rectangle([(40, 200), (860, 275)], fill=(250, 252, 250), outline=(200, 215, 200), width=1)
    draw.text((55, 210), "Customer Name:", fill=(60, 60, 60), font=f_bold)
    draw.text((55, 230), fields["party"], fill=(10, 10, 10), font=f_header)
    draw.text((55, 252), f"Tax ID (GST): {fields['gstin']}", fill=(40, 40, 40), font=f_body)

    # Line item block
    draw.text((55, 300), f"Service / Commodity: {fields['item_desc']}", fill=(20, 20, 20), font=f_body)
    draw.text((55, 330), f"HS Classification: {fields['hs_code']}", fill=(40, 40, 40), font=f_body)
    draw.text((55, 360), f"Quantity Billed: {fields['qty']} Units", fill=(40, 40, 40), font=f_body)

    # Amount Payable block
    draw.rectangle([(420, 440), (860, 500)], fill=(245, 250, 245), outline=(50, 120, 50), width=2)
    draw.text((440, 458), "Amount Payable:", fill=(10, 50, 20), font=f_header)
    draw.text((640, 458), f"INR {fields['formatted_total']}", fill=(10, 50, 20), font=f_header)

    return img


def apply_scan_artifacts(img: Image.Image, rng: random.Random) -> Image.Image:
    """Mild scan artifacts: slight rotation, blur, or JPEG compression."""
    # Deterministic rotation ±1.5 deg
    angle = rng.choice([-1.5, -1.0, -0.5, 0.5, 1.0, 1.5])
    img = img.rotate(angle, resample=Image.Resampling.BILINEAR, expand=False, fillcolor=(255, 255, 255))

    # Optional mild blur
    if rng.random() > 0.5:
        img = img.filter(ImageFilter.GaussianBlur(radius=0.4))

    # JPEG artifact compression
    buf = io.BytesIO()
    quality = rng.randint(82, 92)
    img.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def generate_dataset(output_dir: str, seed: int = 42):
    rng = random.Random(seed)
    hs_code_list = load_hs_codes()

    os.makedirs(output_dir, exist_ok=True)
    labels_file = os.path.join(output_dir, "labels.jsonl")

    # Fonts
    font_paths = [DEFAULT_FONT_SANS, DEFAULT_FONT_SERIF]

    # Total 60: 20 dev, 40 test
    # Dev: layouts 1 and 2 only (10 layout 1, 10 layout 2)
    # Test: layouts 1, 2, and 3 (13 layout 1, 13 layout 2, 14 layout 3)
    dataset_plan = []
    for i in range(1, 21):
        layout = 1 if (i % 2 != 0) else 2
        dataset_plan.append((f"inv_{i:03d}.png", "dev", layout))

    for i in range(21, 61):
        rem = (i - 21) % 3
        layout = rem + 1  # 1, 2, or 3
        dataset_plan.append((f"inv_{i:03d}.png", "test", layout))

    base_date = datetime(2026, 3, 1)
    labels = []

    for filename, split, layout_id in dataset_plan:
        font_path = rng.choice(font_paths)
        seller = rng.choice(SELLERS)
        party = rng.choice(PARTIES)
        gstin = generate_gstin(rng)
        hs_code, item_desc = rng.choice(hs_code_list)

        # Dates: Day-first Indian format
        date_offset = rng.randint(1, 60)
        inv_dt = base_date + timedelta(days=date_offset)
        iso_date = inv_dt.strftime("%Y-%m-%d")

        date_style = rng.choice(["slash", "dash", "dot"])
        if date_style == "slash":
            display_date = inv_dt.strftime("%d/%m/%Y")
        elif date_style == "dash":
            display_date = inv_dt.strftime("%d-%m-%Y")
        else:
            display_date = inv_dt.strftime("%d.%m.%Y")

        # Invoice number
        num = rng.randint(1000, 9999)
        if layout_id == 1:
            inv_no = f"INV-2026-{num}"
        elif layout_id == 2:
            inv_no = f"TX/26/{num}"
        else:
            inv_no = f"BILL-{num}"

        # Amounts
        qty = rng.randint(1, 25)
        unit_rate = rng.choice([250.0, 500.0, 1250.0, 3400.0, 8500.0, 15000.0, 45000.0])
        subtotal = round(qty * unit_rate, 2)
        tax_pct = rng.choice([5, 12, 18])
        tax = round(subtotal * (tax_pct / 100.0), 2)
        total_amount = round(subtotal + tax, 2)

        fields = {
            "seller_name": seller[0],
            "seller_addr": seller[1],
            "seller_gstin": seller[2],
            "party": party,
            "gstin": gstin,
            "hs_code": hs_code,
            "item_desc": item_desc,
            "invoice_no": inv_no,
            "display_date": display_date,
            "iso_date": iso_date,
            "qty": qty,
            "subtotal": subtotal,
            "tax": tax,
            "tax_pct": tax_pct,
            "total_amount": total_amount,
            "formatted_subtotal": format_indian_currency(subtotal),
            "formatted_tax": format_indian_currency(tax),
            "formatted_total": format_indian_currency(total_amount),
            "place_of_supply": rng.choice(["Mumbai, Maharashtra", "Bengaluru, Karnataka", "Chennai, Tamil Nadu", "New Delhi, Delhi"]),
        }

        if layout_id == 1:
            img = render_layout_1(fields, font_path)
        elif layout_id == 2:
            img = render_layout_2(fields, font_path)
        else:
            img = render_layout_3(fields, font_path)

        # Apply noise to 40% of images
        if rng.random() < 0.40:
            img = apply_scan_artifacts(img, rng)

        img_path = os.path.join(output_dir, filename)
        img.save(img_path, format="PNG")

        label = {
            "file": filename,
            "split": split,
            "invoice_no": inv_no,
            "invoice_date": iso_date,
            "total_amount": total_amount,
            "gstin": gstin,
            "hs_code": hs_code,
            "party": party,
        }
        labels.append(label)

    with open(labels_file, "w", encoding="utf-8") as f:
        for lbl in labels:
            f.write(json.dumps(lbl) + "\n")

    print(f"Generated {len(labels)} invoices in {output_dir}")
    print(f"Labels written to {labels_file}")


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic invoice dataset")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic generation")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "data", "synthetic"),
        help="Target directory for generated images and labels.jsonl",
    )
    args = parser.parse_args()
    generate_dataset(args.output_dir, seed=args.seed)


if __name__ == "__main__":
    main()

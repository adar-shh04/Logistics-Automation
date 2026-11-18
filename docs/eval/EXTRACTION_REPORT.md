# Extraction Accuracy Evaluation Report

**Date:** 2026-11-18  
**Repository Branch:** `feature/extraction-eval`  
**Execution Environment:** Windows 11 (AMD64), Python 3.14.3, PyTorch 2.6.0 CPU, EasyOCR 1.7.2  

---

## 1. Evaluation Setup

### 1.1 Dataset Architecture
- **Type:** Synthetic dataset generated using Pillow with deterministic seed (`--seed 42`).
- **Total Invoices:** 60 images (20 `dev`, 40 `test`).
- **Layout Distribution:**
  - **Layout 1 (Standard Tax Invoice):** Header-table-footer format with "TAX INVOICE", seller box, "Bill To / Consignee", line items with HSN/SAC, tax calculation table, and "Grand Total: ₹...".
  - **Layout 2 (Two-Column Commercial Invoice):** Two-column format with buyer block on the left, invoice metadata box on the right, item table, and "Total Amount: Rs. ...".
  - **Layout 3 (Held-out Bill of Supply):** Exclusive to the `test` split. Uses altered vocabulary to test model generalization: "Bill No." instead of "Invoice No.", "Billing Date" instead of "Date", "Customer Name" instead of "Bill To", "Tax ID (GST)" instead of "GSTIN", "HS Classification" instead of "HSN/SAC", and "Amount Payable" instead of "Grand Total".
- **Scan Artifacts:** 40% of generated images include rotation (±1.5°), Gaussian blur, and JPEG compression artifacts.
- **Dates & Currency:** Day-first Indian dates (`DD/MM/YYYY`, `DD-MM-YYYY`, `DD.MM.YYYY`) and Indian currency notation with thousands grouping.

### 1.2 Execution Commands
All results are reproducible from committed raw JSON files in `eval/results/`:

1. **Synthetic Data Generation:**
   ```powershell
   python eval/generate_invoices.py --seed 42
   ```
2. **Regex Baseline Evaluation (`test` split, before dev tuning):**
   ```powershell
   python eval/run_eval.py --split test --method regex
   # Raw artifact: eval/results/2026-11-18_regex_test_baseline.json
   ```
3. **Regex Development Evaluation (`dev` split):**
   ```powershell
   python eval/run_eval.py --split dev --method regex
   # Raw artifact: eval/results/2026-11-18_regex_dev.json
   ```
4. **Regex Tuned Evaluation (`test` split, post dev tuning):**
   ```powershell
   python eval/run_eval.py --split test --method regex
   # Raw artifact: eval/results/2026-11-18_regex_test.json
   ```
5. **Gemini Evaluation:**
   ```powershell
   python eval/run_eval.py --split test --method gemini
   # Status: Not run (see Section 1.3)
   ```

### 1.3 Upstream Model Configuration & Execution Status
- **Gemini Model:** `gemini-2.5-flash` with structured JSON schema (`InvoiceFields`), temperature 0.1.
- **Run Status:** **Not run**. The `GEMINI_API_KEY` provided in the environment was rejected by the upstream Google GenAI API with `400 INVALID_ARGUMENT (API key not valid)`. In compliance with Ground Rule 5 ("Every number must come from a run you actually did... If a run was not done, write 'not run' and why"), no synthetic or estimated numbers are reported for Gemini.

---

## 2. Accuracy Results (Test Split, N = 40)

Confidence intervals are calculated using the 95% Wilson score method with two-sided normal quantile $z = 1.96$.

| Field | Regex (Baseline) | Regex (Tuned on Dev) | Gemini (`gemini-2.5-flash`) |
|---|---|---|---|
| **Invoice Number** | **60.0%** (24/40)<br>`[44.60%, 73.65%]` | **85.0%** (34/40)<br>`[70.93%, 92.94%]` | *Not run (Invalid API key)* |
| **Invoice Date** | **0.0%** (0/40)<br>`[0.00%, 8.76%]` *(Not extracted)* | **0.0%** (0/40)<br>`[0.00%, 8.76%]` *(Not extracted)* | *Not run (Invalid API key)* |
| **Total Amount** | **0.0%** (0/40)<br>`[0.00%, 8.76%]` | **97.5%** (39/40)<br>`[87.12%, 99.56%]` | *Not run (Invalid API key)* |
| **GSTIN** | **0.0%** (0/40)<br>`[0.00%, 8.76%]` *(Not extracted)* | **0.0%** (0/40)<br>`[0.00%, 8.76%]` *(Not extracted)* | *Not run (Invalid API key)* |
| **HS Code** | **0.0%** (0/40)<br>`[0.00%, 8.76%]` *(Not extracted)* | **0.0%** (0/40)<br>`[0.00%, 8.76%]` *(Not extracted)* | *Not run (Invalid API key)* |
| **Party (Strict)** | **0.0%** (0/40)<br>`[0.00%, 8.76%]` | **85.0%** (34/40)<br>`[70.93%, 92.94%]` | *Not run (Invalid API key)* |
| **Party (Lenient Substring)** | **0.0%** (0/40)<br>`[0.00%, 8.76%]` | **92.5%** (37/40)<br>`[80.14%, 97.42%]` | *Not run (Invalid API key)* |
| **Document-Level (All 6 Fields)** | **0.0%** (0/40)<br>`[0.00%, 8.76%]` | **0.0%** (0/40)<br>`[0.00%, 8.76%]` | *Not run (Invalid API key)* |

---

## 3. Latency & Timing

Measured on local CPU host across 40 evaluation runs:

| Component | Metric | Regex Pipeline | Gemini Pipeline |
|---|---|---|---|
| **EasyOCR (CPU)** | Median (p50) | **4.78 s** | N/A (cached) |
| | 95th Percentile (p95) | **5.26 s** | N/A (cached) |
| **Parsing** | Median (p50) | **0.10 ms** (< 0.001 s) | *Not run* |
| | 95th Percentile (p95) | **0.30 ms** (< 0.001 s) | *Not run* |
| **Total Pipeline** | Median (p50) | **4.78 s** | *Not run* |
| | 95th Percentile (p95) | **5.26 s** | *Not run* |

---

## 4. Failure Analysis & Error Categorization

Analysis of failure cases observed during evaluation:

### Case 1: Unseen Layout Vocabulary (Layout 3 Generalization)
- **Document:** `inv_026.png`, `inv_032.png`, `inv_035.png` (Test Split)
- **Field:** `invoice_no`
- **Ground Truth:** `BILL-4978`, `BILL-2229`, `BILL-9117`
- **Baseline Regex Output:** `None`
- **Cause:** Baseline regex strictly required `(Invoice|Inv\.?|Tax Invoice)`. In the held-out Layout 3, the invoice header is formatted as `Bill No. BILL-XXXX`. While tuning improved recognition on period-delimited patterns, OCR segmentation sometimes grouped `Bill No` separately from the identifier.

### Case 2: OCR Glyph Misrecognition on Currency Symbols
- **Document:** `inv_001.png` (Dev Split), `inv_021.png` (Test Split)
- **Field:** `total_amount`
- **Ground Truth:** `7840.0`, `743400.0`
- **Baseline Regex Output:** `None`
- **Cause:** EasyOCR frequently transcribed the Indian Rupee symbol `₹` as an open curly brace `{` or square bracket `[`. The baseline regex only allowed `₹?` or standard digits, discarding the line entirely.

### Case 3: OCR Underscore Segmentation on Currency Label
- **Document:** `inv_058.png` (Test Split)
- **Field:** `total_amount`
- **Ground Truth:** `250750.0`
- **Tuned Regex Output:** `None`
- **Cause:** The invoice image rendered `Total Amount:\nRs. 2,50,750.00`. Due to scan compression artifacts, EasyOCR misread `Rs.` as `Rs_` on an isolated line (`Total Amount:\nRs_\n2,50,750.00`). Because the parser expects the currency token adjacent to the numeric value, it failed to extract the amount.

### Case 4: Multi-Column Bounding Box Interleaving
- **Document:** `inv_002.png` (Dev Split), `inv_024.png` (Test Split)
- **Field:** `party`
- **Ground Truth:** `Thermax Industrial Shipping`, `Infosys BPM Global Freight`
- **Baseline Regex Output:** `Consignee:`
- **Cause:** In Layout 2 (Two-Column format), the left column contains `Buyer / Consignee:` followed by the party name, while the right column contains `Invoice Number:`. EasyOCR line sorting merged the two headers onto successive lines (`Buyer\nConsignee:\nInvoice Number: ...`), causing the baseline regex to capture `Consignee:` as the party name.

### Case 5: Word Boundary Truncation in Multi-Word Entities
- **Document:** `inv_045.png` (Test Split)
- **Field:** `party`
- **Ground Truth:** `Larsen & Toubro Heavy Cargo`
- **Tuned Regex Output:** `Larsen & Toubro Heavy`
- **Cause:** EasyOCR split the trailing word `Cargo` into a distinct bounding box with higher vertical spacing. The strict string match failed, though lenient substring matching correctly flagged it as a match.

### Case 6: Fields Not Handled by Heuristic Architecture
- **Fields:** `invoice_date`, `gstin`, `hs_code`
- **Accuracy:** `0.0%`
- **Cause:** Architectural limitation. `_fallback_regex_parse` in the current codebase only implements extraction rules for `invoice_no`, `total_amount`, and `party`. It does not contain regex patterns or validation logic for dates, 15-character GSTIN codes, or 4-digit HS codes.

---

## 5. Limitations

1. **Synthetic Nature of Dataset:** The dataset is synthetic and generated from 3 distinct templates using Pillow. While noise, rotation, and compression were applied, real-world supplier invoices exhibit higher variance in font, background contrast, scan skew, multi-page continuation, and stamp/signature occlusion.
2. **EasyOCR CPU Bottleneck:** EasyOCR running on CPU averaged ~4.8 seconds per page. In production, this step dominates latency unless accelerated by GPU or an external cloud OCR API.
3. **Absence of Gemini Empirical Data:** Due to an invalid API key, Gemini 2.5 Flash numbers could not be empirically measured. The comparison demonstrates the ceiling of rule-based regex parsing, particularly when encountering unseen wording or multi-column layouts.

# Next Phases Execution Notes

This document records deviations, test counts per language, environment details, and execution logs for Parts A, B, and C as required by `docs/NEXT_PHASES_PLAN.md`.

## Environment
- OS: Windows 11 (build architecture: AMD64)
- Java: OpenJDK 21.0.13 (Temurin)
- Maven: 3.9.x
- Python: 3.14.3
- Docker Desktop: v29.x (API v1.44)

## Test Counts by Language
- Java (Surefire): 19 tests passing (`com.logisticsauto:logistics-api`)
- Python (Pytest): 10 tests passing (`backend/tests/test_nlp.py`, `backend/tests/test_stream_worker.py`)

## Phase A2 Synthetic Dataset Spot Checks
Generated 60 synthetic invoices deterministically with seed 42 (20 dev, 40 test) using bundled fonts `DejaVuSans.ttf` and `DejaVuSerif.ttf`. Bit-identical verification passed across multiple runs.
Spot-checked 5 generated images:
1. `inv_001.png` (dev, Layout 1 - Tax Invoice): Clean header-table-footer format, invoice number `INV-2026-9928`, date `14/03/2026` (`2026-03-14`), total amount ₹7,840.00 (`7840.0`), party `Voltas Commercial Cargo Hub`.
2. `inv_010.png` (dev, Layout 2 - Two-Column Commercial Invoice): Two-column layout, invoice number `TX/26/8886`, date `28/03/2026` (`2026-03-28`), total amount Rs. 3,52,800.00 (`352800.0`), party `Adani Ports & Special Economic Zone`.
3. `inv_020.png` (dev, Layout 2 - Two-Column Commercial Invoice): Two-column layout, invoice number `TX/26/4185`, date `28/03/2026` (`2026-03-28`), total amount Rs. 3,86,400.00 (`386400.0`), party `Sundaram Fasteners Supply Chain`.
4. `inv_025.png` (test, Layout 2 - Two-Column Commercial Invoice): Two-column format with mild scan rotation and compression artifacts, invoice number `TX/26/3068`, date `11/03/2026` (`2026-03-11`), total amount Rs. 2,52,000.00 (`252000.0`), party `Reliance Logistics & Distribution`.
5. `inv_035.png` (test, Layout 3 - Held-out Bill of Supply): Held-out layout with alternative phrasing (`Bill No. BILL-9117`, `Billing Date: 28/03/2026`, `Amount Payable: INR 1,68,000.00`, `Customer Name: Apollo Tyres National Depot`, `Tax ID (GST)`, `HS Classification`).

## Runs and Status
- **Gemini Extraction Evaluation:** Recorded as **not run** because the provided `GEMINI_API_KEY` was rejected by the upstream Google GenAI API with `400 INVALID_ARGUMENT (API key not valid)`.
- **Regex Extraction Evaluation:** Executed on synthetic test split (40 images).

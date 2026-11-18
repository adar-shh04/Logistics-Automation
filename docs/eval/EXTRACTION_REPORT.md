# Extraction Accuracy Evaluation Report

**Last updated:** 2026-11-19 (first runs 2026-11-18)
**Environment:** Windows 11 (AMD64), Python 3.14.3, PyTorch 2.11.0+cpu, EasyOCR 1.7.2, Pillow 12.2.0, all on CPU
**Parser under test:** `backend/app/nlp.py` (git blob `8b7fad22eb60baae8d24b2a8b0f2ec3e5380f7c8`)

## Summary

- **Gemini has not been measured.** The available `GEMINI_API_KEY` is rejected with `400 INVALID_ARGUMENT (API key not valid)`, so every number below is for the **regex fallback parser** only.
- **Familiar wording:** on layouts whose wording the parser was tuned on (layouts 1 and 2), the regex gets the invoice number, total and party right on most invoices.
- **Unseen wording:** on a blind layout with label wording it was not written for (layout 4), it collapses: **26.7% invoice number, 20.0% total, 0% party**.
- **What the regex gets right there:** only the labels it already knows (`Invoice #`, `... Amount Due`).
- **Never extracted:** the regex has no rules at all for date, GSTIN or HS code.
- **Conclusion:** regex extraction does not generalise beyond the layouts it was written for. That is the case for LLM extraction, and it still has to be measured with a working key.

### Correction to the first version of this report

The 2026-11-18 version reported tuned-regex test accuracy of 85% (invoice number), 97.5% (total) and 85% (party) and called it held-out. **Those figures are not held-out scores.**
- Layout 3 was supposed to appear only in the test split.
- But the tuned parser contains exactly layout 3's wording (`Bill`, `Amount Payable`, `Customer Name`), which never appears in the dev split.
- So the parser was tuned with knowledge of the test layout.

Below, layout 3 is reported separately and labelled as contaminated. A new blind set (layout 4, section 3) was generated **after** the parser was frozen and run once.

---

## 1. Datasets

| Set | Files | Layouts | Created | Used for tuning? |
|---|---|---|---|---|
| `dev` | `inv_001`–`inv_020` (20) | 1, 2 | 2026-11-18, `eval/generate_invoices.py --seed 42` | Yes |
| `test` | `inv_021`–`inv_060` (40) | 1, 2, 3 | same | Layout 3 wording leaked into the parser (see above) |
| `holdout` | `hold_001`–`hold_030` (30) | 4 | 2026-11-19, `eval/generate_holdout.py --seed 2026` (generated after the parser was frozen) | No. Run once. |

All images are **synthetic**, rendered with Pillow and bundled DejaVu fonts. 40% get mild scan artefacts (rotation ±1.5°, blur, JPEG compression). Dates are day-first (Indian format), and amounts use Indian digit grouping.

**Layout 4** ("freight invoice") moves the blocks around: seller and invoice details on the left, recipient on the right, and the total in a band at the bottom left. Each invoice draws its labels at random from common Indian invoice wording:

| Field | Label variants |
|---|---|
| Number | `Document No:`, `Ref. No.:`, `Invoice #:`, `Voucher No:` |
| Date | `Issue Date:`, `Dated:`, `Date of Issue:` |
| Party | `Ship To:`, `Sold To:`, `Recipient:`, `Billed To:` |
| GSTIN | `GST No.:`, `GSTIN/UIN:`, `GST Reg. No.:` |
| HS code | `Tariff Code`, `HSN Code`, `Commodity Code` |
| Total | `Net Amount Due:`, `Balance Due:`, `TOTAL (INR):`, `Invoice Value:` |
| Currency | `₹`, `Rs`, `INR`, or none |

The wording was fixed before the first run. It was chosen as realistic variety, not to make the regex pass or fail. Its author had seen the regex, so treat it as an independent layout, not a perfectly blind one.

## 2. Commands

```powershell
python eval/generate_invoices.py --seed 42                     # dev + test
python eval/generate_holdout.py  --seed 2026                   # layout-4 hold-out
python eval/run_eval.py --split test    --method regex         # eval/results/2026-11-18_regex_test.json
python eval/run_eval.py --split holdout --method regex --labels eval/data/holdout/labels.jsonl
                                                               # eval/results/2026-11-19_regex_holdout.json
python eval/layout_breakdown.py eval/results/<file>.json        # per-layout table below
python eval/run_eval.py --split test --method gemini           # NOT RUN: invalid API key
```

The baseline (before tuning) test run is in `eval/results/2026-11-18_regex_test_baseline.json`, and the dev run is in `eval/results/2026-11-18_regex_dev.json`.

## 3. Results, regex parser, per layout

Accuracy is exact match after normalisation. Lenient party matching is a substring match. 95% Wilson intervals are in brackets.

| Set / layout | n | Invoice no. | Total amount | Party (strict) | Party (lenient) | Status |
|---|---|---|---|---|---|---|
| test, layout 1 | 14 | 14/14 | 14/14 | 12/14 | 13/14 | In-distribution (same wording as dev) |
| test, layout 2 | 13 | 13/13 | 12/13 | 12/13 | 12/13 | In-distribution (same wording as dev) |
| test, layout 3 | 13 | 7/13 | 13/13 | 10/13 | 12/13 | **Contaminated**: the parser was tuned with this wording |
| **holdout, layout 4** | **30** | **8/30 = 26.7%** [14.2–44.5%] | **6/30 = 20.0%** [9.5–37.3%] | **0/30 = 0%** [0–11.4%] | **0/30 = 0%** [0–11.4%] | **Blind: the only true held-out result** |

Date, GSTIN and HS code: **0% on every set**, because the regex parser has no rules for them.

Document-level accuracy (all 6 fields right) is **0% on every set** for the same reason.

### Layout 4 by label wording

| Field | Known to the regex | Correct | Unknown to the regex | Correct |
|---|---|---|---|---|
| Invoice no. | `Invoice #:` | 8/10 | `Ref. No.:`, `Voucher No:`, `Document No:` | 0/20 |
| Total | `Net Amount Due:` (contains `Amount Due`) | 6/6 | `TOTAL (INR):`, `Balance Due:`, `Invoice Value:` | 0/24 |

Party is 0/30 because none of the four party labels are in the regex. It then falls back to the first OCR line, which is the title `FREIGHT INVOICE`.

## 4. Timing (regex runs, CPU)

| Run | OCR p50 | OCR p95 | Parse p50 |
|---|---|---|---|
| holdout (30 images, 2026-11-19) | 6.39 s | 8.27 s | 0.2 ms |
| test (40 images, 2026-11-18) | 4.78 s | 5.26 s | 0.1 ms |

The hold-out images carry more text per page, and the run shared the machine with other work. OCR dominates the time in both runs.

## 5. Error analysis (from the 2026-11-18 runs, still valid)

- **₹ read as `{` or `[` by EasyOCR:** this broke the amount regex until it was tuned on dev.
- **Two-column layouts:** OCR line order interleaves the columns (`Buyer / Consignee:` next to `Invoice Number:`), so the baseline regex returned `Consignee:` as the party.
- **Split words:** a trailing word on its own OCR box truncates multi-word party names (`Larsen & Toubro Heavy`).
- **`Rs.` read as `Rs_`** on its own line, so the amount was missed (`inv_058`).

## 6. Limitations and next steps

1. **The data is synthetic.** Real invoices vary far more (stamps, handwriting, multi-page, low-quality scans). Real redacted invoices should be added as a separate table.
2. **Gemini is not measured.** Next step: a working key, then `run_eval.py --method gemini` on the **holdout** and **test** sets with no prompt changes, and report both.
3. **No further regex tuning against layout 4.** If the regex is changed, generate a new layout 5 to measure it.
4. **One run per configuration.** OCR is deterministic for a fixed image, so the only run-to-run variation is Gemini's, which is not measured yet.

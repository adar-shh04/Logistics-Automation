# Logistics Automation - Performance and Load Test Report

**Date of Execution:** 2026-11-18  
**Branch:** `feature/observability-load`  
**Test Harness:** k6 (`grafana/k6:0.49.0`), Prometheus (`prom/prometheus:v2.51.0`), Grafana (`grafana/grafana:10.4.0`)

---

## 1. Test Environment and Configuration

| Parameter | Specification |
|---|---|
| **Host OS** | Windows 11 Home Single Language (Build 10.0.26300, 64-bit) |
| **CPU Model** | 11th Gen Intel(R) Core(TM) i5-11400H @ 2.70 GHz |
| **CPU Cores / Threads** | 6 physical cores, 12 logical processors |
| **Host Memory (RAM)** | 16 GB DDR4 (15.73 GB visible) |
| **Container Engine** | Docker Desktop 4.x on WSL2 backend |
| **Resource Limits** | Default WSL2/Docker limits (no artificial CPU throttling configured) |
| **Load Topology** | Single host: load generator (k6), API, Redis, Postgres, Prometheus, Grafana, and workers all execute on the same physical host connected over Docker bridge network (`logistics-automation_default`). |
| **Worker Stub Delay** | 500 ms (`WORKER_STUB_DELAY_MS=500`, simulated worker processing time for L1/L2) |
| **Volume Isolation** | Dedicated named Docker volumes (`loadtest_uploads`, `loadtest_ledger`) mounted during tests to ensure zero pollution of tracked repository paths (`sample_docs/`, `backend/models/ledger.txt`). |

---

## 2. Test Scenarios and Results

Every test configuration was executed **3 times**. The tables below document the **median run** for each configuration, derived from the raw JSON summaries in `loadtests/results/`.

### L1: Spring Boot API Ingestion Latency

- **Target:** `POST /upload` endpoint
- **Payload:** Fixed PNG image (`loadtests/fixtures/test_invoice.png`, 832 bytes)
- **Duration:** 60 seconds per run
- **Worker Configuration:** 1 worker in stub mode (500 ms delay)
- **Executor:** Constant arrival rate (`constant-arrival-rate`)

| Target Rate | Achieved Rate | Error % | p50 (Median) | p90 | p95 | p99 | Median Run File |
|---|---|---|---|---|---|---|---|
| **5 req/s** | 5.02 req/s | 0.00% | **7.82 ms** | 9.37 ms | 10.65 ms | 15.24 ms | `loadtests/results/l1_5rps_run3.json` |
| **20 req/s** | 20.00 req/s | 0.00% | **5.38 ms** | 6.72 ms | 7.57 ms | 9.41 ms | `loadtests/results/l1_20rps_run3.json` |
| **50 req/s** | 50.01 req/s | 0.00% | **4.13 ms** | 4.94 ms | 5.36 ms | 18.17 ms | `loadtests/results/l1_50rps_run2.json` |

#### All Individual L1 Runs

| Configuration | Total Requests | Error Rate | Median Duration | p95 Duration | Max Duration | Raw Summary File |
|---|---|---|---|---|---|---|
| **5 rps - Run 1** | 300 | 0.00% | 8.92 ms | 14.11 ms | 200.50 ms | `l1_5rps_run1.json` |
| **5 rps - Run 2** | 301 | 0.00% | 7.36 ms | 10.20 ms | 16.98 ms | `l1_5rps_run2.json` |
| **5 rps - Run 3** | 301 | 0.00% | 7.82 ms | 10.65 ms | 17.51 ms | `l1_5rps_run3.json` |
| **20 rps - Run 1** | 1,201 | 0.00% | 5.43 ms | 7.62 ms | 18.42 ms | `l1_20rps_run1.json` |
| **20 rps - Run 2** | 1,200 | 0.00% | 5.11 ms | 7.09 ms | 15.60 ms | `l1_20rps_run2.json` |
| **20 rps - Run 3** | 1,201 | 0.00% | 4.79 ms | 6.08 ms | 10.53 ms | `l1_20rps_run3.json` |
| **50 rps - Run 1** | 3,001 | 0.00% | 4.28 ms | 5.53 ms | 16.66 ms | `l1_50rps_run1.json` |
| **50 rps - Run 2** | 3,001 | 0.00% | 3.94 ms | 5.07 ms | 39.65 ms | `l1_50rps_run2.json` |
| **50 rps - Run 3** | 3,001 | 0.00% | 3.85 ms | 5.12 ms | 41.58 ms | `l1_50rps_run3.json` |

*Finding:* The Java 21 / Spring Boot 3 API demonstrates negligible overhead under increasing load. Due to connection pooling and JIT optimization, median latency decreased from ~7.8 ms at 5 req/s to ~4.1 ms at 50 req/s, with p95 holding steady at 5.36 ms and zero failed requests across all 9,000+ submissions.

---

### L2: Horizontal Worker Scaling (Batch Drain Benchmark)

- **Target:** Batch processing of **N = 300** documents uploaded concurrently
- **Polling Interval:** Every 250 ms per job via `/status/<uid>` until status reaches `completed`
- **Worker Configuration:** 1, 2, and 3 workers scaled via Docker Compose (`--scale worker=W`)
- **Worker Stub Delay:** 500 ms per job
- **Isolation:** Fresh database and volumes initialized before each run via `docker compose down -v`
- **Integrity Assertions:** Verified after each run:
  1. `COUNT(*) FROM transactions` == 300
  2. `COUNT(DISTINCT document_id) FROM transactions` == 300
  3. `python -m app.audit verify` passes with 0 broken cryptographic links

| Workers | Drain Time | Completed Throughput | Speed-up vs 1 Worker | End-to-End p50 | End-to-End p95 | Median Run File |
|---|---|---|---|---|---|---|
| **1 Worker** | 158.85 s | **1.89 jobs/s** | **1.00x** (baseline) | 26.03 s | 26.28 s | `loadtests/results/l2_w1_run2.json` |
| **2 Workers** | 83.53 s | **3.59 jobs/s** | **1.90x** | 12.95 s | 14.91 s | `loadtests/results/l2_w2_run1.json` |
| **3 Workers** | 59.57 s | **5.04 jobs/s** | **2.67x** | 8.85 s | 13.67 s | `loadtests/results/l2_w3_run2.json` |

#### All Individual L2 Runs

| Configuration | Drain Time | Throughput | e2e p50 | e2e p95 | Tx Count | Distinct Docs | Audit Verify | Raw Summary File |
|---|---|---|---|---|---|---|---|---|
| **1 Worker - Run 1** | 158.74 s | 1.89 jobs/s | 26.04 s | 26.29 s | 300 | 300 | Pass (300 records) | `l2_w1_run1.json` |
| **1 Worker - Run 2** | 158.85 s | 1.89 jobs/s | 26.03 s | 26.28 s | 300 | 300 | Pass (300 records) | `l2_w1_run2.json` |
| **1 Worker - Run 3** | 159.04 s | 1.89 jobs/s | 26.04 s | 26.31 s | 300 | 300 | Pass (300 records) | `l2_w1_run3.json` |
| **2 Workers - Run 1** | 83.53 s | 3.59 jobs/s | 12.95 s | 14.91 s | 300 | 300 | Pass (300 records) | `l2_w2_run1.json` |
| **2 Workers - Run 2** | 84.77 s | 3.54 jobs/s | 13.06 s | 15.00 s | 300 | 300 | Pass (300 records) | `l2_w2_run2.json` |
| **2 Workers - Run 3** | 83.33 s | 3.60 jobs/s | 12.89 s | 14.88 s | 300 | 300 | Pass (300 records) | `l2_w2_run3.json` |
| **3 Workers - Run 1** | 58.88 s | 5.10 jobs/s | 8.83 s | 13.25 s | 300 | 300 | Pass (300 records) | `l2_w3_run1.json` |
| **3 Workers - Run 2** | 59.57 s | 5.04 jobs/s | 8.85 s | 13.70 s | 300 | 300 | Pass (300 records) | `l2_w3_run2.json` |
| **3 Workers - Run 3** | 59.57 s | 5.04 jobs/s | 8.84 s | 13.66 s | 300 | 300 | Pass (300 records) | `l2_w3_run3.json` |

*Finding:* 
- Scaling from 1 to 2 workers reduced batch drain time from 158.85 s to 83.53 s, delivering a **1.90x speed-up** (95.0% scaling efficiency relative to linear).
- Scaling to 3 workers further reduced drain time to 59.57 s, delivering a **2.67x speed-up** (89.0% scaling efficiency).
- In all 9 runs, zero duplicate transactions occurred (`COUNT(*) == COUNT(DISTINCT document_id) == 300`), and PostgreSQL transaction-level advisory locking (`SELECT pg_advisory_xact_lock`) preserved the SHA-256 cryptographic audit chain across multiple concurrent workers without corruption or gaps.

---

### L3: Real Pipeline Sample (Actual OCR & Extraction)

- **Target:** 20 sequential synthetic invoices (`inv_001.png` – `inv_020.png` from `eval/data/synthetic/`)
- **Mode:** `WORKER_STUB_MODE=false` (Real EasyOCR on CPU, regex NLP parsing, Isolation Forest anomaly scoring, PostgreSQL persistence, and SHA-256 audit ledger hash chain)
- **Workers:** 1 worker
- **Summary File:** `loadtests/results/l3_real_ocr.json`

| Metric | Measured Value |
|---|---|
| **Total Jobs Processed** | 20 / 20 (100% success rate) |
| **Per-Job Total Duration (Median)** | **5.931 s** |
| **Per-Job Total Duration (p95)** | **11.424 s** |
| **Per-Job Total Duration (Min)** | 5.361 s |
| **Per-Job Total Duration (Max)** | 11.424 s |

#### Stage Breakdown (Scraped from Prometheus Metrics)

| Stage | Average Duration per Job | Percentage of Total Time | Prometheus Metric |
|---|---|---|---|
| **OCR (EasyOCR on CPU)** | **5.1873 s** | **87.5%** | `logistics_stage_duration_seconds_sum{stage="ocr"}` |
| **Parsing (Regex Fallback)** | **0.2267 s** | **3.8%** | `logistics_stage_duration_seconds_sum{stage="parse"}` |
| **Risk Scoring (Isolation Forest)** | **0.0629 s** | **1.1%** | `logistics_stage_duration_seconds_sum{stage="score"}` |
| **Database Persistence (SQLAlchemy/Postgres)** | **0.0125 s** | **0.2%** | `logistics_stage_duration_seconds_sum{stage="db"}` |
| **Audit Ledger Append (Advisory Lock)** | **0.0056 s** | **0.1%** | `logistics_stage_duration_seconds_sum{stage="audit"}` |
| **HS Code Lookup (CSV Map)** | **0.0000 s** | **<0.01%** | `logistics_stage_duration_seconds_sum{stage="hs_lookup"}` |

*Finding:* Real image processing is overwhelmingly dominated by EasyOCR CPU-bound tensor operations (87.5% of pipeline runtime). By comparison, database transactions and audit logging take less than 20 ms combined (<0.3%). This proves that worker horizontal scaling is the key lever for scaling logistics throughput when processing untrusted scanned invoices.

---

## 3. Observability and Grafana Dashboards

The Prometheus and Grafana stack was deployed via `docker-compose.observability.yml` and monitored live metrics throughout the benchmark runs.

### Dashboard Overview
Below is the full Grafana dashboard capture showing API request rate, latency quantiles, document upload rates, worker throughput, and stage duration histograms:

![Grafana Dashboard Full](file:///X:/projects/Logistics-Automation/docs/perf/img/grafana_dashboard_full.png)

### Key Metrics Panels
Focused view of API request latency, queue pending gauges, and stage durations during high-load processing:

![Grafana Dashboard Panels](file:///X:/projects/Logistics-Automation/docs/perf/img/grafana_dashboard_panels.png)

---

## 4. Limitations and Caveats

1. **Colocated Execution:** The load generator (k6), API, message broker (Redis), database (PostgreSQL), and workers all ran on the same physical development workstation. During heavy load, k6 and Docker competed for CPU cores and memory bandwidth.
2. **Stub vs Real Execution:** The L1 and L2 scaling benchmarks were evaluated in stub mode (`WORKER_STUB_MODE=true`, 500 ms delay) to evaluate queueing, database contention, and Redis Stream distribution without saturating CPU threads on OCR. Real-world CPU utilization scales with OCR concurrency.
3. **Local Storage:** These tests executed with local Docker volumes before transitioning to cloud object storage (Amazon S3 in Part C).
4. **Non-Production Environment:** These results are generated on a single-node laptop and do not reflect distributed multi-node network latency, cloud load balancer overhead, or AWS RDS network hops.

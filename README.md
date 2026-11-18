# 🌐 LogisticsAuto

A prototype that automates the digitization, parsing, and risk scoring of international trade documents such as invoices.

[![GitHub Repo](https://img.shields.io/badge/GitHub-Logistics--Automation-blue?logo=github)](https://github.com/adar-shh04/Logistics-Automation)
![Project Overview](logistics-automation-overview.png)

## 🎯 Project Overview
**LogisticsAuto** takes an uploaded document, extracts its text and key fields in a background worker, scores the transaction for risk, and shows the result on a dashboard.

### 📑 Engineering Reports
The system includes three comprehensive engineering evaluation and deployment reports:
- 📊 **[Extraction Accuracy Evaluation Report](docs/eval/EXTRACTION_REPORT.md)**: Quantitative evaluation of invoice extraction across 60 synthetic invoices, measuring Wilson 95% confidence intervals, regex vs. LLM error profiles, and OCR noise degradation.
- ⚡ **[Load Testing & Scaling Report](docs/perf/LOAD_TEST_REPORT.md)**: End-to-end performance benchmarks using k6 across 5, 20, and 50 RPS, worker horizontal scaling efficiency (1–3 replicas), Prometheus & Grafana observability, and real OCR execution timings.
- ☁️ **[AWS Production Deployment Guide](docs/DEPLOY.md)**: Complete Infrastructure-as-Code (Terraform) in `ap-south-1` (Mumbai), Amazon S3 object storage, Amazon ECR container pipelines, GitHub Actions OIDC federation, SSM Parameter Store secrets, and multi-layer rate limiting.

### ✅ What It Does
- **Asynchronous stream processing**: uploads return immediately while a Python worker processes tasks dispatched through a Redis Stream.
- **Pluggable object storage**: supports local filesystem storage and private Amazon S3 buckets (AWS SDK v2 for Java, boto3 for Python).
- **Structured extraction**: EasyOCR reads text from invoice images and Gemini extracts fields such as invoice number, amount, party, and HS code.
- **Risk scoring**: an Isolation Forest model scores each transaction from 0 to 1 and flags scores above 0.6.
- **HS code lookup**: extracted codes are matched against a sample CSV to attach item descriptions.
- **Audit trail & concurrency control**: each processed document is written to PostgreSQL with advisory row locks and appended to a SHA-256 hash-chained ledger file.

> **Status:** this is a portfolio prototype. It has not been benchmarked or used on production shipments, so no accuracy, speed, or cost figures are claimed. The Isolation Forest is trained on synthetic data (`backend/app/train_model.py`), and the HS code table is a sample.

---

## 🏗️ Technical Architecture

### Component Diagram

```
React Dashboard (Vite / Nginx)
          │
          ▼  HTTP (Port 80 / 8000)
Spring Boot 3 API (Java 21) ─────────────► Amazon S3 / LocalStack (Uploads)
     │                     │
     │ JPA / Flyway        │ XADD (logistics:jobs)
     ▼                     ▼
PostgreSQL 15          Redis 7 Stream
     ▲                     │
     │ Advisory Lock       │ XREADGROUP (group "workers")
     │ Results & Status    ▼
Python Stream Worker Replicas (EasyOCR + Gemini + Isolation Forest)
     │
     └─────────────────────► SHA-256 Hash-Chained Audit Ledger
```

### AWS Cloud Production Topology

```
Internet ──► Security Group (Inbound 80/443, Port 22 Closed)
                 │
                 ▼
         EC2 Instance (Amazon Linux 2023 - t3.large)
         ┌──────────────────────────────────────────────────────────┐
         │ Nginx Reverse Proxy (Port 80)                            │
         │   ├── /api/ ──────────► Spring Boot 3 API (Port 8000)    │
         │   └── / ──────────────► React Frontend (Static SPA)      │
         │                                                          │
         │ Redis 7 ◄─────────────► Python Stream Workers (3x)       │
         │                              │                           │
         │ PostgreSQL 15 ◄──────────────┘                           │
         └──────────────────────────────────────────────────────────┘
                 │                         │
                 ▼                         ▼
         Amazon S3 Bucket          AWS Systems Manager
         (Uploads, SSE-S3)         (SSM Parameter Store Secrets)
```

### 🧠 Services & Components
- **API (`api-java/`)**: Java 21 & Spring Boot 3.4 REST service handling document upload, job dispatch to Redis Streams, status checks, transaction queries, API key authentication, rate limiting, and Flyway database migrations (`V1__init.sql`).
- **PostgreSQL 15 (`db`)**: stores documents, transactions, and audit records with advisory transaction locking.
- **Redis 7 (`redis`)**: Redis Stream (`logistics:jobs`) message broker between the API and worker replicas.
- **Worker (`backend/`)**: Python stream worker consuming jobs with `XREADGROUP` and `XAUTOCLAIM`, running OCR, Gemini parsing, HS code lookup, Isolation Forest scoring, and ledger hashing.
- **Observability (`observability/`)**: Prometheus scraping metrics from the API and Python worker, visualised in a curated Grafana dashboard.
- **Storage Abstraction**: Seamlessly toggles between local filesystem and Amazon S3 via `STORAGE_TYPE=local|s3`.

---

## 🔄 The End-to-End Flow

1. **Upload**: A PNG or JPG invoice is uploaded via `POST /upload`. The Spring Boot API validates file type and size, generates a unique UID, saves the image to S3 (or local disk), records the document row in PostgreSQL, and enqueues a job with `XADD` onto Redis Stream `logistics:jobs`.
2. **Stream Consumer**: Python worker replicas consume jobs from `logistics:jobs` using consumer group `workers`.
3. **Idempotency Check**: If a transaction already exists for `document_id`, the worker marks the document completed and ACKs immediately to prevent duplicate transactions or ledger entries.
4. **Processing Pipeline**:
   - **OCR**: EasyOCR extracts text from image bytes.
   - **Gemini**: Parses text into structured fields.
   - **HS Code**: Looks up classification from `hs_codes.csv`.
   - **Risk Scoring**: Isolation Forest scores transaction features.
5. **Atomic Persistence**: The worker records the `transactions` entry under a PostgreSQL transaction advisory lock, updates `documents.status='completed'`, and appends to the hash-chained audit ledger.
6. **Result Display**: The React frontend polls `GET /status/{uid}` and displays formatted transaction totals and risk indicators.

---

## 🛠️ Running the Application

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Google Gemini API Key](https://aistudio.google.com/app/apikey)

### Quick Start (Standard Mode)
1. **Environment Setup**:
   ```bash
   cp .env.example .env
   # Add your GEMINI_API_KEY to .env
   ```

2. **Launch with Docker Compose**:
   ```bash
   docker compose down -v
   docker compose up --build -d
   ```

3. **Access Points**:
   - **Dashboard**: `http://localhost:5173`
   - **API Health**: `http://localhost:8000/health`
   - **Prometheus Metrics**: `http://localhost:8000/actuator/prometheus`
   - **Swagger UI**: `http://localhost:8000/swagger-ui.html`

### Observability Stack (Prometheus & Grafana)
To launch the full observability stack:
```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d
```
- **Grafana Dashboard**: `http://localhost:3000` (credentials: `admin` / `admin`)
- **Prometheus Targets**: `http://localhost:9090/targets`

---

## 🧪 Running Tests

### Java API Tests
Run all 27 unit and Testcontainers integration tests (requires Docker running for PostgreSQL and Redis):
```bash
cd api-java
./mvnw test
```

### Python Worker Tests
Run all 27 pytest unit and integration tests (uses fakeredis, stubs OCR and Gemini, and moto for S3):
```bash
pytest backend/tests -v
```

### Audit Ledger Hash Chain Verification
Verify the SHA-256 hash chaining of the audit ledger:
```bash
python -m backend.app.audit verify
```

---

*Developed by [adar-shh04](https://github.com/adar-shh04)*

# 🌐 LogisticsAuto

A prototype that automates the digitization, parsing, and risk scoring of international trade documents such as invoices.

[![GitHub Repo](https://img.shields.io/badge/GitHub-Logistics--Automation-blue?logo=github)](https://github.com/adar-shh04/Logistics-Automation)
![Project Overview](logistics-automation-overview.png)

## 🎯 Project Overview
**LogisticsAuto** takes an uploaded document, extracts its text and key fields in a background worker, scores the transaction for risk, and shows the result on a dashboard.

### ✅ What It Does
- **Asynchronous processing**: uploads return immediately while a Celery worker runs OCR, parsing, and scoring.
- **Structured extraction**: EasyOCR reads the text and Gemini 2.5 Flash turns it into fields such as invoice number, amount, party, and HS code.
- **Risk scoring**: an Isolation Forest model scores each transaction from 0 to 1 and flags scores above 0.6.
- **HS code lookup**: extracted codes are matched against a small sample CSV to attach a description.
- **Audit trail**: each processed document is written to the database and to a SHA-256 hash-chained ledger file.

> **Status:** this is a portfolio prototype. It has not been benchmarked or used on production shipments, so no accuracy, speed, or cost figures are claimed. The Isolation Forest is trained on synthetic data (`backend/app/train_model.py`), and the HS code table is a sample.

---

## 🏗️ Technical Architecture (Dockerized)

**Docker Compose** runs five services: `db`, `redis`, `backend`, `worker`, and `frontend`.

### 🧠 Backend
- **FastAPI**: REST API for document uploads, status polling, and transaction details.
- **PostgreSQL 15**: stores documents, transactions, and audit records.
- **Redis 7**: message broker between the API and the worker.
- **Celery Worker**: runs OCR, parsing, and scoring outside the request cycle.
- **Pydantic v2**: settings and response schemas.
- **SQLAlchemy 2.0**: ORM for the database models.

### 🎨 Frontend
- **React 18 & Vite**: the dashboard application.
- **Tailwind CSS v4**: styling.
- **Status polling**: the dashboard polls the API to show document status and risk scores.

### 🤖 AI & Machine Learning Pipeline
- **EasyOCR**: extracts raw text from uploaded documents.
- **Google Gemini 2.5 Flash**: parses the text into structured fields.
- **Isolation Forest (Scikit-Learn)**: produces the anomaly-based risk score.

---

## 🔄 The End-to-End Flow

1.  **Upload**: a document is uploaded through the dashboard and saved to the `/data/uploads` volume.
2.  **Dispatch**: the API queues a Celery task through **Redis**.
3.  **Processing**:
    *   **OCR** extracts the raw text.
    *   **Gemini** extracts the structured fields.
    *   The **HS code** is looked up in the sample table.
    *   **Isolation Forest** scores the transaction and flags high-risk results.
4.  **Storage**: the results are saved to **PostgreSQL** and appended to the hash-chained audit ledger.
5.  **Display**: the dashboard picks up the result through polling.

---

## 🛠️ Deployment Guide

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Google Gemini API Key](https://aistudio.google.com/app/apikey)

### Quick Start
1.  **Environment Setup**:
    ```bash
    cp .env.example .env
    # Edit .env and add your GEMINI_API_KEY
    ```

2.  **Launch Cluster**:
    ```bash
    docker-compose up --build -d
    ```

3.  **Access Points**:
    - **Dashboard**: `http://localhost:5173`
    - **API Docs**: `http://localhost:8000/docs`

---

*Developed by [adar-shh04](https://github.com/adar-shh04)*

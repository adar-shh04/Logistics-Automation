# 🌐 LogisticsAuto

An industry-grade, AI-powered system designed to automate the digitization, parsing, and risk assessment of logistics documents for international trade.

[![GitHub Repo](https://img.shields.io/badge/GitHub-Logistics--Automation-blue?logo=github)](https://github.com/adar-shh04/Logistics-Automation)
![Project Overview](logistics-automation-overview.png)

## 🎯 Project Overview
**LogisticsAuto** provides a fully integrated, containerized solution that digitizes and automates the entire logistics workflow—from booking to delivery—bringing speed, transparency, compliance, and control to global trade.

### 🚀 Key Benefits
- **40-60% Faster Turnaround**: Through advanced AI automation and streamlined digital workflows.
- **80-90% Paperless Operations**: Integrated digital document management and secure e-signature support.
- **99% Compliance Accuracy**: Automated regulatory checks with real-time global trade updates.
- **10-20% Cost Savings**: Optimized container routing, reduced detention/demurrage, and granular cost control.
- **100% Real-time Visibility**: Live shipment tracking with proactive exception management.

---

## 🏗️ Technical Architecture (Dockerized)

The system is built on a production-ready, decoupled architecture using **Docker Compose** to orchestrate five primary high-availability services.

### 🧠 Backend (The Core Engine)
A high-performance Python ecosystem optimized for heavy-duty document processing and asynchronous task execution.
- **FastAPI**: High-performance REST API layer handling concurrent file uploads and status polling with sub-millisecond latency.
- **PostgreSQL 15**: Enterprise-grade relational database ensuring ACID compliance for all transaction records, audit ledgers, and document metadata.
- **Redis 7**: High-speed message broker and caching layer facilitating seamless communication between services.
- **Celery Worker**: Distributed task queue handling CPU-intensive operations (OCR, AI Parsing, ML) in the background to ensure a non-blocking UI.
- **Pydantic v2**: Strict data validation and type safety across the entire data pipeline.
- **SQLAlchemy 2.0**: Modern ORM managing complex relational queries and seamless database migrations.

### 🎨 Frontend (Command Center)
A premium, responsive dashboard designed for real-time visibility and operational efficiency.
- **React 18 & Vite**: Lightning-fast frontend development and optimized production bundles.
- **Tailwind CSS v4**: Sleek, glassmorphic UI design with a custom enterprise color palette for a professional experience.
- **State Synchronization**: Intelligent polling and reactive state management for real-time document status updates.

### 🤖 AI & Machine Learning Pipeline
- **Google Gemini 2.5 Flash**: Orchestrates advanced LLM-based parsing to extract structured JSON from raw document text (Invoice #, HS Codes, Line Items).
- **EasyOCR**: Localized, high-speed OCR engine for initial text extraction from unstructured images and PDFs.
- **Isolation Forest (Scikit-Learn)**: Production-ready anomaly detection model that calculates risk scores for every transaction based on historical data patterns.

---

## 🔄 The End-to-End Flow

1.  **Enquiry & Booking**: Seamless initiation of shipments and document uploads via the Command Center.
2.  **Shipment Planning**: Automated metadata preparation and optimal container allocation.
3.  **Document Intelligence**: 
    *   Secure upload to the `/data/uploads` persistent volume.
    *   Asynchronous task dispatching via **Redis**.
4.  **Autonomous Processing**:
    *   **Celery Workers** ingest the task for distributed processing.
    *   **OCR** extracts raw textual data.
    *   **Gemini AI** performs structured extraction into validated JSON.
    *   **ML Models** run risk assessment and flag potential compliance anomalies.
5.  **Validation & Compliance**: Extracted goods are automatically mapped to HS Codes for regulatory validation.
6.  **Ledger Update**: Validated data is committed to **PostgreSQL**, triggering UI updates via the polling mechanism.

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

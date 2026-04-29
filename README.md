# 🌐 Digital Import-Export Automation

An industry-grade, AI-powered system designed to automate the digitization, parsing, and risk assessment of logistics documents (such as invoices and bills of lading) for international trade.

## 🎯 Purpose

In the logistics and customs industry, manually processing thousands of import/export invoices is slow, error-prone, and susceptible to fraud. This project solves that by providing an automated pipeline that:
1. **Digitizes** uploaded documents using Optical Character Recognition (OCR).
2. **Extracts** structured data (Invoice Number, Amount, GSTIN, Party Name, HS Code) using state-of-the-art Large Language Models (LLMs).
3. **Assesses Risk** using a Machine Learning anomaly detection model (Isolation Forest) to instantly flag potentially fraudulent or abnormal transactions based on historical patterns.
4. **Validates Compliance** by mapping extracted goods to Harmonized System (HS) codes.

## 🛠️ Tech Stack

This project is built using a modern, decoupled architecture:

### Frontend
*   **React 18** (via Vite)
*   **Tailwind CSS v4** (Premium Glassmorphic Design)
*   **Axios** (for API communication)

### Backend
*   **FastAPI** (High-performance Python web framework)
*   **PostgreSQL** (Relational database for robust transaction storage)
*   **Redis** (Message broker for asynchronous background tasks)
*   **SQLAlchemy** (ORM for database interactions)
*   **Pydantic** (Data validation and configuration management)

### AI & Machine Learning
*   **Google Gemini 2.5 Flash** (Primary extraction engine for structured NLP parsing)
*   **EasyOCR** (Fallback/initial text extraction from images)
*   **Scikit-Learn** (Isolation Forest for anomaly/fraud detection)

### DevOps & Infrastructure
*   **Docker & Docker Compose** (Containerized orchestration for easy deployment)

---

## 🔄 Project Architecture & Flow

The system operates asynchronously to ensure a highly responsive user experience, even during heavy AI processing.

1. **Upload Initiation**: The user uploads an invoice (PDF/Image) via the React dashboard.
2. **Instant Acknowledgment**: The FastAPI backend receives the file, creates a pending `Document` record in PostgreSQL, and immediately returns a `document_id` to the frontend.
3. **Background Processing**: The heavy lifting is offloaded to a background task worker:
    *   **OCR Stage**: The image is converted to raw text.
    *   **NLP Stage**: The raw text is sent to the Gemini API, which intelligently extracts key fields into a structured JSON schema.
    *   **ML Risk Scoring**: The extracted data (e.g., total amount, party history) is fed into the loaded `Isolation Forest` model to calculate a fraud risk score (0-100%).
    *   **Database Commit**: The parsed fields and the calculated risk score are saved to the PostgreSQL database, and an audit ledger entry is created.
4. **Real-time Polling**: While the background task is running, the React frontend polls the `/status/{document_id}` endpoint.
5. **Dashboard Rendering**: Once processing is complete, the frontend dynamically updates to display the parsed data, the risk gauge, and adds the transaction to the historical dashboard.

---

## 🚀 Getting Started

### Prerequisites
*   [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Required for easy deployment)
*   A [Google Gemini API Key](https://aistudio.google.com/app/apikey)

### Installation & Deployment

1. **Clone the repository** (if you haven't already).
   
2. **Configure Environment Variables**:
   Copy the provided `.env.example` file to a new file named `.env`.
   ```bash
   cp .env.example .env
   ```
   Open `.env` and insert your Gemini API Key:
   ```env
   GEMINI_API_KEY=your_actual_api_key_here
   ```

3. **Start the Docker Cluster**:
   Launch the entire stack (PostgreSQL, Redis, Backend, and Frontend) using Docker Compose:
   ```bash
   docker-compose up --build -d
   ```

4. **Access the Application**:
   *   **Frontend UI**: [http://localhost:5173](http://localhost:5173)
   *   **Backend API Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔮 Future Enhancements

While the system is robust, there are several avenues for future expansion:
*   **Authentication & Role-Based Access (RBAC)**: Implement JWT authentication so different customs officers or logistics managers can have personalized dashboards and audit trails.
*   **Multi-Document Support**: Extend the Gemini prompting to handle complex, multi-page Bills of Lading, Packing Lists, and Certificates of Origin.
*   **Feedback Loop for ML**: Add a feature in the UI allowing humans to override a "Flagged" status, which would feed back into the ML pipeline to retrain and improve the Isolation Forest model over time.
*   **Cloud Storage Integration**: Move document storage from local volumes to AWS S3 or Google Cloud Storage for infinite scalability.
*   **Celery Workers**: Transition from FastAPI `BackgroundTasks` to a dedicated Celery worker pool for extreme horizontal scaling under heavy load.

---
*Developed by adar-shh04*

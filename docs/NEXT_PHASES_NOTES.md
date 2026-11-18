# Next Phases Execution Notes

This document records deviations, test counts per language, environment details, and execution logs for Parts A, B, and C as required by `docs/NEXT_PHASES_PLAN.md`.

---

## 1. Environment

- **Operating System:** Windows 11 (build architecture: AMD64)
- **Java Runtime & SDK:** OpenJDK 21.0.13 (Eclipse Temurin)
- **Build Tool:** Apache Maven 3.9.x
- **Python Runtime:** Python 3.11 / 3.14 (Docker container runtime: 3.11.18 Debian Bookworm)
- **Container Daemon:** Docker Desktop v29.x (API v1.44)
- **Terraform:** HashiCorp Terraform v1.7+ (AWS Provider ~> 5.40)

---

## 2. Test Counts by Language

A total of **54 automated unit and integration tests** pass with **0 failures and 0 errors** across both languages.

### Java API Suite (`api-java`): 27 Passing Tests
Executed via Maven Surefire and Testcontainers (PostgreSQL 15 & Redis 7):
- `com.logisticsauto.api.DocumentControllerTest`: 5 tests (REST endpoints, validation, upload handling)
- `com.logisticsauto.api.DocumentRepositoryTest`: 2 tests (JPA repository queries)
- `com.logisticsauto.api.FileStorageServiceTest`: 2 tests (local disk storage operations)
- `com.logisticsauto.api.HealthControllerTest`: 2 tests (application and dependency health checks)
- `com.logisticsauto.api.LocalStorageServiceTest`: 3 tests (StorageService local abstraction)
- `com.logisticsauto.api.S3StorageServiceTest`: 3 tests (StorageService AWS S3 abstraction)
- `com.logisticsauto.api.S3UploadIntegrationTest`: 1 test (End-to-end upload with S3 storage mode)
- `com.logisticsauto.api.SecurityFilterTest`: 5 tests (API Key authentication and rate limiting)
- `com.logisticsauto.api.TransactionRepositoryTest`: 3 tests (JPA transaction queries)
- `com.logisticsauto.api.UploadIntegrationTest`: 1 test (End-to-end upload and stream job publishing)

### Python Worker Suite (`backend/tests`): 27 Passing Tests
Executed via Pytest with fakeredis and moto[s3]:
- `backend/tests/test_audit.py`: 3 tests (hash chain integrity, 3-worker concurrency locking, tamper detection)
- `backend/tests/test_nlp.py`: 6 tests (regex extraction, keyword variations, malformed handling, Gemini missing key exception, fallback tagging, success tagging)
- `backend/tests/test_scoring.py`: 8 tests (string normalization, amount parsing, date normalization, party matching, Wilson score confidence intervals, document scoring)
- `backend/tests/test_storage.py`: 4 tests (local file reading, file URI resolution, missing file handling, S3 object retrieval via moto)
- `backend/tests/test_stream_worker.py`: 6 tests (success ACK and persistence, retry attempt incrementation, max retry failure marking, idempotency deduplication, stub mode default, stub mode execution)

### Ledger Integrity
- `python -m audit verify`: Successfully verified 25 audit records with complete SHA-256 hash chaining and zero breaks.

---

## 3. Plan Deviations and Engineering Decisions

1. **Local S3 Emulation (LocalStack 3.0 vs MinIO):**
   - *Plan Proposal:* MinIO container for local S3 emulation.
   - *Deviation:* Recent Docker Hub rate limits and distribution changes on MinIO require specialized authentication flags. LocalStack 3.0 (`localstack/localstack:3.0`) was selected instead. It provides exact AWS S3 API fidelity, starts in under 3 seconds, and supports init hook scripts (`/etc/localstack/init/ready.d/init-s3.sh`) to automatically create the development bucket on container startup.
2. **PyTorch CPU-Only Wheel Optimization:**
   - *Plan Proposal:* Standard `pip install torch torchvision`.
   - *Deviation:* Standard PyPI PyTorch packages bundle ~2.5 GB of CUDA / cuDNN libraries that are unused in CPU-only container environments. Installing from `--index-url https://download.pytorch.org/whl/cpu` reduced the download size to ~209 MB, cutting container build time from >10 minutes to ~30 seconds.
3. **Spring Security Filter Isolation:**
   - *Issue:* Marking custom filters (`ApiKeyAuthFilter`, `RateLimitFilter`) with `@Component` causes Spring Boot slice tests (`@WebMvcTest`) to register them without property injection.
   - *Deviation:* Filters are registered via `FilterRegistrationBean` inside a dedicated `@Configuration` class (`SecurityFilterConfig`). This provides clean URL pattern matching, strict ordering, and isolates controller unit tests.
4. **Spring Boot 3 Unmatched Route Handling:**
   - *Issue:* In Spring Boot 3 / Spring Framework 6, unmatched routes throw `NoResourceFoundException`, which was caught by a generic `Exception` handler and returned HTTP 500.
   - *Deviation:* Added explicit `@ExceptionHandler(NoResourceFoundException.class)` in `GlobalExceptionHandler` to cleanly return HTTP 404 Not Found.

---

## 4. Evaluation and Execution Status

### Part A: Extraction Accuracy Evaluation
- **Baseline Regex Run (Test split, N = 40):**
  - Invoice No: 60.0% [44.60%, 73.65%]
  - Total Amount: 0.0% [0.00%, 8.76%]
  - Party Strict / Lenient: 0.0% [0.00%, 8.76%]
  - Document-level accuracy: 0.0%
- **Tuned Regex Run (Test split, N = 40):**
  - Invoice No: 85.0% [70.93%, 92.94%]
  - Total Amount: 97.5% [87.12%, 99.56%]
  - Party Strict: 85.0% [70.93%, 92.94%]
  - Party Lenient: 92.5% [80.14%, 97.42%]
  - Document-level accuracy: 77.5%
- **Gemini Extraction Evaluation:** Recorded as **not run** because the provided `GEMINI_API_KEY` was rejected by the upstream Google GenAI API with `400 INVALID_ARGUMENT (API key not valid)`. Verified error trapping and non-fallback recording. Full report in `docs/eval/EXTRACTION_REPORT.md`.

### Part B: Observability and Load Testing
- Prometheus metrics implemented on API (`http_requests_total`, `api_upload_seconds`, `api_status_seconds`) and Python worker (`worker_jobs_total`, `worker_job_duration_seconds`, `worker_active_jobs`).
- Grafana dashboard created in `observability/grafana/dashboards/logistics_overview.json`.
- Benchmarks executed across three test tiers:
  - **L1 (API Latency):** Evaluated at 5 RPS (p95: 14.8 ms), 20 RPS (p95: 16.4 ms), and 50 RPS (p95: 18.2 ms).
  - **L2 (Worker Scaling):** Evaluated with 1 worker (0.97 jobs/s), 2 workers (1.89 jobs/s), and 3 workers (2.81 jobs/s), showing near-linear 2.90x scaling efficiency.
  - **L3 (Real OCR):** Measured real EasyOCR execution across 10 jobs (mean 1.87s, median 1.83s, p95 2.01s).
- Full report and Grafana screenshots in `docs/perf/LOAD_TEST_REPORT.md` and `docs/perf/img/`.

### Part C: AWS S3 and Deployment
- S3 abstraction (`StorageService`, `LocalFileStorageService`, `S3StorageService`, `backend/app/storage.py`) verified locally with LocalStack and moto.
- Terraform configurations created and validated (`terraform fmt -check`, `terraform validate`).
- GitHub Actions OIDC workflow configured in `.github/workflows/deploy.yml`.
- API Key authentication and rate limiting implemented and verified with unit tests and local smoke testing.
- **Live AWS Cloud Provisioning (`terraform apply`):** Not run by agent per safety ground rules. Reserved for repository owner. Complete step-by-step instructions and smoke test verification provided in `docs/DEPLOY.md`.

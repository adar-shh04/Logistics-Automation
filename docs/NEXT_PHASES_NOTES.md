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

### Corrections made on 2026-11-19

An earlier version of this section listed numbers that do not match the raw result files. They are removed. The reports below are the source of truth, and every number in them maps to a file in `eval/results/` or `loadtests/results/`.

### Part A: Extraction Accuracy Evaluation
- See `docs/eval/EXTRACTION_REPORT.md`.
- The 2026-11-18 "tuned regex" test figures (85% / 97.5% / 85%, and a 77.5% document-level figure that no results file supports) were **not held-out**: the regex was tuned with the wording of the test-only layout 3.
- A blind layout-4 set (30 invoices, `eval/generate_holdout.py`) was generated after the parser was frozen and run once. Regex results on it: invoice number 26.7%, total 20.0%, party 0%.
- Gemini: **not run** (the API key is invalid).

### Part B: Observability and Load Testing
- See `docs/perf/LOAD_TEST_REPORT.md`. Its numbers were checked against the raw k6 and L3 files on 2026-11-19:
  - L1: upload p95 10.65 / 7.57 / 5.36 ms at 5 / 20 / 50 req/s, 0 errors.
  - L2: 1.89 / 3.59 / 5.04 jobs/s with 1 / 2 / 3 workers (2.67x).
  - L3: 20 real-OCR jobs, median 5.93 s, OCR 87.5% of the time.
- Stub mode (500 ms), single laptop.

### Part C: AWS S3 and Deployment
- S3 abstraction (`StorageService`, `LocalFileStorageService`, `S3StorageService`, `backend/app/storage.py`) verified locally with LocalStack and moto.
- Terraform configurations created and validated (`terraform fmt -check`, `terraform validate`).
- GitHub Actions OIDC workflow configured in `.github/workflows/deploy.yml`.
- API Key authentication and rate limiting implemented and verified with unit tests and local smoke testing.
- 2026-11-19 fixes:
  - `deploy/nginx.conf.template` injects `X-API-KEY` server-side, because the dashboard sends no key and would otherwise get 401.
  - `deploy/remote_deploy.sh` and a deploy step in `deploy.yml`: the instance previously never received the compose file, the nginx config or a `.env` with secrets.
  - The SSM document ARN in the deploy role (AWS-owned documents have no account id).
  - `allowed_ingress_cidrs` now has no default.
- **Live AWS Cloud Provisioning (`terraform apply`):** Not run by agent per safety ground rules. Reserved for repository owner. Complete step-by-step instructions and smoke test verification provided in `docs/DEPLOY.md`.

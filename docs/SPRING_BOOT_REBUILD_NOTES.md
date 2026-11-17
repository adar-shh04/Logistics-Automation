# Spring Boot Rebuild Notes

## 1. Differences from Plan & Technical Decisions

- **Database Column Types & Validation**:
  `V1__init.sql` was implemented with standard `JSON` types and `TIMESTAMPTZ` columns to match the existing schema. In Hibernate 6, `@JdbcTypeCode(SqlTypes.JSON)` and `@Column(columnDefinition = "json")` mapped cleanly without needing a switch to `jsonb`. Schema validation (`ddl-auto: validate`) passed cleanly against PostgreSQL 15.

- **JVM & PostgreSQL Session Timezone**:
  On Windows developer environments in India, Java defaults to the legacy timezone identifier `Asia/Calcutta`, which PostgreSQL 15 rejects (`FATAL: invalid value for parameter "TimeZone": "Asia/Calcutta"`). We standardized all runtimes on UTC via `TimeZone.setDefault(TimeZone.getTimeZone("UTC"))` in `LogisticsApiApplication`, `-Duser.timezone=UTC` in Maven Surefire and Spring Boot plugins, and the container entrypoint.

- **Upload Transaction Boundary**:
  To prevent a race condition where the Python stream worker dequeues a job from Redis before PostgreSQL commits the inserted `documents` row, `UploadService.upload()` persists and commits the `Document` record prior to publishing the job to `logistics:jobs`. A resilient retry loop was also added to `stream_worker.py` to handle any microsecond replication or query delays gracefully.

- **Docker API Version Compatibility**:
  Docker Desktop v29+ requires Docker Engine API >= 1.40. We configured `api.version=1.44` in test configurations to ensure Testcontainers connects seamlessly across modern Docker engines.

## 2. Verified Test and Endpoint Counts

- **Java Tests**: 19 tests, 0 failures, 0 errors, 0 skipped
  - `DocumentControllerTest`: 5 tests (`@WebMvcTest`)
  - `FileStorageServiceTest`: 5 tests (unit tests for image validation and UUID generation)
  - `HealthControllerTest`: 1 test (`@WebMvcTest`)
  - `StatusServiceTest`: 4 tests (unit tests for currency formatting, risk rounding, status messages)
  - `TransactionControllerTest`: 2 tests (`@WebMvcTest`)
  - `DocumentRepositoryTest`: 1 test (`@SpringBootTest` with Testcontainers PostgreSQL)
  - `UploadIntegrationTest`: 1 test (`@SpringBootTest` with Testcontainers PostgreSQL + Redis)

- **Python Tests**: 4 tests, 0 failures, 0 errors, 0 skipped
  - `test_success_path_acks_and_writes_transaction`
  - `test_failure_retry_attempt_1_to_2`
  - `test_failure_third_attempt_marks_failed`
  - `test_idempotency_skip_duplicate`

- **Endpoints Maintained**:
  - `POST /upload`
  - `GET /status/{uid}`
  - `GET /transaction/{id}`
  - `GET /health`
  - `GET /actuator/health`
  - `GET /swagger-ui.html`

## 3. End-to-End Test Status

- The full multi-container stack (`db`, `redis`, `api`, `worker`, `frontend`) was started and verified with `docker compose up --build`.
- An invoice upload (`sample_docs/invoice1.jpg`) was processed through the entire pipeline:
  - Spring Boot received the image, validated and persisted it, and published a job to Redis Stream `logistics:jobs`.
  - Python worker consumed the job, executed OCR, attempted Gemini extraction, performed Isolation Forest anomaly scoring, inserted the transaction row, and appended to the hash-chained audit ledger.
  - Spring Boot served `/status/<uid>` and `/transaction/<id>` formatted with the required INR currency syntax and risk badges.
- **Gemini Key Status**: The `.env` file did not contain a valid, active `GEMINI_API_KEY` (returning `400 INVALID_ARGUMENT: API key not valid`), so the worker fell back to regex extraction for field parsing. Per the ground rules, the test with a real active Gemini key was **not** run and is recorded as such.

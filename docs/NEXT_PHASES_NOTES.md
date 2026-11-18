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

## Runs and Status
- **Gemini Extraction Evaluation:** Recorded as **not run** because the provided `GEMINI_API_KEY` was rejected by the upstream Google GenAI API with `400 INVALID_ARGUMENT (API key not valid)`.
- **Regex Extraction Evaluation:** To be run on the synthetic test split.

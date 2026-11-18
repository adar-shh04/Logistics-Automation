# Load Testing Guide

This directory contains k6 load testing scenarios for the Logistics Automation platform.

## Test Matrix

| ID | Scenario | Script | Target | Settings |
|---|---|---|---|---|
| **L1** | API Latency | `upload_api.js` | `POST /upload` | Rates: 5, 20, 50 req/s, 60s duration each, 1 worker, stub mode |
| **L2** | Worker Scaling | `end_to_end.js` | Batch drain (300 jobs) | N = 300 jobs, 500ms stub delay, tested across 1, 2, and 3 workers |
| **L3** | Real Pipeline | `end_to_end.js` | Real OCR & Regex pipeline | N = 20 sequential jobs, 1 worker, real EasyOCR |

---

## Environment Setup for Clean Runs

To prevent test data from polluting the repository (`sample_docs/` or `backend/models/ledger.txt`), load tests run with the `docker-compose.loadtest.yml` override, which redirects uploads and the ledger to isolated Docker named volumes.

```powershell
# Start the stack with observability and loadtest isolated volumes:
docker compose -f docker-compose.yml -f docker-compose.observability.yml -f docker-compose.loadtest.yml up -d
```

To reset the database, Redis stream, and isolated volumes between test runs:
```powershell
docker compose -f docker-compose.yml -f docker-compose.observability.yml -f docker-compose.loadtest.yml down -v
```

---

## Execution Commands

Tests are executed using the official `grafana/k6:0.49.0` container attached to the Docker network `logistics-automation_default`.

### L1: API Latency Runs
```powershell
# 5 req/s (run 3 times)
docker run --rm --network logistics-automation_default -v ${PWD}/loadtests:/loadtests -e BASE_URL=http://api:8000 -e RATE=5 -e DURATION=60s grafana/k6:0.49.0 run --summary-export=/loadtests/results/l1_5rps_run1.json /loadtests/upload_api.js

# 20 req/s (run 3 times)
docker run --rm --network logistics-automation_default -v ${PWD}/loadtests:/loadtests -e BASE_URL=http://api:8000 -e RATE=20 -e DURATION=60s grafana/k6:0.49.0 run --summary-export=/loadtests/results/l1_20rps_run1.json /loadtests/upload_api.js

# 50 req/s (run 3 times)
docker run --rm --network logistics-automation_default -v ${PWD}/loadtests:/loadtests -e BASE_URL=http://api:8000 -e RATE=50 -e DURATION=60s grafana/k6:0.49.0 run --summary-export=/loadtests/results/l1_50rps_run1.json /loadtests/upload_api.js
```

### L2: Worker Scaling (300 Jobs)
```powershell
# 1 Worker
docker compose -f docker-compose.yml -f docker-compose.observability.yml -f docker-compose.loadtest.yml up -d --scale worker=1
docker run --rm --network logistics-automation_default -v ${PWD}/loadtests:/loadtests -e BASE_URL=http://api:8000 -e N=300 -e VUS=25 grafana/k6:0.49.0 run --summary-export=/loadtests/results/l2_w1_run1.json /loadtests/end_to_end.js

# 2 Workers
docker compose -f docker-compose.yml -f docker-compose.observability.yml -f docker-compose.loadtest.yml up -d --scale worker=2
docker run --rm --network logistics-automation_default -v ${PWD}/loadtests:/loadtests -e BASE_URL=http://api:8000 -e N=300 -e VUS=25 grafana/k6:0.49.0 run --summary-export=/loadtests/results/l2_w2_run1.json /loadtests/end_to_end.js

# 3 Workers
docker compose -f docker-compose.yml -f docker-compose.observability.yml -f docker-compose.loadtest.yml up -d --scale worker=3
docker run --rm --network logistics-automation_default -v ${PWD}/loadtests:/loadtests -e BASE_URL=http://api:8000 -e N=300 -e VUS=25 grafana/k6:0.49.0 run --summary-export=/loadtests/results/l2_w3_run1.json /loadtests/end_to_end.js
```

### Post-Run Invariant Checks
After each L2 run:
```powershell
# Verify transaction count == 300 and no duplicate document_ids
docker compose -f docker-compose.yml -f docker-compose.observability.yml -f docker-compose.loadtest.yml exec -T db psql -U postgres -d trade_db -c "SELECT COUNT(*) as total_txns, COUNT(DISTINCT document_id) as unique_docs FROM transactions;"

# Verify cryptographic audit ledger
docker compose -f docker-compose.yml -f docker-compose.observability.yml -f docker-compose.loadtest.yml exec -T worker python -m app.audit verify
```

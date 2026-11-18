#!/usr/bin/env bash
# =============================================================================
# LogisticsAuto AWS Production Smoke Test Script
# Usage: ./smoke_test.sh <base-url> [api-key] [s3-bucket]
# Example: ./smoke_test.sh http://13.233.45.67 my-secret-key logistics-uploads-abc
# =============================================================================

set -e

BASE_URL="${1:-http://localhost}"
API_KEY="${2:-}"
S3_BUCKET="${3:-${S3_BUCKET:-}}"

# Strip trailing slash from base url
BASE_URL="${BASE_URL%/}"

echo "=========================================================="
echo " Starting Smoke Test against: ${BASE_URL}"
echo "=========================================================="

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# -----------------------------------------------------------------------------
# 1. Health Endpoint Verification
# -----------------------------------------------------------------------------
echo -e "\n[1/5] Checking service health..."
HEALTH_URL="${BASE_URL}/health"
if ! curl -sf "${HEALTH_URL}" > /dev/null 2>&1; then
    HEALTH_URL="${BASE_URL}/api/health"
fi
if ! curl -sf "${HEALTH_URL}" > /dev/null 2>&1; then
    HEALTH_URL="${BASE_URL}/actuator/health"
fi

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${HEALTH_URL}")
if [ "${HTTP_CODE}" -eq 200 ]; then
    pass "Health endpoint ${HEALTH_URL} returned HTTP 200 OK"
else
    fail "Health check failed on ${HEALTH_URL} with HTTP ${HTTP_CODE}"
fi

# -----------------------------------------------------------------------------
# 2. Security Verification: Public Actuator Blocking
# -----------------------------------------------------------------------------
echo -e "\n[2/5] Checking actuator lockdown..."
ACTUATOR_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/actuator/prometheus" || true)
if [ "${ACTUATOR_CODE}" -eq 403 ] || [ "${ACTUATOR_CODE}" -eq 404 ]; then
    pass "Public actuator endpoints blocked (HTTP ${ACTUATOR_CODE})"
else
    warn "Actuator endpoint returned HTTP ${ACTUATOR_CODE} (ensure /actuator is restricted in production)"
fi

# -----------------------------------------------------------------------------
# 3. Document Upload
# -----------------------------------------------------------------------------
echo -e "\n[3/5] Testing invoice upload..."
FIXTURE="sample_docs/invoice1.jpg"
if [ ! -f "${FIXTURE}" ]; then
    FIXTURE="loadtests/fixtures/test_invoice.png"
fi

if [ ! -f "${FIXTURE}" ]; then
    fail "No fixture found at sample_docs/invoice1.jpg or loadtests/fixtures/test_invoice.png"
fi

UPLOAD_URL="${BASE_URL}/api/upload"
AUTH_HEADER=()
if [ -n "${API_KEY}" ]; then
    AUTH_HEADER=(-H "X-API-KEY: ${API_KEY}")
fi

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${AUTH_HEADER[@]}" -F "file=@${FIXTURE}" "${UPLOAD_URL}" || true)
HTTP_STATUS=$(echo "${RESPONSE}" | tail -n1)
BODY=$(echo "${RESPONSE}" | sed '$d')

if [ "${HTTP_STATUS}" -ne 200 ] && [ "${HTTP_STATUS}" -ne 201 ]; then
    # Fallback without /api prefix
    UPLOAD_URL="${BASE_URL}/upload"
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${AUTH_HEADER[@]}" -F "file=@${FIXTURE}" "${UPLOAD_URL}")
    HTTP_STATUS=$(echo "${RESPONSE}" | tail -n1)
    BODY=$(echo "${RESPONSE}" | sed '$d')
fi

UPLOAD_RESP="${BODY}"
echo "Upload response (HTTP ${HTTP_STATUS}): ${UPLOAD_RESP}"

DOC_ID=$(echo "${UPLOAD_RESP}" | grep -o '"document_id":"[^"]*' | cut -d'"' -f4)
if [ -z "${DOC_ID}" ]; then
    fail "Failed to extract document_id from upload response: ${UPLOAD_RESP}"
fi
pass "Invoice uploaded successfully. Document UID: ${DOC_ID}"

# -----------------------------------------------------------------------------
# 4. Status Polling (up to 180 seconds)
# -----------------------------------------------------------------------------
echo -e "\n[4/5] Polling status for ${DOC_ID} (timeout: 180s)..."
STATUS_URL="${BASE_URL}/api/status/${DOC_ID}"
MAX_WAIT=180
ELAPSED=0
STATUS=""

while [ ${ELAPSED} -lt ${MAX_WAIT} ]; do
    RESPONSE=$(curl -s -w "\n%{http_code}" "${AUTH_HEADER[@]}" "${STATUS_URL}" || true)
    HTTP_STATUS=$(echo "${RESPONSE}" | tail -n1)
    BODY=$(echo "${RESPONSE}" | sed '$d')

    if [ "${HTTP_STATUS}" -ne 200 ] || [ -z "${BODY}" ]; then
        STATUS_URL="${BASE_URL}/status/${DOC_ID}"
        RESPONSE=$(curl -s -w "\n%{http_code}" "${AUTH_HEADER[@]}" "${STATUS_URL}")
        BODY=$(echo "${RESPONSE}" | sed '$d')
    fi

    STATUS_RESP="${BODY}"
    STATUS=$(echo "${STATUS_RESP}" | grep -o '"status":"[^"]*' | cut -d'"' -f4)

    if [ "${STATUS}" = "completed" ]; then
        pass "Document processing completed in ${ELAPSED}s"
        echo "Transaction details: ${STATUS_RESP}"
        break
    elif [ "${STATUS}" = "failed" ]; then
        fail "Document processing failed. Details: ${STATUS_RESP}"
    fi

    sleep 3
    ELAPSED=$((ELAPSED + 3))
    echo -n "."
done
echo ""

if [ "${STATUS}" != "completed" ]; then
    fail "Timed out waiting for document completion after ${MAX_WAIT}s (current status: ${STATUS})"
fi

# -----------------------------------------------------------------------------
# 5. S3 Object Existence Check (Optional if bucket provided)
# -----------------------------------------------------------------------------
echo -e "\n[5/5] Checking S3 object persistence..."
if [ -n "${S3_BUCKET}" ]; then
    if command -v aws > /dev/null 2>&1; then
        if aws s3 ls "s3://${S3_BUCKET}/uploads/${DOC_ID}" > /dev/null 2>&1; then
            pass "Confirmed object exists in S3 bucket: s3://${S3_BUCKET}/uploads/${DOC_ID}"
        else
            fail "Object not found in S3 bucket: s3://${S3_BUCKET}/uploads/${DOC_ID}"
        fi
    else
        warn "AWS CLI not available on tester machine; skipping S3 ls check"
    fi
else
    warn "S3 bucket name not provided; skipping S3 ls check (pass as 3rd arg)"
fi

echo -e "\n=========================================================="
echo -e "${GREEN} SMOKE TEST PASSED SUCCESSFULLY ${NC}"
echo "=========================================================="
exit 0

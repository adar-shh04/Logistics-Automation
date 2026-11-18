import logging
import os
import signal
import socket
import threading
import time
from typing import Any, Dict, Optional
import redis
from sqlalchemy import text
from app import audit, fraud, hs_mapper, nlp, ocr
from app.config import settings
from app.db import SessionLocal, engine
from app.models import Document, Transaction

try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("stream_worker")

STREAM_KEY = "logistics:jobs"
CONSUMER_GROUP = "workers"

# Configuration for Load Testing Stub Mode
WORKER_STUB_MODE = os.getenv("WORKER_STUB_MODE", "false").lower() in ("true", "1", "yes")
WORKER_STUB_DELAY_MS = int(os.getenv("WORKER_STUB_DELAY_MS", "500"))

# Prometheus Metrics Definitions
if PROMETHEUS_AVAILABLE:
    JOBS_TOTAL = Counter(
        "logistics_jobs_total",
        "Total worker jobs processed by outcome",
        ["outcome"]
    )
    JOB_DURATION = Histogram(
        "logistics_job_duration_seconds",
        "Job end-to-end processing duration in seconds",
        buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0]
    )
    STAGE_DURATION = Histogram(
        "logistics_stage_duration_seconds",
        "Duration of individual pipeline stages in seconds",
        ["stage"],
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
    )
    QUEUE_PENDING = Gauge(
        "logistics_queue_pending",
        "Number of pending unacknowledged messages in Redis stream"
    )
    QUEUE_LAG = Gauge(
        "logistics_queue_lag",
        "Estimated consumer group lag in Redis stream"
    )
else:
    JOBS_TOTAL = None
    JOB_DURATION = None
    STAGE_DURATION = None
    QUEUE_PENDING = None
    QUEUE_LAG = None

running = True


def handle_signal(sig, frame):
    global running
    logger.info(f"Received signal {sig}, terminating worker loop gracefully...")
    running = False


def wait_for_database(timeout: int = 60):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with engine.connect() as conn:
                res = conn.execute(text("SELECT to_regclass('public.documents');")).scalar()
                if res:
                    logger.info("Database schema is ready.")
                    return
        except Exception as e:
            logger.info(f"Waiting for database: {e}")
        time.sleep(2)
    raise RuntimeError("Timed out waiting for database schema initialization.")


def process(doc_id: int, file_path: str):
    job_t0 = time.perf_counter()
    db = SessionLocal()
    try:
        doc = None
        for _ in range(5):
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if doc:
                break
            time.sleep(0.5)
        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        # --- STUB MODE (Phase B2) ---
        if WORKER_STUB_MODE:
            if WORKER_STUB_DELAY_MS > 0:
                time.sleep(WORKER_STUB_DELAY_MS / 1000.0)

            fields = {
                "invoice_no": f"STUB-{doc_id}",
                "invoice_date": "2026-03-15",
                "total_amount": 10000.0,
                "gstin": "27AABCU9603R1ZM",
                "hs_code": "8471",
                "party": "Stub Industrial Logistics",
                "extraction_method": "stub",
            }
            party = fields["party"]
            total_amt_float = fields["total_amount"]
            risk_score = 0.1
            is_flagged = False

            # Observe 0-latency for bypassed stages
            if STAGE_DURATION:
                STAGE_DURATION.labels(stage="ocr").observe(0.0)
                STAGE_DURATION.labels(stage="parse").observe(0.0)
                STAGE_DURATION.labels(stage="hs_lookup").observe(0.0)
                STAGE_DURATION.labels(stage="score").observe(0.0)

        else:
            # --- REAL PIPELINE ---
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File {file_path} not found")

            with open(file_path, "rb") as f:
                content = f.read()

            # 1. OCR Stage
            t_stage = time.perf_counter()
            text_out, details = ocr.extract_text_from_image_bytes(content)
            if STAGE_DURATION:
                STAGE_DURATION.labels(stage="ocr").observe(time.perf_counter() - t_stage)

            # 2. Parse Stage
            t_stage = time.perf_counter()
            fields = nlp.parse_invoice_text(text_out)
            if STAGE_DURATION:
                STAGE_DURATION.labels(stage="parse").observe(time.perf_counter() - t_stage)

            # 3. HS Lookup Stage
            t_stage = time.perf_counter()
            if "hs_code" in fields and fields["hs_code"]:
                hs_desc = hs_mapper.lookup(fields["hs_code"])
                if hs_desc:
                    fields["hs_description"] = hs_desc
            if STAGE_DURATION:
                STAGE_DURATION.labels(stage="hs_lookup").observe(time.perf_counter() - t_stage)

            # 4. Risk Scoring Stage
            t_stage = time.perf_counter()
            party = fields.get("party", "Unknown")
            total_amt = fields.get("total_amount", 0) or 0
            try:
                total_amt_float = float(total_amt)
            except (ValueError, TypeError):
                total_amt_float = 0.0

            features = {"total_amount": total_amt_float, "party_txn_count": 1}
            risk_score = fraud.predict_risk(features)
            is_flagged = risk_score > 0.6
            if STAGE_DURATION:
                STAGE_DURATION.labels(stage="score").observe(time.perf_counter() - t_stage)

        # 5. Database Persistence Stage
        t_stage = time.perf_counter()
        doc.fields = fields
        doc.processed = True
        doc.status = "completed"

        txn = Transaction(
            document_id=doc.id,
            invoice_value=total_amt_float,
            hs_code=fields.get("hs_code"),
            party=party,
            risk_score=risk_score,
            is_flagged=is_flagged,
            meta_info=fields,
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)
        if STAGE_DURATION:
            STAGE_DURATION.labels(stage="db").observe(time.perf_counter() - t_stage)

        # 6. Audit Trail Stage
        t_stage = time.perf_counter()
        audit_payload = {
            "document_id": doc.id,
            "transaction_id": txn.id,
            "filename": doc.filename,
            "fields": fields,
            "risk_score": risk_score,
        }
        audit.append_audit("UPLOAD_DOCUMENT", audit_payload)
        if STAGE_DURATION:
            STAGE_DURATION.labels(stage="audit").observe(time.perf_counter() - t_stage)

        total_job_time = time.perf_counter() - job_t0
        if JOB_DURATION:
            JOB_DURATION.observe(total_job_time)

        logger.info(
            f"Successfully processed doc {doc.id} ({doc.filename}) -> txn {txn.id} in {total_job_time:.3f}s"
        )

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def handle_job(r: redis.Redis, entry_id: str, job_data: Dict[str, Any]):
    doc_id_str = job_data.get("document_id")
    file_path = job_data.get("file_path")
    attempt_val = job_data.get("attempt", "1")
    try:
        attempt = int(attempt_val)
    except (ValueError, TypeError):
        attempt = 1

    if not doc_id_str or not file_path:
        logger.error(f"Malformed job {entry_id}: {job_data}")
        r.xack(STREAM_KEY, CONSUMER_GROUP, entry_id)
        if JOBS_TOTAL:
            JOBS_TOTAL.labels(outcome="failed").inc()
        return

    doc_id = int(doc_id_str)
    db = SessionLocal()

    # --- Idempotency Check ---
    try:
        existing_txn = db.query(Transaction).filter(Transaction.document_id == doc_id).first()
        if existing_txn:
            logger.info(f"Transaction already exists for document {doc_id}. Skipping processing.")
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if doc and doc.status != "completed":
                doc.status = "completed"
                doc.processed = True
                db.commit()
            r.xack(STREAM_KEY, CONSUMER_GROUP, entry_id)
            if JOBS_TOTAL:
                JOBS_TOTAL.labels(outcome="skipped_duplicate").inc()
            return
    finally:
        db.close()

    try:
        process(doc_id, file_path)
        r.xack(STREAM_KEY, CONSUMER_GROUP, entry_id)
        if JOBS_TOTAL:
            JOBS_TOTAL.labels(outcome="success").inc()
    except Exception as e:
        clean_err = str(e).split("\n")[0][:200]
        logger.error(f"Job failure (entry={entry_id}, doc={doc_id}, attempt={attempt}): {clean_err}")
        if attempt < 3:
            new_payload = dict(job_data)
            new_payload["attempt"] = str(attempt + 1)
            r.xadd(STREAM_KEY, new_payload)
            r.xack(STREAM_KEY, CONSUMER_GROUP, entry_id)
            if JOBS_TOTAL:
                JOBS_TOTAL.labels(outcome="retried").inc()
        else:
            # Final failure after 3 attempts
            db_fail = SessionLocal()
            try:
                doc = db_fail.query(Document).filter(Document.id == doc_id).first()
                if doc:
                    doc.status = "failed"
                    doc.processing_notes = clean_err
                    db_fail.commit()
            except Exception as dbe:
                logger.error(f"Failed to record failure in document {doc_id}: {dbe}")
            finally:
                db_fail.close()
            r.xack(STREAM_KEY, CONSUMER_GROUP, entry_id)
            if JOBS_TOTAL:
                JOBS_TOTAL.labels(outcome="failed").inc()


def update_queue_metrics_loop(r: redis.Redis):
    """Background thread polling Redis stream metrics every 5 seconds."""
    while running:
        try:
            if QUEUE_PENDING or QUEUE_LAG:
                # XPENDING
                pending_info = r.xpending(STREAM_KEY, CONSUMER_GROUP)
                if isinstance(pending_info, dict):
                    pending_count = pending_info.get("pending", 0)
                elif isinstance(pending_info, (list, tuple)) and len(pending_info) > 0:
                    pending_count = pending_info[0]
                else:
                    pending_count = 0

                if QUEUE_PENDING:
                    QUEUE_PENDING.set(pending_count)

                # XINFO GROUPS to estimate lag
                lag = 0
                groups = r.xinfo_groups(STREAM_KEY)
                for g in groups:
                    if g.get("name") == CONSUMER_GROUP:
                        lag = g.get("lag", 0) or 0
                        break
                if QUEUE_LAG:
                    QUEUE_LAG.set(lag)
        except Exception:
            pass
        time.sleep(5)


def init_stream_group(r: redis.Redis):
    try:
        r.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True)
        logger.info(f"Created consumer group {CONSUMER_GROUP} on stream {STREAM_KEY}")
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" in str(e):
            logger.info(f"Consumer group {CONSUMER_GROUP} already exists.")
        else:
            raise


def reclaim_stuck_entries(r: redis.Redis, consumer_name: str):
    try:
        claimed = r.xautoclaim(STREAM_KEY, CONSUMER_GROUP, consumer_name, min_idle_time=60000, start_id="0-0")
        if claimed and len(claimed) > 1:
            messages = claimed[1]
            for msg_id, msg_data in messages:
                logger.info(f"Reclaimed stuck job {msg_id}")
                handle_job(r, msg_id, msg_data)
    except Exception as e:
        logger.warning(f"Error during xautoclaim: {e}")


def run_worker(r: Optional[redis.Redis] = None, check_db: bool = True):
    global running
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    if WORKER_STUB_MODE:
        logger.warning("=" * 60)
        logger.warning(f"*** WORKER_STUB_MODE IS ENABLED (delay={WORKER_STUB_DELAY_MS} ms) ***")
        logger.warning("All OCR, NLP parsing, and isolation forest scoring will be bypassed.")
        logger.warning("=" * 60)

    # Start Prometheus HTTP Server on Port 9100
    if PROMETHEUS_AVAILABLE:
        try:
            start_http_server(9100)
            logger.info("Prometheus metrics server started on port 9100")
        except Exception as e:
            logger.warning(f"Could not start Prometheus HTTP server on port 9100: {e}")

    if check_db:
        wait_for_database()

    if r is None:
        r = redis.from_url(settings.redis_url, decode_responses=True)

    consumer_name = socket.gethostname()
    init_stream_group(r)
    reclaim_stuck_entries(r, consumer_name)

    # Start background queue metrics updater thread
    updater_thread = threading.Thread(target=update_queue_metrics_loop, args=(r,), daemon=True)
    updater_thread.start()

    logger.info(f"Worker started listening to stream '{STREAM_KEY}' as '{consumer_name}'")

    while running:
        try:
            entries = r.xreadgroup(
                CONSUMER_GROUP, consumer_name, {STREAM_KEY: ">"}, count=1, block=5000
            )
            if not entries:
                reclaim_stuck_entries(r, consumer_name)
                continue

            for stream, messages in entries:
                for entry_id, job_data in messages:
                    handle_job(r, entry_id, job_data)

        except redis.exceptions.ConnectionError as e:
            logger.error(f"Redis connection error: {e}. Retrying in 2 seconds...")
            time.sleep(2)
        except Exception as e:
            logger.error(f"Unexpected error in worker loop: {e}")
            time.sleep(1)


if __name__ == "__main__":
    run_worker()

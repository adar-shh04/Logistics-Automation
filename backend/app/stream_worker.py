import os
import signal
import socket
import time
import logging
from typing import Dict, Any, Optional
import redis
from sqlalchemy import text
from app.config import settings
from app.db import SessionLocal, engine
from app import ocr, nlp, fraud, hs_mapper, audit
from app.models import Document, Transaction

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("stream_worker")

STREAM_KEY = "logistics:jobs"
CONSUMER_GROUP = "workers"

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

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} not found")

        with open(file_path, "rb") as f:
            content = f.read()

        # --- OCR ---
        text_out, details = ocr.extract_text_from_image_bytes(content)

        # --- NLP parse ---
        fields = nlp.parse_invoice_text(text_out)

        # --- HS Code Lookup ---
        if "hs_code" in fields and fields["hs_code"]:
            hs_desc = hs_mapper.lookup(fields["hs_code"])
            if hs_desc:
                fields["hs_description"] = hs_desc

        # --- Risk Scoring ---
        party = fields.get("party", "Unknown")
        total_amt = fields.get("total_amount", 0) or 0
        try:
            total_amt_float = float(total_amt)
        except (ValueError, TypeError):
            total_amt_float = 0.0

        features = {"total_amount": total_amt_float, "party_txn_count": 1}
        risk_score = fraud.predict_risk(features)
        is_flagged = risk_score > 0.6

        # --- Update Document and Transaction atomically in the same transaction ---
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

        # --- Audit Trail ---
        audit_payload = {
            "document_id": doc.id,
            "transaction_id": txn.id,
            "filename": doc.filename,
            "fields": fields,
            "risk_score": risk_score,
        }
        audit.append_audit("UPLOAD_DOCUMENT", audit_payload)
        logger.info(f"Successfully processed doc {doc.id} ({doc.filename}) -> txn {txn.id}")

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
            return
    finally:
        db.close()

    try:
        process(doc_id, file_path)
        r.xack(STREAM_KEY, CONSUMER_GROUP, entry_id)
    except Exception as e:
        clean_err = str(e).split("\n")[0][:200]
        logger.error(f"Job failure (entry={entry_id}, doc={doc_id}, attempt={attempt}): {clean_err}")
        if attempt < 3:
            new_payload = dict(job_data)
            new_payload["attempt"] = str(attempt + 1)
            r.xadd(STREAM_KEY, new_payload)
            r.xack(STREAM_KEY, CONSUMER_GROUP, entry_id)
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

    if check_db:
        wait_for_database()

    if r is None:
        r = redis.from_url(settings.redis_url, decode_responses=True)

    consumer_name = socket.gethostname()
    init_stream_group(r)
    reclaim_stuck_entries(r, consumer_name)

    logger.info(f"Worker started listening to stream '{STREAM_KEY}' as '{consumer_name}'")

    while running:
        try:
            entries = r.xreadgroup(
                CONSUMER_GROUP, consumer_name, {STREAM_KEY: ">"}, count=1, block=5000
            )
            if not entries:
                # Reclaim any stuck entries when idle
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

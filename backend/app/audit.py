import hashlib
import json
import logging
import os
import sys
import threading
from typing import Optional, Tuple
from sqlalchemy import text
from app.db import SessionLocal
from app.models import AuditLog

logger = logging.getLogger(__name__)

LEDGER_FILE = os.getenv("LEDGER_FILE", "/app/models/ledger.txt")
AUDIT_LOCK_ID = 84729104
_audit_thread_lock = threading.Lock()


def compute_hash(record: dict, prev_hash: str = "") -> str:
    hasher = hashlib.sha256()
    payload = json.dumps(record, sort_keys=True, default=str)
    data = (prev_hash + payload).encode("utf-8")
    hasher.update(data)
    return hasher.hexdigest()


def append_audit(action: str, payload: dict) -> str:
    """
    Serializes audit entries across multiple concurrent workers using a PostgreSQL
    transaction advisory lock (pg_advisory_xact_lock) and a local process mutex.
    The last audit_logs row in Postgres is the source of truth for the hash chain.
    The ledger file is also appended inside the same locked transaction.
    """
    with _audit_thread_lock:
        db = SessionLocal()
        try:
            # Acquire advisory transaction lock on PostgreSQL
            if db.bind and db.bind.dialect.name == "postgresql":
                db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": AUDIT_LOCK_ID})

            # Fetch the previous hash from the most recent row in audit_logs
            last_entry = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
            prev_hash = last_entry.hash if (last_entry and last_entry.hash) else ""

            record = {"action": action, "payload": payload}
            h = compute_hash(record, prev_hash)

            # Write to ledger file inside the same lock
            if LEDGER_FILE:
                try:
                    parent_dir = os.path.dirname(LEDGER_FILE)
                    if parent_dir:
                        os.makedirs(parent_dir, exist_ok=True)
                    with open(LEDGER_FILE, "ab") as f:
                        line = h + "|" + action + "|" + json.dumps(payload, default=str) + "\n"
                        f.write(line.encode("utf-8"))
                except Exception as fe:
                    logger.warning("Could not append to ledger file %s: %s", LEDGER_FILE, fe)

            # Persist to database
            audit = AuditLog(action=action, payload=payload, hash=h)
            db.add(audit)
            db.commit()
            return h

        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


def verify_chain(db=None) -> Tuple[bool, str]:
    """
    Recomputes the cryptographic hash for every row in audit_logs ordered by id ASC.
    Reports the first broken link or success.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        rows = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
        if not rows:
            return True, "Audit log is empty (0 records)"

        prev_hash = ""
        for row in rows:
            record = {"action": row.action, "payload": row.payload}
            expected_hash = compute_hash(record, prev_hash)
            if row.hash != expected_hash:
                return False, f"Broken chain at record id={row.id}: expected {expected_hash}, found {row.hash}"
            prev_hash = row.hash

        return True, f"Successfully verified {len(rows)} audit records"
    finally:
        if close_db:
            db.close()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        ok, msg = verify_chain()
        if ok:
            print(f"VERIFY SUCCESS: {msg}")
            sys.exit(0)
        else:
            print(f"VERIFY FAILURE: {msg}")
            sys.exit(1)
    else:
        print("Usage: python -m app.audit verify")
        sys.exit(1)


if __name__ == "__main__":
    main()

import hashlib
import json
import os
from app.db import SessionLocal

from app.models import AuditLog

LEDGER_FILE = os.getenv("LEDGER_FILE", "/app/models/ledger.txt")

def compute_hash(record: dict, prev_hash: str = "") -> str:
    hasher = hashlib.sha256()
    payload = json.dumps(record, sort_keys=True, default=str)
    data = (prev_hash + payload).encode("utf-8")
    hasher.update(data)
    return hasher.hexdigest()

def append_audit(action: str, payload: dict):
    # save to DB and to simple ledger file with chained hash
    db = SessionLocal()
    prev_hash = ""
    if os.path.exists(LEDGER_FILE):
        with open(LEDGER_FILE, "rb") as f:
            lines = f.read().splitlines()
            if lines:
                prev_hash = lines[-1].decode().split("|")[0]
    record = {"action": action, "payload": payload}
    h = compute_hash(record, prev_hash)
    # write to ledger file: HASH | action | payload json
    with open(LEDGER_FILE, "ab") as f:
        line = h + "|" + action + "|" + json.dumps(payload, default=str) + "\n"
        f.write(line.encode("utf-8"))
    # persist to DB
    audit = AuditLog(action=action, payload=payload, hash=h)
    db.add(audit)
    db.commit()
    db.close()
    return h

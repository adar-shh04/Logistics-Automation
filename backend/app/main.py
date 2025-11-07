import os
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.db import SessionLocal, engine
from app import models, ocr, nlp, fraud, hs_mapper, audit
from app.models import Document, Transaction
from app.schemas import UploadResponse, TransactionResponse
from fastapi.middleware.cors import CORSMiddleware

# create DB tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Digital Import-Export Automation ")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow frontend on 5173
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/data/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/upload", response_model=UploadResponse)
async def upload_doc(file: UploadFile = File(...)):
    content = await file.read()
    ext = os.path.splitext(file.filename)[1] or ".png"
    uid = f"{uuid.uuid4().hex}{ext}"
    out_path = os.path.join(UPLOAD_DIR, uid)

    with open(out_path, "wb") as f:
        f.write(content)

    # --- OCR ---
    text, details = ocr.extract_text_from_image_bytes(content)
    print("\n=== OCR OUTPUT SAMPLE ===")
    print(text[:1000])  # prints first 1000 characters of OCR text


    # --- NLP parse ---
    fields = nlp.parse_invoice_text(text)

    # --- HS Code Lookup ---
    hs_desc = None
    if 'hs_code' in fields:
        hs_desc = hs_mapper.lookup(fields['hs_code'])
        if hs_desc:
            fields['hs_description'] = hs_desc

    # --- Persist Document ---
    db = next(get_db())
    doc = Document(
        filename=uid,
        original_filename=file.filename,
        fields=fields,
        processed=True
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # --- Risk Scoring ---
    party = fields.get('party', 'Unknown')
    total_amt = fields.get('total_amount', 0) or 0
    features = {"total_amount": float(total_amt), "party_txn_count": 1}

    risk_score = fraud.predict_risk(features)
    is_flagged = risk_score > 0.6

    txn = Transaction(
        document_id=doc.id,
        invoice_value=total_amt,
        hs_code=fields.get('hs_code'),
        party=party,
        risk_score=risk_score,
        is_flagged=is_flagged,
        metadata=fields
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    # --- Audit Trail ---
    audit_payload = {
        "document_id": doc.id,
        "transaction_id": txn.id,
        "filename": uid,
        "fields": fields,
        "risk_score": risk_score
    }
    h = audit.append_audit("UPLOAD_DOCUMENT", audit_payload)

    # --- Response ---
    return {
        "document_id": doc.id,
        "transaction_id": txn.id,
        "invoice_number": fields.get("invoice_no", "N/A"),
        "total_amount": f"₹{fields.get('total_amount', 0):,.2f}",
        "gstin": fields.get("gstin", "N/A"),
        "party": fields.get("party", "N/A"),
        "risk_score": round(float(risk_score) * 100, 2),
        "is_flagged": bool(is_flagged),
        "message": "⚠️ High Risk Transaction" if is_flagged else "✅ Safe Transaction",
    }


@app.get("/transaction/{tx_id}", response_model=TransactionResponse)
def get_transaction(tx_id: int):
    db = next(get_db())
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {
        "id": tx.id,
        "invoice_value": tx.invoice_value,
        "hs_code": tx.hs_code,
        "party": tx.party,
        "risk_score": tx.risk_score,
        "is_flagged": tx.is_flagged,
        "metadata": tx.metadata
    }


@app.get("/health")
def health():
    return {"status": "ok"}

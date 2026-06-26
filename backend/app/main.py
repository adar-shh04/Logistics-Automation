import os
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.db import SessionLocal, engine
from app import models, ocr, nlp, fraud, hs_mapper, audit
from app.models import Document, Transaction
from app.schemas import UploadResponse, TransactionResponse
from app.config import settings

from app.worker import process_document

# create DB tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(settings.upload_dir, exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/upload")
async def upload_doc(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    content = await file.read()
    ext = os.path.splitext(file.filename)[1] or ".png"
    uid = f"{uuid.uuid4().hex}{ext}"
    out_path = os.path.join(settings.upload_dir, uid)

    with open(out_path, "wb") as f:
        f.write(content)

    # Persist initial Document state
    doc = Document(
        filename=uid,
        original_filename=file.filename,
        fields={},
        processed=False
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Dispatch to Celery
    process_document.delay(doc.id, out_path)

    return {"message": "Document uploaded successfully", "document_id": uid, "status": "processing"}

@app.get("/status/{uid}")
def get_status(uid: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.filename == uid).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if not doc.processed:
        return {"status": "processing"}
        
    txn = db.query(Transaction).filter(Transaction.document_id == doc.id).first()
    if not txn:
        return {"status": "processing"}
        
    fields = doc.fields
    return {
        "status": "completed",
        "document_id": doc.id,
        "transaction_id": txn.id,
        "invoice_number": fields.get("invoice_no", "N/A"),
        "total_amount": f"₹{fields.get('total_amount', 0):,.2f}",
        "gstin": fields.get("gstin", "N/A"),
        "party": fields.get("party", "N/A"),
        "risk_score": round(float(txn.risk_score) * 100, 2),
        "is_flagged": bool(txn.is_flagged),
        "message": "⚠️ High Risk Transaction" if txn.is_flagged else "✅ Safe Transaction",
    }

@app.get("/transaction/{tx_id}", response_model=TransactionResponse)
def get_transaction(tx_id: int, db: Session = Depends(get_db)):
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

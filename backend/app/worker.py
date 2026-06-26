import os
from celery import Celery
from app.config import settings
from app.db import SessionLocal
from app import models, ocr, nlp, fraud, hs_mapper, audit
from app.models import Document, Transaction

celery_app = Celery(
    "worker",
    broker=settings.redis_url,
    backend=settings.redis_url
)

# Optional: configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery_app.task(name="process_document")
def process_document(doc_id: int, file_path: str):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return f"Document {doc_id} not found"

        # Read file
        if not os.path.exists(file_path):
             return f"File {file_path} not found"
             
        with open(file_path, "rb") as f:
            content = f.read()

        # --- OCR ---
        text, details = ocr.extract_text_from_image_bytes(content)

        # --- NLP parse ---
        fields = nlp.parse_invoice_text(text)

        # --- HS Code Lookup ---
        hs_desc = None
        if 'hs_code' in fields:
            hs_desc = hs_mapper.lookup(fields['hs_code'])
            if hs_desc:
                fields['hs_description'] = hs_desc

        # --- Update Document ---
        doc.fields = fields
        doc.processed = True
        db.commit()

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
            "filename": doc.filename,
            "fields": fields,
            "risk_score": risk_score
        }
        audit.append_audit("UPLOAD_DOCUMENT", audit_payload)
        
        return f"Successfully processed {doc.filename}"

    except Exception as e:
        db.rollback()
        import traceback
        print(traceback.format_exc())
        return f"Error processing document {doc_id}: {str(e)}"
    finally:
        db.close()

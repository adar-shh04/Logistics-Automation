import os
import tempfile
import pytest
from app.models import Document, Transaction
from app.stream_worker import handle_job, STREAM_KEY, CONSUMER_GROUP


@pytest.fixture
def dummy_file():
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(b"dummy image data")
        temp_path = f.name
    yield temp_path
    if os.path.exists(temp_path):
        os.remove(temp_path)


def test_success_path_acks_and_writes_transaction(monkeypatch, db_session, fake_redis, dummy_file):
    # Stub OCR, NLP, Fraud, HS Mapper, and Audit
    monkeypatch.setattr("app.ocr.extract_text_from_image_bytes", lambda content: ("Mock Invoice Text", {}))
    monkeypatch.setattr("app.nlp.parse_invoice_text", lambda text: {
        "invoice_no": "INV-1001",
        "total_amount": 12500.0,
        "party": "Global Logistics Ltd",
        "hs_code": "847130"
    })
    monkeypatch.setattr("app.hs_mapper.lookup", lambda code: "Laptops and portable computers")
    monkeypatch.setattr("app.fraud.predict_risk", lambda features: 0.15)
    
    audit_calls = []
    monkeypatch.setattr("app.audit.append_audit", lambda action, payload: audit_calls.append((action, payload)))

    # Create Document in DB
    doc = Document(
        filename="success_test.png",
        original_filename="invoice.png",
        status="processing",
        processed=False,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    # Push job to stream
    job_payload = {
        "job_id": "job-101",
        "document_id": str(doc.id),
        "file_path": dummy_file,
        "attempt": "1",
        "enqueued_at": "2026-11-20T10:00:00Z"
    }
    entry_id = fake_redis.xadd(STREAM_KEY, job_payload)

    # Run handle_job
    handle_job(fake_redis, entry_id, job_payload)

    # Verify document updated
    db_session.refresh(doc)
    assert doc.status == "completed"
    assert doc.processed is True
    assert doc.fields["invoice_no"] == "INV-1001"
    assert doc.fields["hs_description"] == "Laptops and portable computers"

    # Verify transaction created
    txn = db_session.query(Transaction).filter(Transaction.document_id == doc.id).first()
    assert txn is not None
    assert txn.invoice_value == 12500.0
    assert txn.risk_score == 0.15
    assert txn.is_flagged is False
    assert txn.party == "Global Logistics Ltd"

    # Verify audit called
    assert len(audit_calls) == 1
    assert audit_calls[0][0] == "UPLOAD_DOCUMENT"

    # Verify stream has no pending unacked message
    pending = fake_redis.xpending(STREAM_KEY, CONSUMER_GROUP)
    assert pending["pending"] == 0


def test_failure_retry_attempt_1_to_2(monkeypatch, db_session, fake_redis, dummy_file):
    # Make OCR raise an exception
    def failing_ocr(content):
        raise RuntimeError("OCR service temporarily unavailable")

    monkeypatch.setattr("app.ocr.extract_text_from_image_bytes", failing_ocr)

    doc = Document(
        filename="retry_test.png",
        original_filename="invoice.png",
        status="processing",
        processed=False,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    job_payload = {
        "job_id": "job-102",
        "document_id": str(doc.id),
        "file_path": dummy_file,
        "attempt": "1",
        "enqueued_at": "2026-11-20T10:00:00Z"
    }
    entry_id = fake_redis.xadd(STREAM_KEY, job_payload)

    handle_job(fake_redis, entry_id, job_payload)

    # Document should still be processing
    db_session.refresh(doc)
    assert doc.status == "processing"

    # Original entry should be ACKed
    pending = fake_redis.xpending(STREAM_KEY, CONSUMER_GROUP)
    assert pending["pending"] == 0

    # New entry should be enqueued with attempt 2
    entries = fake_redis.xrange(STREAM_KEY)
    assert len(entries) == 2
    new_entry_id, new_data = entries[1]
    assert new_data["attempt"] == "2"
    assert new_data["document_id"] == str(doc.id)


def test_failure_third_attempt_marks_failed(monkeypatch, db_session, fake_redis, dummy_file):
    def failing_ocr(content):
        raise RuntimeError("Unrecoverable parsing error")

    monkeypatch.setattr("app.ocr.extract_text_from_image_bytes", failing_ocr)

    doc = Document(
        filename="fail_test.png",
        original_filename="invoice.png",
        status="processing",
        processed=False,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    job_payload = {
        "job_id": "job-103",
        "document_id": str(doc.id),
        "file_path": dummy_file,
        "attempt": "3",
        "enqueued_at": "2026-11-20T10:00:00Z"
    }
    entry_id = fake_redis.xadd(STREAM_KEY, job_payload)

    handle_job(fake_redis, entry_id, job_payload)

    # Document should be marked failed with processing_notes set
    db_session.refresh(doc)
    assert doc.status == "failed"
    assert "Unrecoverable parsing error" in doc.processing_notes

    # Original entry should be ACKed and no 4th attempt enqueued
    pending = fake_redis.xpending(STREAM_KEY, CONSUMER_GROUP)
    assert pending["pending"] == 0
    entries = fake_redis.xrange(STREAM_KEY)
    assert len(entries) == 1


def test_idempotency_skip_duplicate(monkeypatch, db_session, fake_redis, dummy_file):
    doc = Document(
        filename="idempotent_test.png",
        original_filename="invoice.png",
        status="processing",
        processed=False,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    # Existing transaction already created
    txn = Transaction(
        document_id=doc.id,
        invoice_value=999.0,
        hs_code="8471",
        party="ACME",
        risk_score=0.1,
        is_flagged=False,
        meta_info={}
    )
    db_session.add(txn)
    db_session.commit()

    ocr_called = []
    monkeypatch.setattr("app.ocr.extract_text_from_image_bytes", lambda content: ocr_called.append(True))

    job_payload = {
        "job_id": "job-104",
        "document_id": str(doc.id),
        "file_path": dummy_file,
        "attempt": "1",
        "enqueued_at": "2026-11-20T10:00:00Z"
    }
    entry_id = fake_redis.xadd(STREAM_KEY, job_payload)

    handle_job(fake_redis, entry_id, job_payload)

    # OCR should NOT have been called
    assert len(ocr_called) == 0

    # Only 1 transaction in DB
    all_txns = db_session.query(Transaction).filter(Transaction.document_id == doc.id).all()
    assert len(all_txns) == 1

    # Document marked completed and entry ACKed
    db_session.refresh(doc)
    assert doc.status == "completed"
    assert doc.processed is True
    pending = fake_redis.xpending(STREAM_KEY, CONSUMER_GROUP)
    assert pending["pending"] == 0

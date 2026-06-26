from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, Boolean, Text
from sqlalchemy.sql import func
from app.db import Base



class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=True)
    fields = Column(JSON)  # extracted fields
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed = Column(Boolean, default=False)
    processing_notes = Column(Text)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer)
    invoice_value = Column(Float)
    hs_code = Column(String)
    party = Column(String)
    risk_score = Column(Float)
    is_flagged = Column(Boolean, default=False)

    # ✅ renamed to avoid reserved attribute
    meta_info = Column("metadata", JSON)  # DB column name is still 'metadata'

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    action = Column(String)
    payload = Column(JSON)
    hash = Column(String)

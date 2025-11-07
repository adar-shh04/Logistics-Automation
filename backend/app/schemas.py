from pydantic import BaseModel
from typing import Optional, Dict, Any

class UploadResponse(BaseModel):
    document_id: int
    transaction_id: int
    fields: Dict[str, Any]
    risk_score: float
    is_flagged: bool

class TransactionResponse(BaseModel):
    id: int
    invoice_value: Optional[float]
    hs_code: Optional[str]
    party: Optional[str]
    risk_score: float
    is_flagged: bool
    metadata: Dict[str, Any]

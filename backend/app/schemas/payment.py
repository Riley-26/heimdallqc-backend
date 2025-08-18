from datetime import datetime
from typing import Optional
from pydantic import BaseModel

# -- INPUT MODELS

class PaymentCreate(BaseModel):
    pass
    
    
# -- RESPONSE MODELS

class PaymentResponse(BaseModel):
    """Base payment model"""
    owner_id: int
    status: str
    name: str
    purchase_type: str

class PaymentListResponse(PaymentResponse):
    """Payments listed response"""
    invoice_id: Optional[str] = None
    value: int
    created_at: datetime
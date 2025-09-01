from datetime import datetime
from typing import Literal, Optional
from pydantic import UUID4, BaseModel, Field

# -- BASE MODEL

class PaymentCreate(BaseModel):
    """Base payment create model"""
    owner_unique_id: UUID4
    price_id: Optional[str] = Field(None, description="Stripe price ID (for subscriptions)")
    success_url: str
    payment_type: Literal["subscription", "one_off"]
    name: str
    amount: int = Field(None, description="Amount in pence (for one-off payments)")
    currency: str = Field(default="gbp")
    description: Optional[str] = None
    
# -- INPUT MODELS

class PaymentUpdate(BaseModel):
    """Updates the payment using Stripe webhooks"""
    session_id: Optional[str] = None
    subscription_id: Optional[str] = None
    invoice_id: Optional[str] = None
    
class SubscriptionUpdate(BaseModel):
    """Updates subscription payment"""
    owner_unique_id: UUID4
    new_plan_id: str
    prorate: bool = Field(default=True)
    
class SubscriptionCancel(BaseModel):
    owner_unique_id: UUID4
    is_immediate_cancel: bool = Field(default=False, description="True for immediate with refund, False for end of period")
    
class PaymentMethodDelete(BaseModel):
    payment_method_id: str
    
# -- RESPONSE MODELS

class PaymentResponse(BaseModel):
    """Base payment model"""
    owner_unique_id: UUID4
    status: str
    name: str
    payment_type: str
    currency: str
    desc: Optional[str] = None
    
class PaymentDetailResponse(PaymentResponse):
    """Detailed payment response"""
    amount: str
    created_at: datetime
    event_id: Optional[str] = None
    pdf_url: Optional[str] = None
    session_id: Optional[str] = None
    subscription_id: Optional[str] = None
    invoice_id: Optional[str] = None
    price_id: Optional[str] = None

class PaymentListResponse(BaseModel):
    """Payments listed response"""
    amount: int
    status: str
    created_at: datetime
    pdf_link: Optional[str] = None
    
class PaymentMethodListResponse(BaseModel):
    """Payment methods listed response"""
    payment_method_id: str
    payment_method_type: str
    card: Optional[dict] = None   # Will contain card details if type is 'card'
    created_at: datetime

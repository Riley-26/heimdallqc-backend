from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, UUID4

# -- AUTH SCHEMAS

class LoginRequest(BaseModel):
    """Authentication credentials"""
    email: EmailStr
    password: str

class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"

class PasswordReset(BaseModel):
    """Password reset request"""
    email: EmailStr

class PasswordUpdate(BaseModel):
    """Password update with token"""
    email: str
    token: str
    new_password: str


# -- INPUT SCHEMAS

class OwnerCreate(BaseModel):
    """Fields required when creating a new owner"""
    email: EmailStr
    name: str
    password: str = Field(..., min_length=8)
    domain: str
    company: Optional[str] = None

    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class OwnerUpdate(BaseModel):
    """Fields that can be updated"""
    name: Optional[str] = None
    domain: Optional[str] = None
    company: Optional[str] = None

class SettingsUpdate(BaseModel):
    """Update owner settings"""
    function_pref: Dict[str, bool]
    ui_pref: Dict[str, bool]
    ai_threshold_option: int = Field(ge=40, le=99)
    privacy_mode: bool
    
class EmailPrefsUpdate(BaseModel):
    """Update owner email preferences"""
    low_tokens_option: Dict[str, bool]
    tokens_threshold: Dict[str, int]

class PlanUpdate(BaseModel):
    """Update plan"""
    owner_id: UUID4
    plan_name: str = Field(..., pattern='^(Extrinsic|Intrinsic|Combo|None)$')
    
class PlanCancel(BaseModel):
    """Cancel plan"""
    owner_id: UUID4
    immediate: bool

class TokenPurchase(BaseModel):
    """Purchase additional tokens"""
    owner_id: UUID4
    pack_name: str = Field(..., pattern='^(sm|md|lg|xl)$')
    
class OwnerJwt(BaseModel):
    """JWT request schema"""
    name: Optional[str] = None
    email: str
    sub: Optional[str] = None
    id: str
    exp: int
    iat: Optional[int] = None


# -- RESPONSE SCHEMAS

class OwnerBase(BaseModel):
    """Base fields returned in all owner responses"""
    id: int
    unique_id: UUID4
    email: EmailStr
    name: str
    domain: str
    company: Optional[str] = None
    is_active: bool
    is_verified: bool
    is_private: bool

    class Config:
        from_attributes = True

class OwnerResponse(OwnerBase):
    """Standard owner response with usage data"""
    current_tokens: int
    tokens_used: int
    plagiarisms_prevented: int
    entries_needing_action: int
    texts_analysed: int

class OwnerDetailResponse(OwnerResponse):
    """Detailed owner response with preferences"""
    claimed_trial: bool
    trial_used: bool
    domain_id: int
    verified_month_end: Optional[datetime] = None
    plan: dict
    function_pref: dict
    ui_pref: dict
    ai_threshold_option: int
    tokens_threshold: int
    low_tokens_option: bool
    created_at: datetime
    updated_at: datetime
    verified_at: Optional[datetime] = None
    customer_id: Optional[str] = None
    subscription_id: Optional[str] = None
    session_ids: Optional[list] = []
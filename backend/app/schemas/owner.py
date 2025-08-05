from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

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
    new_password: str = Field(..., min_length=8)


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
    """Update owner preferences"""
    function_pref: Dict[str, bool]
    ui_pref: Dict[str, bool]
    ai_threshold_option: int = Field(ge=0, le=99)

class PlanUpdate(BaseModel):
    """Update plan"""
    owner_id: int
    plan_name: str = Field(..., pattern='^(extrinsic|intrinsic|combo|none)$')
    
class PlanCancel(BaseModel):
    """Cancel plan"""
    owner_id: int

class TokenPurchase(BaseModel):
    """Purchase additional tokens"""
    owner_id: int
    pack_name: str = Field(..., pattern='^(sm|md|lg|xl)$')


# -- RESPONSE SCHEMAS

class OwnerBase(BaseModel):
    """Base fields returned in all owner responses"""
    id: int
    email: EmailStr
    name: str
    domain: str
    company: Optional[str] = None
    is_active: bool
    is_verified: bool

    class Config:
        from_attributes = True

class OwnerResponse(OwnerBase):
    """Standard owner response with usage data"""
    current_tokens: int
    tokens_used: int
    watermarks_made: int
    plagiarisms_prevented: int

class OwnerDetailResponse(OwnerResponse):
    """Detailed owner response with preferences"""
    domain_id: int
    verified_month_end: Optional[datetime] = None
    plan: dict
    function_pref: dict
    ui_pref: dict
    ai_threshold_option: int
    created_at: datetime
    updated_at: datetime
    verified_at: Optional[datetime] = None
    
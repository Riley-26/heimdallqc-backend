from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr, field_validator
from enum import Enum


class OwnerBase(BaseModel):
    email: EmailStr
    name: str
    domain: str
    company: str
    
    
class OwnerCreate(OwnerBase):
    password: str
    
    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class OwnerUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None


class OwnerResponse(OwnerBase):
    id: int
    domain: str
    is_active: bool
    is_verified: bool
    monthly_submission_limit: int
    monthly_submissions_used: int
    created_at: datetime

    class Config:
        field_attributes = True


class OwnerLogin(BaseModel):
    email: EmailStr
    password: str
    
    
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: str
    token: str
    new_password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    

class SiteBase(BaseModel):
    domain: str


class SiteResponse(SiteBase):
    id: int
    is_active: bool
    total_requests: int
    last_used_at: datetime | None
    created_at: datetime
    
    class Config:
        field_attributes = True
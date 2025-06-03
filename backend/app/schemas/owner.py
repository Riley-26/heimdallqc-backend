from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr, field_validator
from enum import Enum


class OwnerBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    site_url: str
    
    
class OwnerCreate(OwnerBase):
    password: str
    
    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v
    
    
class OwnerUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    website_url: Optional[str] = None
    
    
class OwnerResponse(BaseModel):
    id: int
    api_key: str
    active: bool
    verified: bool
    # Limits
    
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        field_attributes = True
        

# Authentication schemas
class UserLogin(BaseModel):
    email: EmailStr
    password: str
    
    
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    
    
class PasswordReset(BaseModel):
    email: EmailStr
    
    
class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    
    @field_validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v
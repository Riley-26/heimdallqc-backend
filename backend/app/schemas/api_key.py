from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, EmailStr
from enum import Enum


class ApiKeyBase(BaseModel):
    name: str
    # Limits
    
    source_url: str
    
    
class ApiKeyCreate(ApiKeyBase):
    pass


class ApiKeyUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    # Limits
    
     
class ApiKeyResponse(BaseModel):
    id: int
    owner_id: int
    key: str  # Full key returned only on creation
    is_active: bool
    # Analytics/limits
    
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        field_attributes = True
        
        
class ApiKeyListResponse(BaseModel):
    """Response for listing API keys (without exposing full key)"""
    id: int
    name: str
    masked_key: str  # Only show masked version
    is_active: bool
    # Analytics/limits
    
    last_used_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        field_attributes = True
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, EmailStr, UUID4
from enum import Enum

# -- BASE MODEL

class ApiKeyBase(BaseModel):
    name: str

# -- INPUT MODELS

class ApiKeyCreate(ApiKeyBase):
    pass

class ApiKeyDeactivate(BaseModel):
    api_key_id: int

# -- RESPONSE MODELS

class ApiKeyResponse(BaseModel):
    id: int
    owner_unique_id: UUID4
    name: str
    is_active: bool

    class Config:
        field_attributes = True
        
class ApiKeyReveal(BaseModel):
    key: str
    name: str
    is_active: bool
        
class ApiKeyDetailResponse(ApiKeyResponse):
    masked_key: str
    created_at: datetime
    total_requests: int
    last_used_at: Optional[datetime] = None

class ApiKeyListResponse(BaseModel):
    """Response for listing API key names"""
    id: int
    name: str
    masked_key: str
    is_active: bool

    class Config:
        field_attributes = True
        
class ApiKeyList(BaseModel):
    keys: List[ApiKeyListResponse]
    total: int
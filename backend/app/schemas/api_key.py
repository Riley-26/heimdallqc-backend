from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, EmailStr
from enum import Enum


class ApiKeyBase(BaseModel):
    name: str


class ApiKeyCreate(ApiKeyBase):
    pass


class ApiKeyUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class ApiKeyResponse(ApiKeyBase):
    id: int
    owner_id: int
    key: str  # Full key returned only on creation
    is_active: bool
    total_requests: int
    last_used_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        field_attributes = True


class ApiKeyListResponse(BaseModel):
    """Response for listing API keys (without exposing full key)"""
    id: int
    name: str
    masked_key: str
    is_active: bool
    total_requests: int
    last_used_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        field_attributes = True
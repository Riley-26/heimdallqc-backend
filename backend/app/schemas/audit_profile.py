from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, EmailStr, UUID4
from enum import Enum

# Base model

class AuditProfileBase(BaseModel):
    name: str
    
# Input models

class AuditProfileCreate(AuditProfileBase):
    """Create an audit profile"""
    desc: Optional[str] = None
    schedule: dict
    pages: list

class AuditProfileEdit(AuditProfileBase):
    """Edit an audit profile"""
    audit_profile_id: str
    desc: Optional[str] = None
    schedule: dict
    pages: list

class AuditProfileDelete(BaseModel):
    """Delete an audit profile"""
    audit_profile_id: str
    
# Response models

class AuditProfileResponseBase(BaseModel):
    """Base class for audit profile responses"""
    id: int
    name: str
    desc: Optional[str] = None
    pdf_link: Optional[str] = None
    is_active: bool
    
class AuditProfileResponse(AuditProfileResponseBase):
    """Main class for audit profile responses"""
    created_at: datetime
    pages: list
    schedule: dict
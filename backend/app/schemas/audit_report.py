from datetime import datetime
from typing import Optional
from pydantic import BaseModel

# Input models

class AuditReportCreate(BaseModel):
    """Create an audit report"""
    audit_profile_id: str
    score: int
    status: str
    result: dict
    pages: list
    frequency: str
    day: Optional[str] = None
    time: Optional[str] = None

class AuditReportDelete(BaseModel):
    """Delete an audit report"""
    audit_profile_id: str
    
# Response models

class AuditReportResponseBase(BaseModel):
    """Base class for audit report responses"""
    id: int
    score: int
    status: str
    
class AuditReportResponse(AuditReportResponseBase):
    """Main class for audit report responses"""
    owner_id: int
    audit_profile_id: int
    pages: list
    frequency: str
    day: Optional[str]
    time: Optional[str]
    pdf_link: str
    created_at: datetime
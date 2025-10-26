from datetime import datetime
from typing import Optional
from pydantic import BaseModel

# Input models

class AuditReportCreate(BaseModel):
    """Create an audit report"""
    name: str
    score: int
    status: str
    results: list
    pages: list
    frequency: str
    day: Optional[str] = None
    time: Optional[str] = None

class AuditReportDelete(BaseModel):
    """Delete an audit report"""
    id: str
    
# Response models

class AuditReportResponseBase(BaseModel):
    """Base class for audit report responses"""
    id: int
    score: int
    status: str
    name: str
    
class AuditReportResponse(AuditReportResponseBase):
    """Main class for audit report responses"""
    owner_id: int
    results: list
    pages: list
    frequency: str
    day: Optional[str]
    time: Optional[str]
    pdf_link: str
    created_at: datetime
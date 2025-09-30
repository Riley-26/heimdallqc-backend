from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, UUID4

# -- BASE MODEL

class SubmissionBase(BaseModel):
    """Base fields for all submissions"""
    orig_text: str = Field(..., min_length=1, max_length=10000)
    meets_requirements: bool = False
    action_needed: bool = False
    
# -- INPUT MODELS
    
class SubmissionAuto(BaseModel):
    """Fields required when API creates a new submission"""
    orig_text: str
    work_id: str
    question_result: bool
    domain: str
    page_link: str
    webhook_url: str

class SubmissionManual(SubmissionBase):
    """Fields required when manually uploading"""
    api_key_id: str
    manual_upload: bool = True
    
class SubmissionDelete(BaseModel):
    """Fields for deleting a submission entry"""
    submission_unique_id: str
    
class SubmissionEdit(BaseModel):
    """Fields for editing an existing submission"""
    submission_unique_id: str
    edit_text: str
    rescan: bool
    
# -- RESPONSE MODELS    

class SubmissionResponseBase(BaseModel):
    """Base fields for all submission responses"""
    id: int
    status: str
    action_needed: bool
    manual_upload: bool
    tokens_used: int
    created_at: datetime
    
    class Config:
        field_attributes = True
        
class SubmissionCreated(BaseModel):
    """For when a submission is created via API (not manual upload)"""
    status: int
    message: str
    text: Optional[str] = None
    modifiedText: Optional[str] = None
    workId: Optional[str] = None
        
class SubmissionResponse(SubmissionResponseBase):
    """Basic response for general use"""
    unique_id: UUID4
    work_id: Optional[str] = None
    meets_requirements: bool
    orig_text: str
    edit_text: Optional[str] = None
    temp_text: Optional[str] = Field(None, max_length=10000)
    ai_result: dict
    plag_result: dict
    edited: bool
    page_link: Optional[str] = None
    domain: Optional[str] = None
    function_pref: str
    
class SubmissionDetailResponse(SubmissionResponse):
    """Detailed response for admin/owner views"""
    api_key_id: int
    owner_id: int
    failure_reason: Optional[str] = None
    completed_processing_at: Optional[datetime] = None
    message: Optional[str] = None
    edited_at: Optional[datetime] = None

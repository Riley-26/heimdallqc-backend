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
    
class SubmissionAuto(SubmissionBase):
    """Fields required when API creates a new submission"""
    question_result: bool
    manual_upload: bool = False
    domain: str
    page_link: str

class SubmissionManual(SubmissionBase):
    """Fields required when manually uploading"""
    api_key_id: str
    manual_upload: bool = True
    
class SubmissionDelete(BaseModel):
    """Fields for deleting a submission entry"""
    submission_id: int
    
class SubmissionEdit(BaseModel):
    """Fields for editing an existing submission"""
    submission_unique_id: int
    edit_text: str
    
# -- RESPONSE MODELS    

class SubmissionResponseBase(BaseModel):
    """Base fields for all submission responses"""
    id: int
    status: str
    orig_text_prev: Optional[str] = None
    action_needed: bool
    manual_upload: bool
    tokens_used: int
    created_at: datetime
    
    class Config:
        field_attributes = True
        
class SubmissionResponse(SubmissionResponseBase):
    """Basic response for general use"""
    meets_requirements: bool
    failure_reason: Optional[str] = None
    completed_processing_at: Optional[datetime] = None
    message: Optional[str] = None
    
class SubmissionDetailResponse(SubmissionResponse):
    """Detailed response for admin/owner views"""
    unique_id: UUID4
    orig_text: str
    edit_text: Optional[str] = None
    ai_result: dict
    plag_result: dict
    domain: Optional[str] = None
    page_link: Optional[str] = None
    edited: bool
    edited_at: Optional[datetime] = None
    function_pref: str
    temp_text: Optional[str] = Field(None, max_length=10000)
    
class SubmissionHookResponse(BaseModel):
    """Response for webhook, owners save this data"""
    watermark_id: int
    temp_text: str
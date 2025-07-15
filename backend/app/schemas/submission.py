from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import enum

class SubmissionBase(BaseModel):
    orig_text: str = Field(..., min_length=1, max_length=10000)
    edit_text: Optional[str] = Field(None, max_length=10000)
    domain: Optional[str] = Field(None, max_length=1000)
    page_link: Optional[str] = Field(None, max_length=1000)
    custom_id: Optional[int] = None
    question_result: Optional[bool] = None
    manual_upload: bool = False
    action_needed: bool = False
    edited: bool = False
    edited_at: Optional[datetime] = None
    function_pref: Optional[str] = None

class SubmissionCreate(SubmissionBase):
    owner_id: Optional[int] = None
    key_id: str
    temp_text: Optional[str] = Field(None, max_length=10000)
    
    @field_validator('orig_text', 'edit_text')
    def validate_text(cls, v):
        # Remove excessive whitespace
        cleaned = ' '.join(v.split())
        if len(cleaned) < 5:
            raise ValueError('Text must be at least 5 characters long after cleaning')
        return cleaned
    
class SubmissionEdit(BaseModel):
    owner_id: Optional[int] = None
    id: int
    new_text: str


class SubmissionResponse(BaseModel):
    id: int
    owner_id: int
    status: str
    orig_text_length: int
    meets_requirements: Optional[bool] = None
    action_needed: bool
    failure_reason: Optional[str] = None
    created_at: datetime
    completed_processing_at: Optional[datetime] = None
    message: Optional[str] = None
    manual_upload: bool

    class Config:
        field_attributes = True


class SubmissionDetailResponse(SubmissionResponse):
    """More detailed response for admin/owner views"""
    orig_text: str
    edit_text: Optional[str]
    ai_result: dict
    plag_result: dict
    domain: Optional[str] = None
    page_link: Optional[str] = None
    edited: bool
    edited_at: Optional[datetime] = None
    function_pref: str
    temp_text: Optional[str] = Field(None, max_length=10000)

    class Config:
        field_attributes = True

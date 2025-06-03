from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import enum

class SubmissionBase(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    source_url: Optional[str] = Field(None, max_length=1000)


class SubmissionCreate(SubmissionBase):
    api_key: str = Field(..., min_length=8)
    
    @field_validator('text')
    def validate_text(cls, v):
        # Remove excessive whitespace
        cleaned = ' '.join(v.split())
        if len(cleaned) < 40:
            raise ValueError('Text must be at least 40 characters long after cleaning')
        return cleaned


class SubmissionResponse(BaseModel):
    id: int
    status: str
    text_length: int
    meets_requirements: Optional[bool] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    completed_processing_at: Optional[datetime] = None
    message: Optional[str] = None

    class Config:
        field_attributes = True


class SubmissionDetailResponse(SubmissionResponse):
    """More detailed response for admin/owner views"""
    text: str
    processing_result: Optional[Dict[str, Any]] = None
    source_url: Optional[str] = None

    class Config:
        field_attributes = True


class SubmissionListResponse(BaseModel):
    """Simplified response for listing submissions"""
    id: int
    status: str
    text_preview: str = Field(..., description="First 100 characters of text")
    text_length: int
    meets_requirements: Optional[bool] = None
    source_url: Optional[str] = None
    created_at: datetime

    class Config:
        field_attributes = True
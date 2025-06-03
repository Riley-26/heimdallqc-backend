from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import enum

class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"                             # Just received, not started processing
    PROCESSING = "processing"                       # Currently being processed
    SUCCESS = "success"                             # Processed successfully and meets requirements
    FAILED_PROCESSING = "failed_processing"         # Error during processing (API failure, etc.)
    FAILED_REQUIREMENTS = "failed_requirements"     # Processed but doesn't meet requirements
    TIMEOUT = "timeout"                             # Processing timed out, moved to background
    BACKGROUND_PROCESSING = "background_processing" # Currently processing in background


class SubmissionBase(BaseModel):
    text: str = Field(..., min_length=1, max_length=14000)
    source_url: Optional[str] = Field(None, max_length=1000)
    context: Optional[Dict[str, Any]] = None
    custom_id: Optional[int] = None


class SubmissionCreate(SubmissionBase):
    api_key: str = Field(..., min_length=8)
    
    @field_validator('text')
    def validate_text(cls, v):
        # Remove excessive whitespace
        cleaned = ' '.join(v.split())
        if len(cleaned) < 40:
            raise ValueError('Text must be at least 40 characters long after cleaning')
        return cleaned


class SubmissionUpdate(BaseModel):
    status: Optional[ProcessingStatus] = None
    processing_result: Optional[Dict[str, Any]] = None
    meets_requirements: Optional[bool] = None
    score: Optional[float] = Field(None, ge=0, le=100)
    failure_reason: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class SubmissionResponse(BaseModel):
    id: int
    status: ProcessingStatus
    text_length: int
    meets_requirements: Optional[bool] = None
    score: Optional[float] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    completed_processing_at: Optional[datetime] = None
    processing_duration_ms: Optional[int] = None
    message: Optional[str] = None  # User-friendly message

    class Config:
        field_attributes = True
        
        
class SubmissionDetailResponse(SubmissionResponse):
    """More detailed response for admin/owner views"""
    api_key_id: int
    text: str  # Include full text
    text_word_count: Optional[int] = None
    processing_result: Optional[Dict[str, Any]] = None
    source_url: Optional[str] = None
    source_domain: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    started_processing_at: Optional[datetime] = None
    retry_count: int
    forwarded_successfully: bool
    forwarded_to_main_system_at: Optional[datetime] = None

    class Config:
        field_attributes = True
        

class SubmissionListResponse(BaseModel):
    """Simplified response for listing submissions"""
    id: int
    status: ProcessingStatus
    text_preview: str = Field(..., description="First 100 characters of text")
    text_length: int
    meets_requirements: Optional[bool] = None
    score: Optional[float] = None
    source_domain: Optional[str] = None
    created_at: datetime
    completed_processing_at: Optional[datetime] = None

    class Config:
        field_attributes = True
        
        
# Analytics schemas
class SubmissionStats(BaseModel):
    total_submissions: int
    successful_submissions: int
    failed_submissions: int
    pending_submissions: int
    average_processing_time_ms: Optional[float] = None
    success_rate: float = Field(..., ge=0, le=100)
    
    
class SubmissionAnalytics(BaseModel):
    """Analytics data for dashboard"""
    today: SubmissionStats
    this_week: SubmissionStats
    this_month: SubmissionStats
    top_domains: List[Dict[str, Any]]  # [{"domain": "example.com", "count": 50}]
    processing_times: List[float]  # For charts
    hourly_distribution: List[Dict[str, Any]]  # For activity charts
    
    
# Batch operations
class SubmissionBatchUpdate(BaseModel):
    submission_ids: List[int]
    status: Optional[ProcessingStatus] = None
    action: Optional[str] = None  # "retry", "delete", "archive"


class SubmissionFilter(BaseModel):
    """For filtering submissions in list views"""
    status: Optional[List[ProcessingStatus]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    source_domain: Optional[str] = None
    meets_requirements: Optional[bool] = None
    min_score: Optional[float] = Field(None, ge=0, le=100)
    search_text: Optional[str] = None
    
    
class SubmissionExport(BaseModel):
    """For exporting submission data"""
    format: str = Field(..., pattern="^(csv|json|xlsx)$")
    include_text: bool = True
    include_metadata: bool = False
    filters: Optional[SubmissionFilter] = None
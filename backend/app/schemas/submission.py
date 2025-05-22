from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class ProcessingStatus(str, Enum):
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED_PROCESSING = "failed_processing"
    FAILED_REQUIREMENTS = "failed_requirements"

class SubmissionBase(BaseModel):
    text: str
    api_key: str
    source_url: Optional[str] = None

class SubmissionCreate(SubmissionBase):
    pass

class SubmissionResponse(BaseModel):
    id: int
    status: ProcessingStatus
    created_at: datetime
    processed_at: Optional[datetime] = None
    meets_requirements: bool = False
    failure_reason: Optional[str] = None

    class Config:
        orm_mode = True
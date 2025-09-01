from typing import Dict, Optional
from pydantic import BaseModel, UUID4

# -- BASE MODEL

class WatermarkBase(BaseModel):
    """Base model for all watermark responses"""
    ai_score: int
    plag_score: int
    citations: Optional[Dict[str, str]] = None

# -- INPUT MODELS

class WatermarkCreate(WatermarkBase):
    """Input model for watermark creation"""
    owner_unique_id: UUID4
    submission_id: int

# -- RESPONSE MODELS

class WatermarkResponseBase(BaseModel):
    """Base response model for watermarks"""
    submission_id: int

class WatermarkResponse(WatermarkResponseBase):
    """Basic response for most uses"""
    ai_score: int
    plag_score: int
    citations: Optional[Dict[str, str]] = None
    
class WatermarkDetailResponse(WatermarkResponse):
    """Detailed response for debugging"""
    id: int
    owner_unique_id: UUID4
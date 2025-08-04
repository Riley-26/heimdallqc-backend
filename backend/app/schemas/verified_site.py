from datetime import datetime
from typing import Optional
from pydantic import BaseModel

# -- BASE MODEL

class SiteBase(BaseModel):
    domain: str

# -- RESPONSE MODELS

class SiteResponseBase(SiteBase):
    id: int
    is_active: bool
    
    class Config:
        field_attributes = True

class SiteSimpleResponse(SiteResponseBase):
    pass
        
class SiteDetailResponse(SiteResponseBase):
    total_requests: int
    last_used_at: Optional[datetime] = None
    created_at: datetime
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, EmailStr, UUID4
from enum import Enum

# -- BASE MODEL

class WebhookBase(BaseModel):
    name: str

# -- INPUT MODELS

class WebhookCreate(WebhookBase):
    endpoint: str

class WebhookDelete(BaseModel):
    webhook_id: int

# -- RESPONSE MODELS

class WebhookResponse(BaseModel):
    id: int
    owner_unique_id: UUID4
    name: str
    endpoint: str

    class Config:
        field_attributes = True

class WebhookListResponse(BaseModel):
    """Response for listing webhooks"""
    id: int
    name: str
    endpoint: str

    class Config:
        field_attributes = True
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Enum, Float, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..db.database import Base
from datetime import datetime
import enum


class ProcessingStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class Submission(Base):
    __tablename__ = "submissions"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=False, index=True)
    
    # Content
    orig_text = Column(Text, nullable=False)
    orig_text_length = Column(Integer, nullable=False)
    edit_text = Column(Text, nullable=True)
    edit_text_length = Column(Integer, nullable=True)
    custom_id = Column(Integer, nullable=True)
    question_result = Column(Boolean, nullable=True)
    manual_upload = Column(Boolean, nullable=False)
    
    # Processing
    status = Column(String(50), default=ProcessingStatus.PENDING, index=True)
    meets_requirements = Column(Boolean, nullable=True)
    failure_reason = Column(String(500), nullable=True)
    action_needed = Column(Boolean, nullable=False)
    edited = Column(Boolean, nullable=False)
    function_pref = Column(String(20), default="Auto-cite", nullable=True)
    tokens_used = Column(Integer, nullable=False, default=0)
    ai_result = Column(JSON, nullable=True)
    plag_result = Column(JSON, nullable=True)
    temp_text = Column(Text, nullable=True)
    
    # Basic tracking
    domain = Column(String(1000), nullable=True)
    page_link = Column(String(1000), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_processing_at = Column(DateTime(timezone=True), nullable=True)
    edited_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    owner = relationship("Owner", backref="submissions")
    api_key_obj = relationship("ApiKey", back_populates="submissions")

    def __repr__(self):
        return f"<Submission(id={self.id}, status={self.status}, owner_id={self.owner_id})>"
    
    @property
    def is_completed(self):
        """Check if processing is completed"""
        return self.status in [ProcessingStatus.SUCCESS, ProcessingStatus.FAILED]
    
    @property
    def is_processing(self):
        """Check if currently being processed"""
        return self.status == ProcessingStatus.PROCESSING
    
    def update_status(self, new_status: str, reason: str = None):
        """Helper method to update status with timestamp"""
        self.status = new_status
        
        if self.is_completed:
            self.completed_processing_at = datetime.now()
        
        if reason:
            self.failure_reason = reason
            
    def update_action(self, action: bool):
        """Action needed"""
        if self.action_needed != action:
            self.action_needed = action
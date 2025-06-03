from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Enum, Float, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..db.database import Base
from datetime import datetime
import enum
from ..schemas.submission import ProcessingStatus


class Submission(Base):
    __tablename__ = "submissions"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=False, index=True)
    
    # Content
    text = Column(Text, nullable=False)
    text_length = Column(Integer, nullable=False)  # Cache for quick queries
    custom_id = Column(Integer, index=True)
    
    # Processing information
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING, index=True)
    processing_result = Column(JSON, nullable=True)  # Store full analysis results
    
    # Requirements checking
    meets_requirements = Column(Boolean, nullable=True)  # Quick boolean check
    score = Column(Float, nullable=True)  # Confidence in the analysis (0-1)
    
    # Error handling
    failure_reason = Column(String(500), nullable=True)
    error_details = Column(JSON, nullable=True)  # Detailed error info for debugging
    retry_count = Column(Integer, default=0)  # How many times we've retried processing
    
    # Source information
    source_url = Column(String(1000), nullable=True)  # Where the submission came from
    source_domain = Column(String(255), nullable=True, index=True)  # Extracted domain for analytics
    
    # Context
    context = Column(JSON, nullable=True)  # Page context, form data, etc.
    
    # Processing timing
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    started_processing_at = Column(DateTime(timezone=True), nullable=True)
    completed_processing_at = Column(DateTime(timezone=True), nullable=True)
    
    # System interaction
    forwarded_to_main_system_at = Column(DateTime(timezone=True), nullable=True)
    forwarded_successfully = Column(Boolean, default=False)
    main_system_response = Column(JSON, nullable=True)
    
    # Analytics and tracking
    processing_duration_ms = Column(Integer, nullable=True)  # How long processing took
    
    # Soft delete (for data retention)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False, index=True)
    
    # Relationships
    owner = relationship("Owner", backref="submissions")
    api_key_obj = relationship("ApiKey", back_populates="submissions")

    def __repr__(self):
        return f"<Submission(id={self.id}, status={self.status}, owner_id={self.owner_id})>"
    
    @property
    def processing_time_seconds(self):
        """Calculate processing time in seconds"""
        if self.started_processing_at and self.completed_processing_at:
            delta = self.completed_processing_at - self.started_processing_at
            return delta.total_seconds()
        return None
    
    @property
    def is_completed(self):
        """Check if processing is completed (success or failed)"""
        return self.status in [
            ProcessingStatus.SUCCESS,
            ProcessingStatus.FAILED_PROCESSING,
            ProcessingStatus.FAILED_REQUIREMENTS
        ]
    
    @property
    def is_processing(self):
        """Check if currently being processed"""
        return self.status in [
            ProcessingStatus.PROCESSING,
            ProcessingStatus.BACKGROUND_PROCESSING
        ]
    
    def update_status(self, new_status: ProcessingStatus, reason: str = None):
        """Helper method to update status with timestamp"""
        self.status = new_status
        
        if new_status == ProcessingStatus.PROCESSING:
            self.started_processing_at = datetime.now()
        elif self.is_completed:
            self.completed_processing_at = datetime.now()
            if self.started_processing_at:
                delta = self.completed_processing_at - self.started_processing_at
                self.processing_duration_ms = int(delta.total_seconds() * 1000)
        
        if reason:
            self.failure_reason = reason
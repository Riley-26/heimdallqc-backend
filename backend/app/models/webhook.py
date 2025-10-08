from datetime import datetime
import secrets
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..db.database import Base
import string

class Webhook(Base):
    __tablename__ = "webhooks"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False, index=True)
    
    # Webhook details
    endpoint = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    
    # Usage tracking
    total_requests = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    owner = relationship("Owner", back_populates="webhooks")
    submissions = relationship("Submission", back_populates="webhook_obj")

    def __repr__(self):
        return f"<Webhook(id={self.id}, name={self.name}, owner_id={self.owner_id})>"
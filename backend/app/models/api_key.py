from datetime import datetime
import secrets
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..db.database import Base
import string

class ApiKey(Base):
    __tablename__ = "api_keys"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False, index=True)
    
    # API key details
    key = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Usage tracking
    total_requests = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    owner = relationship("Owner", back_populates="api_keys")
    submissions = relationship("Submission", back_populates="api_key_obj")

    def __repr__(self):
        return f"<ApiKey(id={self.id}, name={self.name}, owner_id={self.owner_id})>"
    
    @staticmethod
    def generate_key():
        """Generate a secure API key"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(48))
    
    @property
    def masked_key(self):
        """Return a masked version of the API key for display"""
        return f"{self.key[:8]}...{self.key[-4:]}"
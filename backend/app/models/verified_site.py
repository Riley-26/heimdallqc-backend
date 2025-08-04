from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..db.database import Base

class VerifiedSite(Base):
    __tablename__ = "verified_sites"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    domain = Column(String(100), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Usage tracking
    total_requests = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    owner = relationship("Owner", backref="verified_site")
    
    def __repr__(self):
        return f"<Verified_site(id={self.id}, domain={self.domain})>"
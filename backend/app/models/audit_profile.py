from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..db.database import Base

class AuditProfile(Base):
    __tablename__ = "audit_profiles"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False, index=True)
    
    # Config
    name = Column(String(255), nullable=False)
    desc = Column(Text, nullable=True)
    pages = Column(JSON, nullable=False, default="{}")
    schedule = Column(JSON, nullable=False, default=list)
    
    pdf_link = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    owner = relationship("Owner", back_populates="audit_profiles")
    
    def __repr__(self):
        return f"<AuditProfile(id={self.id}, name={self.name}, owner_id={self.owner_id})>"
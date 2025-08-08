from sqlalchemy import JSON, Column, ForeignKey, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..db.database import Base

class Watermark(Base):
    __tablename__ = "watermarks"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, index=True)
    
    ai_score = Column(Integer, nullable=False)
    plag_score = Column(Integer, nullable=False)
    
    citations = Column(JSON, nullable=True)
    
    # Relationships
    owner = relationship("Owner", backref="watermarks")
    api_key_obj = relationship("ApiKey", back_populates="watermarks")
    
    def __repr__(self):
        return f"<Watermark(id={self.id}, status={self.status}, owner_id={self.owner_id})>"
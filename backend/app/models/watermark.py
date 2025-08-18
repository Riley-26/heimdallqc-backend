from sqlalchemy import JSON, Column, ForeignKey, Integer
from sqlalchemy.orm import relationship
from ..db.database import Base

class Watermark(Base):
    __tablename__ = "watermarks"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, index=True, unique=True)
    
    ai_score = Column(Integer, nullable=False)
    plag_score = Column(Integer, nullable=False)
    
    citations = Column(JSON, nullable=True)
    
    # Relationships
    owner = relationship("Owner", back_populates="watermarks")
    submission = relationship("Submission", back_populates="watermark", uselist=False, single_parent=True)
    
    def __repr__(self):
        return f"<Watermark(id={self.id}, status={self.status}, owner_id={self.owner_id})>"
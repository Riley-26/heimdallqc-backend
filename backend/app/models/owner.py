from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..db.database import Base


class Owner(Base):
    __tablename__ = "owners"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Authentication
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # Basic profile
    name = Column(String(200), nullable=False)
    domain = Column(String(200), nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Usage tracking
    monthly_submission_limit = Column(Integer, default=1000)
    monthly_submissions_used = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    api_keys = relationship("ApiKey", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Owner(id={self.id}, email={self.email})>"
    
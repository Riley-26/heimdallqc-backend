from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..db.database import Base


class Owner(Base):
    __tablename__ = "owners"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Authentication
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    
    # Profile info
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Billing
    
    
    # Contact
    site_url = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Password reset fields
    reset_token = Column(String(255), nullable=True)
    reset_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Email verification
    verification_token = Column(String(255), nullable=True)
    
    # Relationship to API keys
    api_keys = relationship("ApiKey", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Owner(id={self.id}, email={self.email}, company={self.company_name})>"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
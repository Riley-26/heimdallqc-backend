from sqlalchemy import Column, Integer, String, DateTime, Boolean, Table, ForeignKey, JSON, func
from ..db.database import Base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Payment(Base):
    __tablename__ = "payments"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key
    owner_unique_id = Column(UUID(as_uuid=True), ForeignKey("owners.unique_id"), nullable=False)
    
    # Unique metadata ID
    unique_id = Column(String, nullable=False)
    
    # IDs
    customer_id = Column(String, nullable=True)
    event_id = Column(String, nullable=True)
    session_id = Column(String, nullable=True)
    subscription_id = Column(String, nullable=True)
    invoice_id = Column(String, nullable=True)
    price_id = Column(String, nullable=True)
    invoice_pdf = Column(String, nullable=True)
    
    # Details
    status = Column(String, nullable=False)
    payment_type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    currency = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    desc = Column(String, nullable=True)
    
    owner = relationship("Owner", back_populates="payments")
    
    def __repr__(self):
        return f"<Payment(id={self.id})>"
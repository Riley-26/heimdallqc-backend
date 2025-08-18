from sqlalchemy import Column, Integer, String, DateTime, Boolean, Table, ForeignKey, JSON, func
from ..db.database import Base
from sqlalchemy.orm import relationship

class Payment(Base):
    __tablename__ = "payments"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False, index=True)
    
    # IDs
    session_id = Column(String, nullable=False)
    subscription_id = Column(String, nullable=True)
    customer_id = Column(String, nullable=False)
    payment_intent = Column(String, nullable=True)
    invoice_id = Column(String, nullable=True)
    
    # Details
    status = Column(String, nullable=False)
    purchase_type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    value = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    owner = relationship("Owner", back_populates="payments")
    
    def __repr__(self):
        return f"<Payment(id={self.id})>"
from sqlalchemy import Column, DateTime, Integer, String, func
from ..db.database import Base

class Event(Base):
    __tablename__ = "events"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    customer_id = Column(String, nullable=False)
    event_id = Column(String, nullable=False, unique=True)
    event_type = Column(String, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Event(id={self.id})>"
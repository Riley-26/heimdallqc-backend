from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, Time
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..db.database import Base

frequencies = [
    "On-demand",
    "Daily",
    "Bi-daily",
    "Weekly",
    "Bi-weekly",
    "Monthly"
]

days_of_week = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
]

times = [
    "00:00","00:30",
    "01:00","01:30",
    "02:00","02:30",
    "03:00","03:30",
    "04:00","04:30",
    "05:00","05:30",
    "06:00","06:30",
    "07:00","07:30",
    "08:00","08:30",
    "09:00","09:30",
    "10:00","10:30",
    "11:00","11:30",
    "12:00","12:30",
    "13:00","13:30",
    "14:00","14:30",
    "15:00","15:30",
    "16:00","16:30",
    "17:00","17:30",
    "18:00","18:30",
    "19:00","19:30",
    "20:00","20:30",
    "21:00","21:30",
    "22:00","22:30",
    "23:00","23:30"
]

statuses = [
    "pending",
    "failed",
    "success"
]

class AuditReport(Base):
    __tablename__ = "audit_reports"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False, index=True)
    
    # Results
    score = Column(Integer, nullable=False)
    status = Column(String(50), default="pending", index=True)
    results = Column(JSON, nullable=True, default=list)
    
    # Config
    name = Column(String, nullable=False)
    pages = Column(JSON, nullable=False, default=list)
    frequency = Column(String, nullable=False)
    day = Column(String, nullable=True)
    time = Column(String, nullable=True)
    
    pdf_link = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    owner = relationship("Owner", back_populates="audit_reports")
    
    def __repr__(self):
        return f"<AuditReport(id={self.id}, name={self.name}, owner_id={self.owner_id})>"
    
    def set_status(self, status):
        if status in statuses:
            self.status = status
    
    def set_time(self, time):
        if time in times:
            self.time = time
            
    def set_day(self, day):
        if day in days_of_week:
            self.day = day
            
    def set_frequency(self, freq):
        if freq in frequencies:
            self.frequency = freq
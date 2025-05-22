from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Enum
from sqlalchemy.sql import func
import enum
from datetime import datetime
from ..db.database import Base

class ProcessingStatus(str, enum.Enum):
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED_PROCESSING = "failed_processing"
    FAILED_REQUIREMENTS = "failed_requirements"

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    api_key = Column(String, index=True, nullable=False)
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PROCESSING)
    processing_result = Column(JSON, nullable=True)
    failure_reason = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), onupdate=func.now())
    forwarded_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Submission(id={self.id}, status={self.status})>"
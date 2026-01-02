from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from .database import Base


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisRun(Base):
    """Tracks each PR analysis run."""
    
    __tablename__ = "analysis_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    repo = Column(String, index=True)  # e.g., "owner/repo"
    pr_number = Column(Integer, nullable=True)
    pr_url = Column(String, nullable=True)
    diff_text = Column(Text, nullable=True)  # For uploaded diffs
    status = Column(String, default=AnalysisStatus.PENDING)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="analysis_runs")
    result = relationship("AnalysisResult", back_populates="run", uselist=False)


class AnalysisResult(Base):
    """Stores the structured analysis results."""
    
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.id"), unique=True)
    result_json = Column(JSON)  # The full structured review output
    model_version = Column(String, nullable=True)  # e.g., "gpt-4o-mini"
    rules_version = Column(String, nullable=True)  # Version of rules used
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    run = relationship("AnalysisRun", back_populates="result")

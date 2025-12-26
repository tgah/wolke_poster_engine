"""Background generation job tracking."""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.database import Base


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"


class ImageEngine(str, enum.Enum):
    STABLE_DIFFUSION_1_5 = "stable_diffusion_1_5"
    DALL_E = "dall_e"


class BackgroundJob(Base):
    __tablename__ = "background_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    poster_id = Column(UUID(as_uuid=True), ForeignKey("posters.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    input_theme_text = Column(Text, nullable=False)
    normalized_theme_text = Column(String(1000), nullable=False, index=True)
    
    llm_prompt = Column(Text, nullable=True)
    negative_prompt = Column(Text, nullable=True)
    
    engine = Column(Enum(ImageEngine), nullable=False)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.QUEUED)
    
    error_message = Column(Text, nullable=True)
    
    # FIX: All timestamp columns need server_default
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    poster = relationship("Poster", backref="background_jobs")
    user = relationship("User")
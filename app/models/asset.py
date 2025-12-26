"""Asset storage model."""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.database import Base


class AssetType(str, enum.Enum):
    PRODUCT_IMAGE = "product_image"
    BACKGROUND_IMAGE = "background_image"
    POSTER_EXPORT = "poster_export"
    STORE_LOGO = "store_logo"


class StorageBackend(str, enum.Enum):
    LOCAL = "local"
    S3 = "s3"


class Asset(Base):
    __tablename__ = "assets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    
    type = Column(Enum(AssetType), nullable=False)
    storage_backend = Column(Enum(StorageBackend), nullable=False)
    path = Column(String(1000), nullable=False)  # Relative path or S3 key
    
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=True)  # bytes
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Relationships
    company = relationship("Company")
    created_by = relationship("User")

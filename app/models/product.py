"""Product and import models."""
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Text, Enum, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.database import Base


class Product(Base):
    __tablename__ = "products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    
    artikel_nr = Column(String(100), nullable=False, index=True)
    chinese_name = Column(String(500), nullable=True)
    german_name = Column(String(500), nullable=False)
    weight = Column(String(100), nullable=True)
    
    # Prices in EUR
    old_price = Column(Numeric(10, 2), nullable=True)
    new_price = Column(Numeric(10, 2), nullable=False)
    
    # Image
    image_path = Column(String(500), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    company = relationship("Company")
    
    __table_args__ = (
        UniqueConstraint('company_id', 'artikel_nr', name='uq_company_artikel'),
    )


class ImportStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProductImport(Base):
    __tablename__ = "product_imports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    uploaded_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    filename = Column(String(500), nullable=False)
    status = Column(Enum(ImportStatus), nullable=False, default=ImportStatus.PENDING)
    
    rows_processed = Column(Integer, default=0)
    rows_succeeded = Column(Integer, default=0)
    rows_failed = Column(Integer, default=0)
    
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    company = relationship("Company")
    uploaded_by = relationship("User")

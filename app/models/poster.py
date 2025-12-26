"""Poster and template models."""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.database import Base


class PosterStatus(str, enum.Enum):
    DRAFT = "draft"
    BACKGROUND_GENERATING = "background_generating"
    READY = "ready"
    FAILED = "failed"


class PosterTemplate(Base):
    __tablename__ = "poster_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    max_products = Column(Integer, nullable=False)
    
    # Layout configuration as JSON
    layout_json = Column(JSONB, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Poster(Base):
    __tablename__ = "posters"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("poster_templates.id"), nullable=False)
    background_image_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=True)
    
    theme_text = Column(Text, nullable=True)
    llm_prompt = Column(Text, nullable=True)
    sale_title = Column(String(500), nullable=False)
    
    status = Column(Enum(PosterStatus), nullable=False, default=PosterStatus.DRAFT)
    
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    store = relationship("Store")
    template = relationship("PosterTemplate")
    background_image = relationship("Asset", foreign_keys=[background_image_id])
    created_by = relationship("User")
    products = relationship("PosterProduct", back_populates="poster", cascade="all, delete-orphan")


class PosterProduct(Base):
    __tablename__ = "poster_products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    poster_id = Column(UUID(as_uuid=True), ForeignKey("posters.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    
    display_order = Column(Integer, nullable=False)
    
    # Allow overrides
    display_name = Column(String(500), nullable=True)
    display_weight = Column(String(100), nullable=True)
    sale_price = Column(Numeric(10, 2), nullable=False)
    old_price = Column(Numeric(10, 2), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    poster = relationship("Poster", back_populates="products")
    product = relationship("Product")
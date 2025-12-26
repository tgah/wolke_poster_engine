"""Store models."""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Store(Base):
    __tablename__ = "stores"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    company = relationship("Company", backref="stores")


class StoreSettings(Base):
    __tablename__ = "store_settings"
    
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), primary_key=True)
    logo_asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=True)
    
    # Relationships
    store = relationship("Store", backref="settings", uselist=False)
    logo = relationship("Asset", foreign_keys=[logo_asset_id])

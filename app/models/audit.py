"""Audit logging model."""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.sql import func
import uuid
from app.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    ip_address = Column(INET, nullable=True)
    
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    
    # metadata = Column(JSONB, nullable=True)
    event_data = Column(JSON, nullable=True)
    
    __table_args__ = (
        Index('idx_audit_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_audit_action_timestamp', 'action', 'timestamp'),
    )


# Migration hint (Alembic)
"""
To create initial migration:

alembic init migrations
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head

For seeding default templates:

INSERT INTO poster_templates (id, key, name, description, max_products, layout_json, created_at)
VALUES 
(
    gen_random_uuid(),
    'two_product',
    'Two Product Layout',
    'Standard layout for 2 products',
    2,
    '{
        "background": {"x": 0, "y": 0, "width": 1024, "height": 1024},
        "title": {"x": 50, "y": 50, "font_size": 48, "color": "#FFFFFF", "max_width": 924},
        "products": [
            {"x": 100, "y": 300, "width": 400, "height": 400},
            {"x": 524, "y": 300, "width": 400, "height": 400}
        ],
        "logo": {"x": 850, "y": 900, "max_width": 150, "max_height": 100}
    }',
    NOW()
),
(
    gen_random_uuid(),
    'three_product',
    'Three Product Layout',
    'Standard layout for 3 products',
    3,
    '{
        "background": {"x": 0, "y": 0, "width": 1024, "height": 1024},
        "title": {"x": 50, "y": 50, "font_size": 48, "color": "#FFFFFF", "max_width": 924},
        "products": [
            {"x": 50, "y": 200, "width": 300, "height": 300},
            {"x": 362, "y": 200, "width": 300, "height": 300},
            {"x": 674, "y": 200, "width": 300, "height": 300}
        ],
        "logo": {"x": 850, "y": 900, "max_width": 150, "max_height": 100}
    }',
    NOW()
);
"""

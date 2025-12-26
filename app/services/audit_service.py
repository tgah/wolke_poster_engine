"""Audit logging service."""
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.audit import AuditLog


class AuditService:
    """Service for audit logging."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log(
        self,
        action: str,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Create an audit log entry.
        
        Args:
            action: Action performed (e.g., "login_success", "create_poster")
            user_id: User who performed the action
            ip_address: IP address of the request
            entity_type: Type of entity affected (e.g., "poster", "product")
            entity_id: ID of the entity affected
            metadata: Additional context as JSON
        """
        log_entry = AuditLog(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            ip_address=ip_address,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata or {}
        )
        
        self.db.add(log_entry)
        self.db.commit()

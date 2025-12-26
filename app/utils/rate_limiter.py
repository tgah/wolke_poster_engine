"""Rate limiting utilities."""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from app.models.background_job import BackgroundJob, JobStatus
from app.models.audit import AuditLog
from app.config import get_settings

settings = get_settings()


class RateLimiter:
    """Rate limiting for background generation and login attempts."""
    
    @staticmethod
    def normalize_theme(theme: str) -> str:
        """Normalize theme text for comparison."""
        return " ".join(theme.lower().strip().split())
    
    @staticmethod
    def check_same_theme_cooldown(
        db: Session,
        user_id: str,
        theme_text: str
    ) -> tuple[bool, Optional[str]]:
        """
        Check if user can generate with this theme.
        Returns (is_allowed, error_message).
        """
        if not settings.RATE_LIMIT_ENABLED:
            return True, None
        
        normalized = RateLimiter.normalize_theme(theme_text)
        cooldown_threshold = datetime.utcnow() - timedelta(
            seconds=settings.SAME_THEME_COOLDOWN_SECONDS
        )
        
        # Check for recent jobs with same normalized theme
        recent_job = db.query(BackgroundJob).filter(
            and_(
                BackgroundJob.user_id == user_id,
                BackgroundJob.normalized_theme_text == normalized,
                BackgroundJob.requested_at > cooldown_threshold,
                BackgroundJob.status.in_([
                    JobStatus.QUEUED,
                    JobStatus.RUNNING,
                    JobStatus.SUCCEEDED
                ])
            )
        ).first()
        
        if recent_job:
            seconds_left = int(
                (recent_job.requested_at + timedelta(
                    seconds=settings.SAME_THEME_COOLDOWN_SECONDS
                ) - datetime.utcnow()).total_seconds()
            )
            return False, (
                f"You recently generated a background with the same theme. "
                f"Please wait {seconds_left}s or adjust the theme."
            )
        
        return True, None
    
    @staticmethod
    def check_login_rate_limit(
        db: Session,
        ip_address: str,
        email: str
    ) -> tuple[bool, Optional[str]]:
        """
        Check login rate limit by IP and email.
        Returns (is_allowed, error_message).
        """
        if not settings.RATE_LIMIT_ENABLED:
            return True, None
        
        window_start = datetime.utcnow() - timedelta(
            seconds=settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
        )
        
        # Count failed login attempts
        failed_attempts = db.query(func.count(AuditLog.id)).filter(
            and_(
                AuditLog.action == "login_failure",
                AuditLog.ip_address == ip_address,
                AuditLog.timestamp > window_start
            )
        ).scalar()
        
        if failed_attempts >= settings.LOGIN_RATE_LIMIT_ATTEMPTS:
            return False, (
                f"Too many failed login attempts. "
                f"Please try again in a few minutes."
            )
        
        return True, None
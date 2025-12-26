"""Authentication service."""
from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.user import User, UserRole
from app.schemas.auth import (
    UserRegister, UserLogin, Token, TwoFASetup, UserResponse
)
from app.utils.security import (
    hash_password, verify_password, create_access_token, TwoFactorAuth
)
from app.utils.rate_limiter import RateLimiter
from app.services.audit_service import AuditService
from app.config import get_settings

settings = get_settings()


class AuthenticationError(Exception):
    """Authentication related errors."""
    pass


class AuthService:
    """Handle user authentication and authorization."""
    
    def __init__(self, db: Session):
        self.db = db
        self.audit = AuditService(db)
    
    def register_user(
        self,
        data: UserRegister,
        company_id: UUID,
        ip_address: Optional[str] = None
    ) -> User:
        """
        Register a new user.
        In v1, this might be admin-only or restricted.
        """
        # Check if email already exists in company
        existing = self.db.query(User).filter(
            and_(
                User.company_id == company_id,
                User.email == data.email
            )
        ).first()
        
        if existing:
            raise AuthenticationError("Email already registered")
        
        # Validate password length
        if len(data.password) < settings.PASSWORD_MIN_LENGTH:
            raise AuthenticationError(
                f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters"
            )
        
        # Create user
        user = User(
            company_id=company_id,
            store_id=data.store_id,
            email=data.email,
            password_hash=hash_password(data.password),
            role=UserRole.STORE_USER,
            is_active=True
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        # Audit log
        self.audit.log(
            action="user_registered",
            user_id=user.id,
            ip_address=ip_address,
            entity_type="user",
            entity_id=user.id,
            metadata={"email": user.email}
        )
        
        return user
    
    def authenticate_user(
        self,
        data: UserLogin,
        company_id: UUID,
        ip_address: Optional[str] = None
    ) -> Tuple[User, Token]:
        """
        Authenticate user and return token.
        Handles 2FA if enabled.
        """
        # Check rate limit
        allowed, error = RateLimiter.check_login_rate_limit(
            self.db, ip_address or "unknown", data.email
        )
        
        if not allowed:
            self.audit.log(
                action="login_rate_limited",
                ip_address=ip_address,
                metadata={"email": data.email, "reason": error}
            )
            raise AuthenticationError(error)
        
        # Find user
        user = self.db.query(User).filter(
            and_(
                User.company_id == company_id,
                User.email == data.email
            )
        ).first()
        
        if not user or not verify_password(data.password, user.password_hash):
            self.audit.log(
                action="login_failure",
                user_id=user.id if user else None,
                ip_address=ip_address,
                metadata={"email": data.email, "reason": "invalid_credentials"}
            )
            raise AuthenticationError("Invalid email or password")
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            raise AuthenticationError("Account temporarily locked")
        
        if not user.is_active:
            raise AuthenticationError("Account is disabled")
        
        # Check 2FA if enabled
        if user.twofa_enabled and settings.TWOFA_ENABLED:
            if not data.totp_code:
                raise AuthenticationError("2FA code required")
            
            if not TwoFactorAuth.verify_totp(user.twofa_secret, data.totp_code):
                self.audit.log(
                    action="login_failure",
                    user_id=user.id,
                    ip_address=ip_address,
                    metadata={"email": data.email, "reason": "invalid_2fa"}
                )
                raise AuthenticationError("Invalid 2FA code")
        
        # Update last login
        user.last_login_at = datetime.utcnow()
        user.failed_login_attempts = 0
        user.locked_until = None
        self.db.commit()
        
        # Create token
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "company_id": str(user.company_id)
        }
        access_token = create_access_token(token_data)
        
        # Audit log
        self.audit.log(
            action="login_success",
            user_id=user.id,
            ip_address=ip_address,
            metadata={"email": user.email}
        )
        
        return user, Token(access_token=access_token, token_type="bearer")
    
    def setup_2fa(self, user_id: UUID) -> TwoFASetup:
        """
        Generate 2FA secret and QR code for user.
        Does not enable 2FA until verified.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AuthenticationError("User not found")
        
        if user.twofa_enabled:
            raise AuthenticationError("2FA already enabled")
        
        # Generate secret
        secret = TwoFactorAuth.generate_secret()
        uri = TwoFactorAuth.get_totp_uri(user.email, secret)
        qr_code = TwoFactorAuth.generate_qr_code(uri)
        
        # Store secret (not enabled yet)
        user.twofa_secret = secret
        self.db.commit()
        
        return TwoFASetup(secret=secret, qr_code_data_url=qr_code)
    
    def enable_2fa(self, user_id: UUID, totp_code: str) -> bool:
        """
        Enable 2FA after verifying initial code.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AuthenticationError("User not found")
        
        if not user.twofa_secret:
            raise AuthenticationError("2FA not set up. Call setup first.")
        
        # Verify code
        if not TwoFactorAuth.verify_totp(user.twofa_secret, totp_code):
            raise AuthenticationError("Invalid code")
        
        # Enable 2FA
        user.twofa_enabled = True
        self.db.commit()
        
        self.audit.log(
            action="2fa_enabled",
            user_id=user.id,
            entity_type="user",
            entity_id=user.id
        )
        
        return True
    
    def disable_2fa(self, user_id: UUID, password: str) -> bool:
        """
        Disable 2FA (requires password confirmation).
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AuthenticationError("User not found")
        
        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid password")
        
        user.twofa_enabled = False
        user.twofa_secret = None
        self.db.commit()
        
        self.audit.log(
            action="2fa_disabled",
            user_id=user.id,
            entity_type="user",
            entity_id=user.id
        )
        
        return True
    
    def get_current_user(self, user_id: UUID) -> User:
        """Get user by ID."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AuthenticationError("User not found")
        return user
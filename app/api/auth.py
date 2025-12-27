"""Authentication API endpoints with Redis cleanup on logout."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import UserRegister, UserLogin, Token, TwoFASetup, TwoFAVerify, UserResponse
from app.services.auth_service import AuthService, AuthenticationError
from app.dependencies import get_current_user, get_session_id
from app.utils.session_manager import SessionManager
from uuid import UUID

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse)
async def register(
    data: UserRegister,
    db: Session = Depends(get_db),
):
    """Register a new user."""
    service = AuthService(db)
    
    from app.models.company import Company
    company = db.query(Company).first()
    if not company:
        raise HTTPException(400, "No company found. Please run seed script.")
    
    try:
        user = service.register_user(data, company.id)
        return user
    except AuthenticationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=Token)
async def login(
    data: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """Authenticate user and return JWT token."""
    service = AuthService(db)
    
    from app.models.company import Company
    company = db.query(Company).first()
    
    try:
        user, token = service.authenticate_user(
            data,
            company.id,
            ip_address=request.client.host
        )
        return token
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
async def logout(
    current_user = Depends(get_current_user),
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db)
):
    """
    Logout user and cleanup session data.
    Deletes products from Redis immediately.
    """
    # Delete session products from Redis
    session_mgr = SessionManager()
    session_mgr.delete_products(session_id)
    
    # Audit log
    from app.services.audit_service import AuditService
    audit = AuditService(db)
    audit.log(
        action="logout",
        user_id=current_user.id,
        metadata={"session_id": session_id}
    )
    
    print(f"✅ User {current_user.id} logged out, session {session_id} cleaned up")
    
    return {
        "message": "Logged out successfully",
        "session_cleaned": True
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user = Depends(get_current_user)
):
    """Get current user information."""
    return current_user


@router.post("/2fa/setup", response_model=TwoFASetup)
async def setup_2fa(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set up 2FA for current user."""
    service = AuthService(db)
    try:
        return service.setup_2fa(current_user.id)
    except AuthenticationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/2fa/enable")
async def enable_2fa(
    data: TwoFAVerify,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enable 2FA after verifying code."""
    service = AuthService(db)
    try:
        service.enable_2fa(current_user.id, data.totp_code)
        return {"message": "2FA enabled successfully"}
    except AuthenticationError as e:
        raise HTTPException(status_code=400, detail=str(e))
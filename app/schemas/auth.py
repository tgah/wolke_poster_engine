"""Authentication schemas."""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    store_id: Optional[UUID] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = Field(None, min_length=6, max_length=6)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TwoFASetup(BaseModel):
    secret: str
    qr_code_data_url: str
    

class TwoFAVerify(BaseModel):
    totp_code: str = Field(min_length=6, max_length=6)


class UserResponse(BaseModel):
    id: UUID
    email: str
    role: str
    company_id: UUID
    store_id: Optional[UUID]
    twofa_enabled: bool
    created_at: datetime
    last_login_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

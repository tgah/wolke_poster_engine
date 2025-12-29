"""
Configuration management using Pydantic Settings.
Follows 12-factor app principles.
"""
from pydantic_settings import BaseSettings
from typing import Optional, Literal
from functools import lru_cache


class Settings(BaseSettings):
    """Application configuration."""
    
    # Application
    APP_NAME: str = "Poster Generator API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str
    DB_ECHO: bool = False
    
    # Security
    SECRET_KEY: str  # For JWT/session signing
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Session cookies (if using cookie-based auth)
    SESSION_COOKIE_NAME: str = "poster_session"
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SECURE: bool = True  # Set False for local dev
    SESSION_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    
    # Password hashing
    PASSWORD_MIN_LENGTH: int = 8
    
    # 2FA
    TWOFA_ENABLED: bool = True  # Global toggle
    TWOFA_ISSUER_NAME: str = "Poster Generator"
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    SAME_THEME_COOLDOWN_SECONDS: int = 60
    LOGIN_RATE_LIMIT_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 300  # 5 minutes
    
    # Storage
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    STORAGE_BASE_PATH: str = "./storage"  # For local storage
    STORAGE_BASE_URL: str = "/assets"  # URL prefix for serving
    
    # S3 Configuration (if using S3)
    S3_BUCKET: Optional[str] = None
    S3_REGION: str = "eu-central-1"  # EU region
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    
    # Asset limits
    MAX_UPLOAD_SIZE_MB: int = 10
    MIN_BACKGROUND_WIDTH: int = 1024
    MIN_BACKGROUND_HEIGHT: int = 1024
    ALLOWED_IMAGE_TYPES: list[str] = ["image/png", "image/jpeg"]
    
    # AI - LLM Provider
    LLM_PROVIDER: Literal["openai", "anthropic"] = "openai"
    LLM_API_KEY: str
    LLM_MODEL: str = "gpt-4"
    LLM_BASE_URL: Optional[str] = None
    LLM_TIMEOUT_SECONDS: int = 30
    
    # AI - Image Generation
    IMAGE_GEN_PROVIDER: Literal["stable_diffusion", "dalle"] = "stable_diffusion"
    
    # Stable Diffusion
    SD_MODEL_PATH: str = "runwayml/stable-diffusion-v1-5"
    SD_DEVICE: str = "mps"  # or "cpu"
    SD_NUM_INFERENCE_STEPS: int = 50
    SD_GUIDANCE_SCALE: float = 7.5
    SD_IMAGE_WIDTH: int = 1024
    SD_IMAGE_HEIGHT: int = 1024
    
    # DALL-E (if used)
    DALLE_API_KEY: Optional[str] = None
    DALLE_MODEL: str = "dall-e-3"
    DALLE_SIZE: str = "1024x1024"
    DALLE_QUALITY: str = "standard"
    
    # Background Jobs
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Poster Export
    EXPORT_DEFAULT_DPI: int = 300
    EXPORT_FONT_PATH: str = "./fonts/Arial.ttf"
    EXPORT_FONT_BOLD_PATH: str = "./fonts/Arial-Bold.ttf"
    
    # Validation
    VALIDATE_SALE_PRICE_LTE_OLD_PRICE: bool = True
    
    # CSV Import
    CSV_MAX_ROWS: int = 10000
    CSV_REQUIRED_COLUMNS: list[str] = [
        "artikelNr", "chineseName", "germanName", 
        "weight", "oldPrice", "newPrice"
    ]
    
    # Audit
    AUDIT_LOG_SENSITIVE_DATA: bool = False  # Don't log passwords, etc.
    
    # CORS (if needed)
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000"]
    CORS_CREDENTIALS: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()

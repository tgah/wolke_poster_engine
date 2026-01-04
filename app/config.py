"""
Configuration management using Pydantic Settings.
Follows 12-factor app principles.
"""
from pydantic_settings import BaseSettings
from pydantic import validator, field_validator
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
    MIN_BACKGROUND_WIDTH: int = 3508  # A3 portrait width at 300 DPI
    MIN_BACKGROUND_HEIGHT: int = 4961  # A3 portrait height at 300 DPI
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
    SD_IMAGE_WIDTH: int = 3508  # A3 portrait width at 300 DPI
    SD_IMAGE_HEIGHT: int = 4961  # A3 portrait height at 300 DPI
    
    # DALL-E (if used)
    DALLE_API_KEY: Optional[str] = None
    DALLE_MODEL: str = "dall-e-3"
    DALLE_SIZE: str = "1024x1792"  # Portrait, will be upscaled to A3
    DALLE_QUALITY: str = "standard"

    # DALL-E System Prompts (randomly selected for variety)
    DALLE_SYSTEM_PROMPTS: list[str] = [
        # System Prompt 1: Modern graphic illustration
        """You are an expert graphic designer and illustrator creating background-only artwork for A3 portrait promotional sale posters for a convenience store.
Core Purpose: Your task is to generate a visually engaging illustrated poster background that supports later placement of product images, pricing information, discount details, and promotional text. The background must enhance these elements without competing with them.
Layout & Composition Rules (MANDATORY): Canvas: A3 size, portrait orientation. Negative space is essential. Keep large, clean, uncluttered areas specifically intended for product images and text overlays. Reserve at least one central or lower-central open area and one side or upper open area. These empty areas must be visually calm, low contrast, and free of focal elements.
Strict Exclusions (CRITICAL): The image must NOT contain any text, letters, numbers, symbols, or typography; logos, brand marks, mascots, or signage; price tags, labels, stickers, badges, banners, or tag-like shapes; UI elements, frames, borders, or callout bubbles. The image must be purely illustrative and abstract/environmental.
Visual Style: Illustrative graphic art, not photorealistic. Influenced by pop-art and modern graphic illustration. Smooth color transitions, soft gradients, or flat color blocks. Clear visual hierarchy with background depth, but no clutter.
Detail Placement Guidance: Concentrate visual detail around edges, in corners, along borders or diagonals. Gradually reduce detail toward reserved empty areas. Use lighting, color contrast, or texture to naturally guide the eye away from empty zones.
User-provided keywords define season, mood, color palette, and atmosphere. Colors should be: Cohesive, print-friendly and should not overly saturated in empty zones.
The output Goal is to produce a print-ready illustrated background that: feels premium and modern, works as a neutral yet expressive base for commercial overlays and can be reused across multiple promotions without visual conflict. You are not to explain your choices.""",

        # System Prompt 2: Minimal illustrative
        """You are a professional graphic designer creating background-only artwork for A3 portrait promotional posters.
Primary Objective: Generate a minimal, illustrative poster background that serves as a neutral yet visually appealing base for adding product images, prices, discount text, and promotional information. The background must remain clean, uncluttered, and secondary to future overlays.
Canvas & Layout (MANDATORY): Format: A3 size, portrait orientation. The bottom half must contain large, clearly readable empty space with low visual noise and flat or softly graded color only. The upper half may contain simple illustrative or abstract graphic elements with controlled visual interest.
Visual Style: Illustrative, not photorealistic. Minimal graphic abstraction with bold flat illustration, clean shapes, solid fills, limited texture, and strong but restrained color palette with a modern and poster-ready composition.
Strict Prohibitions (CRITICAL): The generated image must NOT include text, letters, numbers, or typography; logos, brand symbols, mascots, or signage; price tags, labels, stickers, badges, or any tag-like shapes; icons, banners, ribbons, or callout shapes; UI elements, borders, frames, or placeholders. All shapes must remain abstract or environmental.
Composition Rules: Visual elements should be concentrated toward the top and upper sides, fading in complexity toward the bottom half. Empty areas must be intentional, clearly usable for text and product overlays, and free of strong contrast or patterns.
User-provided keywords determine mood, season, color palette, and atmosphere. You should maintain a high print clarity, with calm, readable background tone in empty areas. 
Output Instructions: Produce a single, print ready illustrated background that must feel designed, fun and friendly""",

        # System Prompt 3: Playful childish art style
        """You are a professional illustrator creating background-only artwork for A3 portrait promotional posters.
Core Goal: Create an illustrative, abstract advertising background with a playful, childish art style, intended to support later placement of product images, pricing and discount text, and promotional messaging. The background must remain clean, flexible, and secondary to these elements.
Canvas & Layout (MANDATORY): Format: A3 size, portrait orientation. The bottom half must be visually open and uncluttered, calm, low-contrast, and suitable for text and product overlays. The upper half may contain playful abstract forms, expressive illustration, and advertising-style visual energy.
Visual Style: Illustrative, not photorealistic. Abstract advertising art with childish/playful aesthetic featuring simple shapes, rounded forms, friendly proportions, hand-drawn or naïve illustration feel, flat or lightly textured color fills, and bold but controlled color usage.
Strict Prohibitions (CRITICAL): The image must NOT include any text, letters, numbers, or typographic shapes; logos, brand marks, mascots, or signage; price tags, labels, stickers, badges, or tag-like forms; sale symbols, banners, ribbons, or callouts; UI elements, borders, frames, or placeholders. All visual elements must remain non-literal, non-commercial, and abstract.
Composition Rules: Visual interest should be concentrated in the top half and gradually simplify toward the bottom half. Empty areas must be intentional, clearly usable, and avoid sharp contrast or busy patterns You should derive the mood, season and palette exlusively from user-provided keywords.
User-provided keywords define mood, season, and color palette. You should maintain a high contrast and playful color in decorative areas with softer, quiter tones in empty zones for readability. 
Output Instructions: Generate one print-ready illustrated background, prioritizing clarity, friendliness and adaptability"""
    ]

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
    CORS_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000", "http://127.0.0.1:8000"]
    CORS_CREDENTIALS: bool = True

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()

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
        """You are creating a background-only illustration for a grocery store promotional poster.
            Format
            A3 size
            Portrait orientation
            Full-bleed image
            Creative Direction
            Use the user-provided keywords as an initial direction for:
            Theme
            Mood
            Color palette
            Go beyond the keywords using your own artistic inspiration.
            Aim for originality and variation; each image should feel visually distinct and creatively fresh.
            Composition
            All decorative and expressive design elements must appear only in the top portion of the image, occupying no more than the top 60% of the canvas.
            The placement of these elements within the top area should feel natural and varied, not centered or repetitive.
            The bottom 40% of the image must remain intentionally empty:
            Calm
            Low contrast
            Minimal texture
            Clearly suitable for product images and text to be added later
            Style
            Illustrative or design-led (not photorealistic)
            Abstract or decorative
            Any art style is allowed if it supports the keywords and composition
            Encourage experimentation with shapes, colors, textures, and illustration techniques
            Strict Rules
            Do not include any text, letters, numbers, or symbols that resemble text
            Do not include logos, brands, signage, or sale-related visuals
            Do not include frames, borders, UI elements, or placeholders
            Do not depict literal products
            Output
            Generate one high-quality, print-ready background image
            Do not explain or describe the image""",

        # System Prompt 3: Playful childish art style
        """Role
            You are an expert commercial illustrator and art director generating background-only artwork for A3 portrait grocery store posters. 
            The artwork will be used as a supporting layer beneath product images and pricing added later by another system.
            PRIMARY OBJECTIVE
            Create a high-quality, print-ready illustrated background that is:
            Visually engaging and original
            Compositionally optimized for later overlays
            Highly creative and varied in style
            Strictly free of text, logos, or symbolic sales elements
            Each generation should feel distinct, not a variation of a previous image.
            CANVAS & FORMAT (STRICT)
            Size: A3
            Orientation: Portrait
            Single full-bleed image
            No borders, frames, or margins
            COMPOSITION & LAYOUT (CRITICAL)
            The poster must be visually top-heavy by design.
            Top 50–60% of the canvas
            Primary visual interest lives here
            Decorative illustration, abstract forms, or thematic elements
            Dynamic composition, expressive shapes, or creative motifs
            May be dense, energetic, playful, elegant, or expressive depending on keywords
            Bottom 40–50% of the canvas
            Intentionally calm and open
            Low visual noise
            Soft gradients, subtle textures, or gentle color transitions only
            No focal points, no dense shapes, no contrast spikes
            Must clearly read as a “safe zone” for product photos and text overlays
            Visual complexity must decrease gradually from top to bottom.
            VISUAL STYLE (FLEXIBLE & CREATIVE)
            Illustrative or design-led, not photorealistic
            Style may vary freely between:
            Abstract
            Playful
            Minimalist
            Festive
            Elegant
            Bold graphic
            Painterly
            Flat design
            Textured illustration
            Art style should be strongly influenced by user keywords
            Avoid repeating the same composition, motifs, or illustration style across generations
            Encourage novelty and experimentation in:
            Shape language
            Illustration techniques
            Color relationships
            Visual rhythm
            COLOR & MOOD
            Derive palette, emotion, and seasonal cues exclusively from user-provided keywords
            Top section may use:
            Strong contrast
            Saturated or expressive colors
            Bottom section must use:
            Softer tones
            Reduced contrast
            Harmonious color blending for readability
            ABSOLUTE PROHIBITIONS (NON-NEGOTIABLE)
            The image must NOT contain:
            Any text, letters, numbers, or typographic shapes
            Logos, brand marks, mascots, or recognizable symbols
            Sale-related visuals (price tags, stickers, banners, ribbons, badges)
            UI elements, icons, placeholders, or mockups
            Real-world signage or commercial objects
            Literal product depictions
            All visuals must remain abstract, illustrative, or decorative only.
            VARIATION REQUIREMENT (IMPORTANT)
            Each image must:
            Explore a different visual idea or composition
            Avoid default poster tropes
            Avoid repeating layouts, motifs, or art styles
            Feel like it was created by a human illustrator experimenting creatively
            OUTPUT RULES
            Generate one high-quality, print-ready background image
            Do not include explanations or commentary
            Do not include text or symbolic elements
            Prioritize originality, clarity, and adaptability
            """
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

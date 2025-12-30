"""FastAPI application entry point."""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import logging
from pathlib import Path

from app.config import get_settings
from app.api import auth, products, posters, assets, backgrounds
from app.database import engine, Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    # allow_origins=["*"],  # TEMPORARY: Allow all origins for testing
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(backgrounds.router)  # NEW: Background management
app.include_router(products.router)
app.include_router(posters.router)
app.include_router(assets.router)

# Mount static files for assets
if settings.STORAGE_BACKEND == "local":
    storage_path = Path(settings.STORAGE_BASE_PATH)
    storage_path.mkdir(parents=True, exist_ok=True)
    app.mount(
        settings.STORAGE_BASE_URL,
        StaticFiles(directory=str(storage_path)),
        name="assets"
    )


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    logger.info(f"Redis URL: {settings.CELERY_BROKER_URL}")
    logger.info(f"Image Generator: {settings.IMAGE_GEN_PROVIDER}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down application")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error_code": "INTERNAL_ERROR"
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "image_provider": settings.IMAGE_GEN_PROVIDER
    }
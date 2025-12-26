"""Background task definitions."""
import asyncio
from datetime import datetime
from uuid import UUID

from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.models.poster import Poster, PosterStatus
from app.models.background_job import BackgroundJob, JobStatus, ImageEngine
from app.models.asset import Asset, AssetType, StorageBackend
from app.ai.prompt_builder import LLMPromptBuilder
from app.ai.image_generator import get_image_generator
from app.services.audit_service import AuditService
from app.services.asset_service import AssetService
from app.utils.rate_limiter import RateLimiter
from app.config import get_settings

settings = get_settings()


@celery_app.task(name="generate_background", bind=True)
def generate_background_task(self, poster_id: str, user_id: str, theme_text: str):
    """
    Generate background image for poster.
    This runs as a Celery task.
    """
    print(f"Starting background generation for poster {poster_id}")
    print(f"Theme: {theme_text}")
    
    db = SessionLocal()
    
    try:
        # Create job record
        normalized_theme = RateLimiter.normalize_theme(theme_text)
        
        job = BackgroundJob(
            poster_id=UUID(poster_id),
            user_id=UUID(user_id),
            input_theme_text=theme_text,
            normalized_theme_text=normalized_theme,
            engine=ImageEngine.STABLE_DIFFUSION_1_5,
            status=JobStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        db.add(job)
        db.commit()
        
        print(f"Created background job {job.id}")
        
        # Get poster
        poster = db.query(Poster).filter(Poster.id == UUID(poster_id)).first()
        if not poster:
            raise ValueError("Poster not found")
        
        print("Step 1: Generating prompt with LLM...")
        
        # Generate prompt using LLM
        prompt_builder = LLMPromptBuilder()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        prompt_result = loop.run_until_complete(
            prompt_builder.generate_prompt(theme_text)
        )
        
        job.llm_prompt = prompt_result["positive_prompt"]
        job.negative_prompt = prompt_result.get("negative_prompt", "")
        poster.llm_prompt = prompt_result["positive_prompt"]
        db.commit()
        
        print(f"Generated prompt: {prompt_result['positive_prompt'][:100]}...")
        print(f"Step 2: Generating image with {settings.IMAGE_GEN_PROVIDER}...")
        
        # Generate image
        generator = get_image_generator()
        image_bytes = loop.run_until_complete(
            generator.generate(
                prompt_result["positive_prompt"],
                prompt_result.get("negative_prompt"),
                width=settings.SD_IMAGE_WIDTH,
                height=settings.SD_IMAGE_HEIGHT
            )
        )
        
        loop.close()
        
        print(f"Image generated! Size: {len(image_bytes)} bytes")
        print("Step 3: Saving image as asset...")
        
        # Save as asset
        asset_service = AssetService(db)
        asset = asset_service.save_asset(
            image_bytes,
            AssetType.BACKGROUND_IMAGE,
            poster.store.company_id,
            user_id=UUID(user_id),
            width=settings.SD_IMAGE_WIDTH,
            height=settings.SD_IMAGE_HEIGHT,
            mime_type="image/png"
        )
        
        print(f"Asset saved with ID: {asset.id}")
        
        # Update poster
        poster.background_image_id = asset.id
        poster.status = PosterStatus.READY
        
        # Update job
        job.status = JobStatus.SUCCEEDED
        job.completed_at = datetime.utcnow()
        
        db.commit()
        
        print(f"✅ Background generation completed successfully for poster {poster_id}")
        
        # Audit
        audit = AuditService(db)
        audit.log(
            action="background_generated",
            user_id=UUID(user_id),
            entity_type="poster",
            entity_id=UUID(poster_id),
            metadata={
                "job_id": str(job.id),
                "engine": job.engine.value
            }
        )
        
        return {
            "status": "success",
            "poster_id": poster_id,
            "asset_id": str(asset.id)
        }
    
    except Exception as e:
        print(f"❌ Error generating background: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Handle failure
        if 'job' in locals():
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
        
        if 'poster' in locals():
            poster.status = PosterStatus.FAILED
        
        db.commit()
        
        # Re-raise to let Celery handle retry
        raise
    
    finally:
        db.close()
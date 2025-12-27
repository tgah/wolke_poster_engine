"""Background task definitions with split background generation."""
import asyncio
import hashlib
from datetime import datetime as dt
from pathlib import Path
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

@celery_app.task(name="generate_background_only", bind=True)
def generate_background_only_task(
    self,
    asset_id: str,
    user_id: str,
    theme_text: str,
    job_id: str
):
    """
    Generate background image only (no poster creation).
    Updates the asset when complete.
    """
    print(f"Starting background-only generation for asset {asset_id}")
    print(f"Theme: {theme_text}")
    
    db = SessionLocal()
    
    try:
        # Get job and asset
        job = db.query(BackgroundJob).filter(BackgroundJob.id == UUID(job_id)).first()
        asset = db.query(Asset).filter(Asset.id == UUID(asset_id)).first()
        
        if not job or not asset:
            raise ValueError("Job or asset not found")
        
        job.status = JobStatus.RUNNING
        job.started_at = dt.now()
        db.commit()
        
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
        print("Step 3: Saving image...")
        
        # # Update asset with actual image
        # asset_service = AssetService(db)
        # # Delete placeholder asset
        # db.delete(asset)
        # db.flush()

        # Generate filename
        timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
        file_hash = hashlib.md5(image_bytes).hexdigest()[:8]
        filename = f"background_image_{timestamp}_{file_hash}.png"

        # Determine storage path
        storage_path = Path(settings.STORAGE_BASE_PATH) / "background_image"
        storage_path.mkdir(parents=True, exist_ok=True)
        file_path = storage_path / filename

        # Save file
        with open(file_path, "wb") as f:
            f.write(image_bytes)
        
        # # Create real asset
        # asset = asset_service.save_asset(
        #     image_bytes,
        #     AssetType.BACKGROUND_IMAGE,
        #     asset.company_id,
        #     user_id=UUID(user_id),
        #     width=settings.SD_IMAGE_WIDTH,
        #     height=settings.SD_IMAGE_HEIGHT,
        #     mime_type="image/png"
        # )
        
        # Update asset record (don't create new one)
        asset.path = f"background_image/{filename}"
        asset.width = settings.SD_IMAGE_WIDTH
        asset.height = settings.SD_IMAGE_HEIGHT
        asset.file_size = len(image_bytes)
        asset.storage_backend = StorageBackend.LOCAL

        db.flush()

        # Update job
        job.status = JobStatus.SUCCEEDED
        job.completed_at = dt.now()
        
        db.commit()
        
        print(f"✅ Background generation completed successfully for asset {asset.id}")
        
        # Audit
        audit = AuditService(db)
        audit.log(
            action="background_generated",
            user_id=UUID(user_id),
            entity_type="asset",
            entity_id=asset.id,
            metadata={
                "job_id": str(job.id),
                "engine": job.engine.value,
                "theme": theme_text
            }
        )
        
        return {
            "status": "success",
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
            job.completed_at = dt.now()
        
        db.commit()
        
        raise
    
    finally:
        db.close()

# @celery_app.task(name="generate_background", bind=True)
# def generate_background_task(self, poster_id: str, user_id: str, theme_text: str):
#     """
#     Generate background image for poster.
#     This runs as a Celery task.
#     """
#     print(f"Starting background generation for poster {poster_id}")
#     print(f"Theme: {theme_text}")
    
#     db = SessionLocal()
    
#     try:
#         # Create job record
#         normalized_theme = RateLimiter.normalize_theme(theme_text)
        
#         job = BackgroundJob(
#             poster_id=UUID(poster_id),
#             user_id=UUID(user_id),
#             input_theme_text=theme_text,
#             normalized_theme_text=normalized_theme,
#             engine=ImageEngine.STABLE_DIFFUSION_1_5,
#             status=JobStatus.RUNNING,
#             started_at=datetime.utcnow()
#         )
#         db.add(job)
#         db.commit()
        
#         print(f"Created background job {job.id}")
        
#         # Get poster
#         poster = db.query(Poster).filter(Poster.id == UUID(poster_id)).first()
#         if not poster:
#             raise ValueError("Poster not found")
        
#         print("Step 1: Generating prompt with LLM...")
        
#         # Generate prompt using LLM
#         prompt_builder = LLMPromptBuilder()
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)
        
#         prompt_result = loop.run_until_complete(
#             prompt_builder.generate_prompt(theme_text)
#         )
        
#         job.llm_prompt = prompt_result["positive_prompt"]
#         job.negative_prompt = prompt_result.get("negative_prompt", "")
#         poster.llm_prompt = prompt_result["positive_prompt"]
#         db.commit()
        
#         print(f"Generated prompt: {prompt_result['positive_prompt'][:100]}...")
#         print(f"Step 2: Generating image with {settings.IMAGE_GEN_PROVIDER}...")
        
#         # Generate image
#         generator = get_image_generator()
#         image_bytes = loop.run_until_complete(
#             generator.generate(
#                 prompt_result["positive_prompt"],
#                 prompt_result.get("negative_prompt"),
#                 width=settings.SD_IMAGE_WIDTH,
#                 height=settings.SD_IMAGE_HEIGHT
#             )
#         )
        
#         loop.close()
        
#         print(f"Image generated! Size: {len(image_bytes)} bytes")
#         print("Step 3: Saving image as asset...")
        
#         # Save as asset
#         asset_service = AssetService(db)
#         asset = asset_service.save_asset(
#             image_bytes,
#             AssetType.BACKGROUND_IMAGE,
#             poster.store.company_id,
#             user_id=UUID(user_id),
#             width=settings.SD_IMAGE_WIDTH,
#             height=settings.SD_IMAGE_HEIGHT,
#             mime_type="image/png"
#         )
        
#         print(f"Asset saved with ID: {asset.id}")
        
#         # Update poster
#         poster.background_image_id = asset.id
#         poster.status = PosterStatus.READY
        
#         # Update job
#         job.status = JobStatus.SUCCEEDED
#         job.completed_at = datetime.utcnow()
        
#         db.commit()
        
#         print(f"✅ Background generation completed successfully for poster {poster_id}")
        
#         # Audit
#         audit = AuditService(db)
#         audit.log(
#             action="background_generated",
#             user_id=UUID(user_id),
#             entity_type="poster",
#             entity_id=UUID(poster_id),
#             metadata={
#                 "job_id": str(job.id),
#                 "engine": job.engine.value
#             }
#         )
        
#         return {
#             "status": "success",
#             "poster_id": poster_id,
#             "asset_id": str(asset.id)
#         }
    
#     except Exception as e:
#         print(f"❌ Error generating background: {str(e)}")
#         import traceback
#         traceback.print_exc()
        
#         # Handle failure
#         if 'job' in locals():
#             job.status = JobStatus.FAILED
#             job.error_message = str(e)
#             job.completed_at = datetime.utcnow()
        
#         if 'poster' in locals():
#             poster.status = PosterStatus.FAILED
        
#         db.commit()
        
#         # Re-raise to let Celery handle retry
#         raise
    
#     finally:
#         db.close()


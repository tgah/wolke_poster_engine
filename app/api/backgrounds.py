"""Background generation and management API."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.database import get_db
from app.dependencies import get_current_user
from app.models.asset import Asset, AssetType
from app.services.asset_service import AssetService
from app.workers.tasks import generate_background_only_task

router = APIRouter(prefix="/backgrounds", tags=["backgrounds"])


class BackgroundGenerateRequest(BaseModel):
    theme_text: str = Field(min_length=5, max_length=2000)


class BackgroundResponse(BaseModel):
    id: UUID
    status: str  # "generating", "ready", "failed"
    url: Optional[str] = None
    theme_text: Optional[str] = None
    created_at: str
    
    class Config:
        from_attributes = True


@router.post("/generate", response_model=BackgroundResponse, status_code=202)
async def generate_background(
    data: BackgroundGenerateRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate AI background image.
    Returns immediately with status 'generating'.
    Poll GET /backgrounds/{id} to check completion.
    """
    from app.models.background_job import BackgroundJob, JobStatus, ImageEngine
    from app.utils.rate_limiter import RateLimiter
    
    # Check rate limit
    allowed, error = RateLimiter.check_same_theme_cooldown(
        db,
        str(current_user.id),
        data.theme_text
    )
    
    if not allowed:
        raise HTTPException(429, error)
    
    # Create placeholder asset
    asset = Asset(
        company_id=current_user.company_id,
        type=AssetType.BACKGROUND_IMAGE,
        storage_backend="local",  # Will be updated when generated
        path="",  # Will be updated
        mime_type="image/png",
        created_by_user_id=current_user.id
    )
    db.add(asset)
    db.flush()
    
    # Create background job
    normalized_theme = RateLimiter.normalize_theme(data.theme_text)
    job = BackgroundJob(
        poster_id=None,  # No poster yet
        user_id=current_user.id,
        input_theme_text=data.theme_text,
        normalized_theme_text=normalized_theme,
        engine=ImageEngine.STABLE_DIFFUSION_1_5,
        status=JobStatus.QUEUED
    )
    db.add(job)
    db.commit()
    db.refresh(asset)
    db.refresh(job)
    
    # Queue Celery task
    generate_background_only_task.delay(
        str(asset.id),
        str(current_user.id),
        data.theme_text,
        str(job.id)
    )

    # Queue Celery task -------------------------------------------------------
    print(f"🚀 Queueing background generation task...")
    print(f"   Asset ID: {asset.id}")
    print(f"   User ID: {current_user.id}")
    print(f"   Job ID: {job.id}")

    try:
        task_result = generate_background_only_task.delay(
            str(asset.id),
            str(current_user.id),
            data.theme_text,
            str(job.id)
        )
        print(f"✅ Task queued with ID: {task_result.id}")
    except Exception as e:
        print(f"❌ Failed to queue task: {e}")
        import traceback
        traceback.print_exc()
    # Queue Celery task end -------------------------------------------------------
    
    return {
        "id": asset.id,
        "status": "generating",
        "url": None,
        "theme_text": data.theme_text,
        "created_at": asset.created_at.isoformat()
    }


@router.post("/upload", response_model=BackgroundResponse)
async def upload_background(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload custom background image.
    Saves to user's background library.
    """
    from PIL import Image
    import io
    from app.utils.validators import ImageValidator
    
    # Read file
    content = await file.read()
    
    # Validate type
    valid, error = ImageValidator.validate_image_type(file.content_type)
    if not valid:
        raise HTTPException(400, error)
    
    # Validate size
    try:
        img = Image.open(io.BytesIO(content))
        width, height = img.size
    except Exception as e:
        raise HTTPException(400, f"Invalid image file: {str(e)}")
    
    valid, error = ImageValidator.validate_image_size(width, height)
    if not valid:
        raise HTTPException(400, error)
    
    # Save asset
    asset_service = AssetService(db)
    asset = asset_service.save_asset(
        content,
        AssetType.BACKGROUND_IMAGE,
        current_user.company_id,
        user_id=current_user.id,
        width=width,
        height=height,
        mime_type=file.content_type
    )
    
    url = asset_service.get_asset_url(asset)
    
    return {
        "id": asset.id,
        "status": "ready",
        "url": url,
        "theme_text": f"Uploaded: {file.filename}",
        "created_at": asset.created_at.isoformat()
    }


@router.get("", response_model=List[BackgroundResponse])
async def list_backgrounds(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all backgrounds belonging to current user.
    """
    asset_service = AssetService(db)
    
    backgrounds = db.query(Asset).filter(
        Asset.created_by_user_id == current_user.id,
        Asset.type == AssetType.BACKGROUND_IMAGE
    ).order_by(Asset.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for bg in backgrounds:
        # Check if still generating
        from app.models.background_job import BackgroundJob
        job = db.query(BackgroundJob).filter(
            BackgroundJob.user_id == current_user.id
        ).order_by(BackgroundJob.requested_at.desc()).first()
        
        status = "ready" if bg.path else "generating"
        url = asset_service.get_asset_url(bg) if bg.path else None
        
        result.append({
            "id": bg.id,
            "status": status,
            "url": url,
            "theme_text": None,  # Could store this in metadata
            "created_at": bg.created_at.isoformat()
        })
    
    return result


@router.get("/{background_id}", response_model=BackgroundResponse)
async def get_background(
    background_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get specific background details.
    """
    asset_service = AssetService(db)
    
    background = db.query(Asset).filter(
        Asset.id == background_id,
        Asset.created_by_user_id == current_user.id,
        Asset.type == AssetType.BACKGROUND_IMAGE
    ).first()
    
    if not background:
        raise HTTPException(404, "Background not found or access denied")
    
    status = "ready" if background.path else "generating"
    url = asset_service.get_asset_url(background) if background.path else None
    
    return {
        "id": background.id,
        "status": status,
        "url": url,
        "theme_text": None,
        "created_at": background.created_at.isoformat()
    }


@router.delete("/{background_id}")
async def delete_background(
    background_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete background from library.
    Fails if background is used in any posters.
    """
    from app.models.poster import Poster
    
    background = db.query(Asset).filter(
        Asset.id == background_id,
        Asset.created_by_user_id == current_user.id,
        Asset.type == AssetType.BACKGROUND_IMAGE
    ).first()
    
    if not background:
        raise HTTPException(404, "Background not found or access denied")
    
    # Check if used in posters
    posters_using = db.query(Poster).filter(
        Poster.background_image_id == background_id
    ).count()
    
    if posters_using > 0:
        raise HTTPException(
            400,
            f"Cannot delete background: used in {posters_using} poster(s)"
        )
    
    # Delete file from storage
    # TODO: Implement file deletion based on storage backend
    
    # Delete from database
    db.delete(background)
    db.commit()
    
    return {"message": "Background deleted successfully"}
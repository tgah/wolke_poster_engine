"""Poster API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.schemas.poster import (
    PosterCreate, PosterUpdate, PosterResponse,
    BackgroundGenerateRequest, PosterExportRequest
)
from app.services.poster_service import PosterService
from app.dependencies import get_current_user
from app.models.poster import PosterStatus

router = APIRouter(prefix="/posters", tags=["posters"])


@router.post("", response_model=PosterResponse, status_code=201)
async def create_poster(
    data: PosterCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new poster."""
    service = PosterService(db)
    
    try:
        poster = service.create_poster(
            data,
            current_user.id,
            current_user.company_id
        )
        
        # If not using uploaded background, trigger generation
        if not data.use_uploaded_background and data.theme_text:
            print(f"🚀 Queueing background generation for poster {poster.id}")
            print(f"   Theme: {data.theme_text}")
            
            # Update status first
            poster.status = PosterStatus.BACKGROUND_GENERATING
            db.commit()
            db.refresh(poster)
            
            # Import and queue the task
            # Import here to avoid issues at startup
            try:
                from app.workers.tasks import generate_background_task
                
                # Call the Celery task with .delay()
                task = generate_background_task.delay(
                    str(poster.id),
                    str(current_user.id),
                    data.theme_text
                )
                
                print(f"✅ Task queued with ID: {task.id}")
                
            except Exception as e:
                print(f"❌ Error queueing task: {str(e)}")
                import traceback
                traceback.print_exc()
                
                # Rollback status on error
                poster.status = PosterStatus.FAILED
                db.commit()
                raise HTTPException(500, f"Failed to queue background generation: {str(e)}")
        
        return poster
    
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/{poster_id}", response_model=PosterResponse)
async def get_poster(
    poster_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get poster details."""
    service = PosterService(db)
    
    try:
        poster = service.get_poster(poster_id, current_user.company_id)
        return poster
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.patch("/{poster_id}", response_model=PosterResponse)
async def update_poster(
    poster_id: UUID,
    data: PosterUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update poster details."""
    service = PosterService(db)
    
    try:
        poster = service.update_poster(
            poster_id,
            data,
            current_user.id,
            current_user.company_id
        )
        return poster
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{poster_id}/background/generate")
async def generate_background(
    poster_id: UUID,
    data: BackgroundGenerateRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trigger background generation for poster."""
    from app.utils.rate_limiter import RateLimiter
    from app.workers.tasks import generate_background_task
    
    print(f"🚀 Manual background generation requested for poster {poster_id}")
    
    # Check rate limit
    allowed, error = RateLimiter.check_same_theme_cooldown(
        db,
        str(current_user.id),
        data.theme_text
    )
    
    if not allowed:
        raise HTTPException(429, error)
    
    # Update poster status
    service = PosterService(db)
    try:
        poster = service.get_poster(poster_id, current_user.company_id)
        poster.status = PosterStatus.BACKGROUND_GENERATING
        poster.theme_text = data.theme_text
        db.commit()
    except ValueError as e:
        raise HTTPException(404, str(e))
    
    # Queue background task
    try:
        task = generate_background_task.delay(
            str(poster_id),
            str(current_user.id),
            data.theme_text
        )
        
        print(f"✅ Task queued with ID: {task.id}")
        
        return {
            "message": "Background generation started",
            "poster_id": str(poster_id),
            "task_id": task.id
        }
    
    except Exception as e:
        print(f"❌ Error queueing task: {str(e)}")
        import traceback
        traceback.print_exc()
        
        poster.status = PosterStatus.FAILED
        db.commit()
        
        raise HTTPException(500, f"Failed to queue background generation: {str(e)}")


@router.post("/{poster_id}/export")
async def export_poster(
    poster_id: UUID,
    data: PosterExportRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export poster as image."""
    from app.services.poster_service import PosterService
    from app.rendering.compositor import PosterCompositor
    from app.services.asset_service import AssetService
    from app.models.asset import AssetType
    
    service = PosterService(db)
    
    try:
        poster = service.get_poster(poster_id, current_user.company_id)
        
        if poster.status != PosterStatus.READY:
            raise HTTPException(400, f"Poster is not ready for export. Current status: {poster.status}")
        
        if not poster.background_image:
            raise HTTPException(400, "Poster has no background image")
        
        # Render poster
        compositor = PosterCompositor()
        image_bytes = compositor.render_poster(
            poster,
            poster.background_image,
            format=data.format.upper()
        )
        
        # Save as asset
        asset_service = AssetService(db)
        asset = asset_service.save_asset(
            image_bytes,
            AssetType.POSTER_EXPORT,
            current_user.company_id,
            user_id=current_user.id,
            mime_type=f"image/{data.format}"
        )
        
        return {
            "asset_id": str(asset.id),
            "url": asset_service.get_asset_url(asset)
        }
    
    except ValueError as e:
        raise HTTPException(404, str(e))
"""Asset serving endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.models.asset import Asset
from app.services.asset_service import AssetService
from app.dependencies import get_current_user

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("/{asset_id}/url")
async def get_asset_url(
    asset_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get public URL for an asset."""
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.company_id == current_user.company_id
    ).first()
    
    if not asset:
        raise HTTPException(404, "Asset not found")
    
    service = AssetService(db)
    url = service.get_asset_url(asset)
    
    return {"url": url}
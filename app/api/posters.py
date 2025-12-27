"""Poster API endpoints with session products and image uploads."""
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from PIL import Image
import io
import base64

from app.database import get_db
from app.dependencies import get_current_user, get_session_id
from app.schemas.poster import PosterResponse, PosterExportRequest
from app.models.poster import Poster, PosterProduct, PosterTemplate, PosterStatus
from app.models.asset import Asset, AssetType
from app.services.asset_service import AssetService
from app.services.audit_service import AuditService
from app.utils.session_manager import SessionManager
from app.rendering.compositor import PosterCompositor

router = APIRouter(prefix="/posters", tags=["posters"])


@router.post("", status_code=201)
async def create_poster(
    background_id: UUID = Form(...),
    template_key: str = Form(...),
    sale_title: str = Form(...),
    artikel_nr_0: str = Form(...),
    artikel_nr_1: str = Form(...),
    artikel_nr_2: Optional[str] = Form(None),
    sale_price_0: Decimal = Form(...),
    sale_price_1: Decimal = Form(...),
    sale_price_2: Optional[Decimal] = Form(None),
    product_image_0: UploadFile = File(...),
    product_image_1: UploadFile = File(...),
    product_image_2: Optional[UploadFile] = File(None),
    current_user = Depends(get_current_user),
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db)
):
    """
    Create poster with background and product images.
    
    Multipart form data:
    - background_id: UUID of background from user's library
    - template_key: "two_product" or "three_product"
    - sale_title: Poster title
    - artikel_nr_N: Product identifiers from session
    - sale_price_N: Sale prices for products
    - product_image_N: Uploaded images for products
    """
    
    print(f"🎨 Creating poster for user {current_user.id}")
    
    # Validate template
    template = db.query(PosterTemplate).filter(
        PosterTemplate.key == template_key
    ).first()
    
    if not template:
        raise HTTPException(400, f"Invalid template: {template_key}")
    
    # Validate background belongs to user
    background = db.query(Asset).filter(
        Asset.id == background_id,
        Asset.created_by_user_id == current_user.id,
        Asset.type == AssetType.BACKGROUND_IMAGE
    ).first()
    
    if not background:
        raise HTTPException(404, "Background not found or access denied")
    
    if not background.path:
        raise HTTPException(400, "Background is still generating")
    
    # Get products from session
    session_mgr = SessionManager()
    session_products = session_mgr.get_products(session_id)
    
    if session_products is None:
        raise HTTPException(
            410,
            "Session expired. Please re-upload CSV."
        )
    
    # Collect product data
    artikel_nrs = [artikel_nr_0, artikel_nr_1]
    sale_prices = [sale_price_0, sale_price_1]
    product_images = [product_image_0, product_image_1]
    
    if template.max_products == 3:
        if not artikel_nr_2 or not sale_price_2 or not product_image_2:
            raise HTTPException(400, "Three products required for this template")
        artikel_nrs.append(artikel_nr_2)
        sale_prices.append(sale_price_2)
        product_images.append(product_image_2)
    
    # Validate product count
    if len(artikel_nrs) != template.max_products:
        raise HTTPException(
            400,
            f"Template requires exactly {template.max_products} products"
        )
    
    # Create poster
    poster = Poster(
        store_id=current_user.store_id,
        template_id=template.id,
        background_image_id=background_id,
        sale_title=sale_title,
        status=PosterStatus.READY,
        created_by_user_id=current_user.id
    )
    db.add(poster)
    db.flush()
    
    print(f"📋 Created poster {poster.id}")
    
    # Process each product
    for idx, (artikel_nr, sale_price, img_file) in enumerate(zip(
        artikel_nrs, sale_prices, product_images
    ), start=1):
        
        # Find product in session
        product_data = session_mgr.get_product_by_artikel_nr(session_id, artikel_nr)
        
        if not product_data:
            db.rollback()
            raise HTTPException(
                400,
                f"Product {artikel_nr} not found in session"
            )
        
        # Read and process image
        try:
            img_content = await img_file.read()
            img = Image.open(io.BytesIO(img_content))
            
            # Resize to max 800x800
            img.thumbnail((800, 800), Image.Resampling.LANCZOS)
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save as JPEG with compression
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85, optimize=True)
            buffer.seek(0)
            
            # Convert to base64
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            print(f"  📷 Processed image for product {idx}: {len(img_base64)} chars")
        
        except Exception as e:
            db.rollback()
            raise HTTPException(400, f"Failed to process image {idx}: {str(e)}")
        
        # Create poster product with denormalized data
        poster_product = PosterProduct(
            poster_id=poster.id,
            display_order=idx,
            artikel_nr=product_data['artikel_nr'],
            german_name=product_data['german_name'],
            chinese_name=product_data.get('chinese_name'),
            weight=product_data.get('weight'),
            product_image_base64=img_base64,
            sale_price=sale_price,
            old_price=product_data.get('old_price')
        )
        db.add(poster_product)
    
    db.commit()
    db.refresh(poster)
    
    print(f"✅ Poster {poster.id} created successfully")
    
    # Audit log
    audit = AuditService(db)
    audit.log(
        action="poster_created",
        user_id=current_user.id,
        entity_type="poster",
        entity_id=poster.id,
        metadata={
            "template": template_key,
            "background_id": str(background_id),
            "products": artikel_nrs
        }
    )
    
    return {
        "id": str(poster.id),
        "status": "ready",
        "message": "Poster created successfully"
    }


@router.get("", response_model=List[dict])
async def list_posters(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all posters for current user."""
    posters = db.query(Poster).filter(
        Poster.created_by_user_id == current_user.id
    ).order_by(Poster.created_at.desc()).offset(skip).limit(limit).all()
    
    asset_service = AssetService(db)
    
    result = []
    for poster in posters:
        bg_url = asset_service.get_asset_url(poster.background_image) if poster.background_image else None
        
        result.append({
            "id": str(poster.id),
            "sale_title": poster.sale_title,
            "template_key": poster.template.key,
            "background_url": bg_url,
            "status": poster.status.value,
            "created_at": poster.created_at.isoformat(),
            "product_count": len(poster.products)
        })
    
    return result


@router.get("/{poster_id}")
async def get_poster(
    poster_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get poster details."""
    poster = db.query(Poster).filter(
        Poster.id == poster_id,
        Poster.created_by_user_id == current_user.id
    ).first()
    
    if not poster:
        raise HTTPException(404, "Poster not found or access denied")
    
    asset_service = AssetService(db)
    bg_url = asset_service.get_asset_url(poster.background_image)
    
    products = []
    for pp in sorted(poster.products, key=lambda p: p.display_order):
        products.append({
            "artikel_nr": pp.artikel_nr,
            "german_name": pp.german_name,
            "chinese_name": pp.chinese_name,
            "weight": pp.weight,
            "sale_price": float(pp.sale_price),
            "old_price": float(pp.old_price) if pp.old_price else None,
            "has_image": bool(pp.product_image_base64)
        })
    
    return {
        "id": str(poster.id),
        "sale_title": poster.sale_title,
        "template_key": poster.template.key,
        "background_url": bg_url,
        "status": poster.status.value,
        "created_at": poster.created_at.isoformat(),
        "products": products
    }


@router.post("/{poster_id}/export")
async def export_poster(
    poster_id: UUID,
    data: PosterExportRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export poster as image.
    First export is rendered and cached.
    Subsequent exports return cached version.
    """
    poster = db.query(Poster).filter(
        Poster.id == poster_id,
        Poster.created_by_user_id == current_user.id
    ).first()
    
    if not poster:
        raise HTTPException(404, "Poster not found or access denied")
    
    if poster.status != PosterStatus.READY:
        raise HTTPException(400, f"Poster is not ready. Status: {poster.status.value}")
    
    # Check for cached export
    asset_service = AssetService(db)
    # cached_export = db.query(Asset).filter(
    #     Asset.type == AssetType.POSTER_EXPORT,
    #     Asset.created_by_user_id == current_user.id
    # ).join(
    #     # This is a simplification - in production you'd want to link exports to posters
    #     Asset, Asset.created_by_user_id == current_user.id
    # ).first()

    cached_export = db.query(Asset).filter(
        Asset.type == AssetType.POSTER_EXPORT,
        Asset.created_by_user_id == current_user.id
    ).first()
    
    # For now, always render (caching can be improved)
    print(f"🎨 Rendering poster {poster_id}")
    
    # Render poster
    compositor = PosterCompositor()
    image_bytes = compositor.render_poster(
        poster,
        poster.background_image,
        format=data.format.upper()
    )
    
    # Save as asset
    asset = asset_service.save_asset(
        image_bytes,
        AssetType.POSTER_EXPORT,
        current_user.company_id,
        user_id=current_user.id,
        mime_type=f"image/{data.format}"
    )
    
    url = asset_service.get_asset_url(asset)
    
    print(f"✅ Poster exported: {url}")
    
    return {
        "asset_id": str(asset.id),
        "url": url,
        "format": data.format
    }
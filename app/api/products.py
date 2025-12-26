"""Product API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.product import ProductResponse, ProductImportResponse
from app.services.product_service import ProductService
from app.dependencies import get_current_user

router = APIRouter(prefix="/products", tags=["products"])

@router.get("", response_model=List[ProductResponse])
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: str = Query(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List products with optional search."""
    service = ProductService(db)
    products = service.get_products(
        current_user.company_id,
        skip=skip,
        limit=limit,
        search=search
    )
    return products

@router.post("/import", response_model=ProductImportResponse)
async def import_products(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import products from CSV file."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(400, "Only CSV files are allowed")
    
    content = await file.read()
    
    service = ProductService(db)
    result = service.import_csv(
        content,
        file.filename,
        current_user.company_id,
        current_user.id
    )
    
    return result
"""Product API endpoints with Redis session storage."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
import pandas as pd
import io

from app.database import get_db
from app.dependencies import get_current_user, get_session_id
from app.utils.session_manager import SessionManager
from app.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/products", tags=["products"])


class ProductResponse(BaseModel):
    artikel_nr: str
    chinese_name: str = None
    german_name: str
    weight: str = None
    old_price: float = None
    new_price: float


class ProductImportResponse(BaseModel):
    message: str
    products_count: int
    products: List[ProductResponse]
    ttl_seconds: int


@router.post("/import", response_model=ProductImportResponse)
async def import_products(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db)
):
    """
    Import products from CSV to session storage (Redis).
    Data expires after 2 hours or on logout.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(400, "Only CSV files are allowed")
    
    content = await file.read()
    
    try:
        # Parse CSV
        df = pd.read_csv(
            io.BytesIO(content),
            dtype=str  # Read everything as string first
        )
        
        # Validate required columns
        required_cols = set(settings.CSV_REQUIRED_COLUMNS)
        actual_cols = set(df.columns)
        
        if not required_cols.issubset(actual_cols):
            missing = required_cols - actual_cols
            raise ValueError(f"Missing columns: {missing}")
        
        # Validate row count
        if len(df) > settings.CSV_MAX_ROWS:
            raise ValueError(
                f"Too many rows. Maximum {settings.CSV_MAX_ROWS} allowed."
            )
        
        # Convert to list of dicts
        products = []
        for idx, row in df.iterrows():
            try:
                artikel_nr = str(row['artikelNr']).strip()
                chinese_name = str(row['chineseName']).strip() if pd.notna(row['chineseName']) else None
                german_name = str(row['germanName']).strip()
                weight = str(row['weight']).strip() if pd.notna(row['weight']) else None
                
                old_price = None
                if pd.notna(row['oldPrice']):
                    old_price = float(row['oldPrice'])
                
                new_price = float(row['newPrice'])
                
                if new_price <= 0:
                    raise ValueError("New price must be positive")
                
                products.append({
                    'artikel_nr': artikel_nr,
                    'chinese_name': chinese_name,
                    'german_name': german_name,
                    'weight': weight,
                    'old_price': old_price,
                    'new_price': new_price
                })
            
            except Exception as e:
                print(f"Error parsing row {idx + 2}: {str(e)}")
                continue
        
        if not products:
            raise ValueError("No valid products found in CSV")
        
        # Store in Redis
        session_mgr = SessionManager()
        session_mgr.store_products(session_id, products)
        
        # Audit log
        from app.services.audit_service import AuditService
        audit = AuditService(db)
        audit.log(
            action="products_imported_to_session",
            user_id=current_user.id,
            metadata={
                "filename": file.filename,
                "products_count": len(products),
                "session_id": session_id
            }
        )
        
        print(f"✅ Imported {len(products)} products to session {session_id}")
        
        return {
            "message": f"Successfully imported {len(products)} products",
            "products_count": len(products),
            "products": products,
            "ttl_seconds": 7200
        }
    
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to process CSV: {str(e)}")


@router.get("", response_model=List[ProductResponse])
async def list_products(
    current_user = Depends(get_current_user),
    session_id: str = Depends(get_session_id)
):
    """
    List products from current session.
    Returns 410 Gone if session expired.
    """
    session_mgr = SessionManager()
    products = session_mgr.get_products(session_id)
    
    if products is None:
        raise HTTPException(
            status_code=410,
            detail={
                "error": "Session expired",
                "message": "Your product data has expired. Please re-upload CSV.",
                "error_code": "SESSION_EXPIRED"
            }
        )
    
    return products


@router.get("/ttl")
async def get_session_ttl(
    current_user = Depends(get_current_user),
    session_id: str = Depends(get_session_id)
):
    """
    Get remaining time before session products expire.
    """
    session_mgr = SessionManager()
    ttl = session_mgr.get_ttl(session_id)
    
    if ttl == -2:
        raise HTTPException(
            status_code=410,
            detail={
                "error": "Session expired",
                "message": "Your product data has expired. Please re-upload CSV.",
                "error_code": "SESSION_EXPIRED"
            }
        )
    
    return {
        "ttl_seconds": ttl,
        "ttl_minutes": ttl // 60,
        "message": f"Products will expire in {ttl // 60} minutes"
    }
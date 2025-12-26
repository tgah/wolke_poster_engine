"""Product management service."""
import io
import pandas as pd
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.product import Product, ProductImport, ImportStatus
from app.schemas.product import ProductCreate, ProductResponse
from app.services.audit_service import AuditService
from app.config import get_settings

settings = get_settings()


class ProductService:
    """Handle product CRUD and CSV imports."""
    
    def __init__(self, db: Session):
        self.db = db
        self.audit = AuditService(db)
    
    def get_products(
        self,
        company_id: UUID,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> List[Product]:
        """Get paginated product list with optional search."""
        query = self.db.query(Product).filter(
            Product.company_id == company_id
        )
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Product.artikel_nr.ilike(search_term),
                    Product.german_name.ilike(search_term),
                    Product.chinese_name.ilike(search_term)
                )
            )
        
        return query.offset(skip).limit(limit).all()
    
    def get_product(self, product_id: UUID, company_id: UUID) -> Optional[Product]:
        """Get single product by ID."""
        return self.db.query(Product).filter(
            Product.id == product_id,
            Product.company_id == company_id
        ).first()
    
    def import_csv(
        self,
        file_content: bytes,
        filename: str,
        company_id: UUID,
        user_id: UUID
    ) -> ProductImport:
        """
        Import products from CSV.
        Expected columns: artikelNr, chineseName, germanName, weight, oldPrice, newPrice
        """
        # Create import record
        import_record = ProductImport(
            company_id=company_id,
            uploaded_by_user_id=user_id,
            filename=filename,
            status=ImportStatus.PROCESSING
        )
        self.db.add(import_record)
        self.db.commit()
        
        try:
            # Parse CSV
            df = pd.read_csv(
                io.BytesIO(file_content),
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
            
            rows_processed = 0
            rows_succeeded = 0
            rows_failed = 0
            errors = []
            
            for idx, row in df.iterrows():
                try:
                    # Parse and validate
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
                    
                    # Upsert product
                    product = self.db.query(Product).filter(
                        Product.company_id == company_id,
                        Product.artikel_nr == artikel_nr
                    ).first()
                    
                    if product:
                        # Update existing
                        product.chinese_name = chinese_name
                        product.german_name = german_name
                        product.weight = weight
                        product.old_price = old_price
                        product.new_price = new_price
                    else:
                        # Create new
                        product = Product(
                            company_id=company_id,
                            artikel_nr=artikel_nr,
                            chinese_name=chinese_name,
                            german_name=german_name,
                            weight=weight,
                            old_price=old_price,
                            new_price=new_price
                        )
                        self.db.add(product)
                    
                    rows_succeeded += 1
                
                except Exception as e:
                    rows_failed += 1
                    errors.append(f"Row {idx + 2}: {str(e)}")
                
                finally:
                    rows_processed += 1
            
            self.db.commit()
            
            # Update import record
            import_record.status = ImportStatus.COMPLETED
            import_record.rows_processed = rows_processed
            import_record.rows_succeeded = rows_succeeded
            import_record.rows_failed = rows_failed
            
            if errors:
                import_record.error_message = "\n".join(errors[:10])  # First 10 errors
            
            import_record.completed_at = datetime.utcnow()
            self.db.commit()
            
            # Audit
            self.audit.log(
                action="product_import_completed",
                user_id=user_id,
                entity_type="product_import",
                entity_id=import_record.id,
                metadata={
                    "filename": filename,
                    "rows_processed": rows_processed,
                    "rows_succeeded": rows_succeeded,
                    "rows_failed": rows_failed
                }
            )
            
        except Exception as e:
            import_record.status = ImportStatus.FAILED
            import_record.error_message = str(e)
            import_record.completed_at = datetime.utcnow()
            self.db.commit()
            
            self.audit.log(
                action="product_import_failed",
                user_id=user_id,
                entity_type="product_import",
                entity_id=import_record.id,
                metadata={"filename": filename, "error": str(e)}
            )
        
        return import_record
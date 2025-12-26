"""Poster management service."""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.poster import Poster, PosterProduct, PosterTemplate, PosterStatus
from app.models.product import Product
from app.schemas.poster import PosterCreate, PosterUpdate, PosterResponse
from app.services.audit_service import AuditService
from app.utils.validators import PriceValidator
from app.config import get_settings

settings = get_settings()


class PosterService:
    """Handle poster CRUD operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.audit = AuditService(db)
    
    def create_poster(
        self,
        data: PosterCreate,
        user_id: UUID,
        company_id: UUID
    ) -> Poster:
        """Create a new poster."""
        # Validate template
        template = self.db.query(PosterTemplate).filter(
            PosterTemplate.key == data.template_key
        ).first()
        
        if not template:
            raise ValueError(f"Invalid template key: {data.template_key}")
        
        # Validate product count
        if len(data.products) > template.max_products:
            raise ValueError(
                f"Too many products. Maximum {template.max_products} allowed for this template."
            )
        
        # Validate all products exist and belong to company
        for prod_input in data.products:
            product = self.db.query(Product).filter(
                Product.id == prod_input.product_id,
                Product.company_id == company_id
            ).first()
            
            if not product:
                raise ValueError(f"Product {prod_input.product_id} not found")
            
            # Validate sale price
            old_price = prod_input.old_price or product.old_price
            valid, error = PriceValidator.validate_sale_price(
                prod_input.sale_price,
                old_price
            )
            if not valid:
                raise ValueError(error)
        
        # Create poster
        poster = Poster(
            store_id=data.store_id,
            template_id=template.id,
            theme_text=data.theme_text,
            sale_title=data.sale_title,
            status=PosterStatus.DRAFT,
            created_by_user_id=user_id
        )
        
        self.db.add(poster)
        self.db.flush()
        
        # Create poster products
        for idx, prod_input in enumerate(data.products, 1):
            product = self.db.query(Product).get(prod_input.product_id)
            
            poster_product = PosterProduct(
                poster_id=poster.id,
                product_id=prod_input.product_id,
                display_order=idx,
                display_name=prod_input.display_name or product.german_name,
                display_weight=prod_input.display_weight or product.weight,
                sale_price=prod_input.sale_price,
                old_price=prod_input.old_price or product.old_price
            )
            self.db.add(poster_product)
        
        self.db.commit()
        self.db.refresh(poster)
        
        # Audit
        self.audit.log(
            action="poster_created",
            user_id=user_id,
            entity_type="poster",
            entity_id=poster.id,
            metadata={"template": data.template_key, "store_id": str(data.store_id)}
        )
        
        return poster
    
    def update_poster(
        self,
        poster_id: UUID,
        data: PosterUpdate,
        user_id: UUID,
        company_id: UUID
    ) -> Poster:
        """Update poster details (without regenerating background)."""
        poster = self._get_poster_for_company(poster_id, company_id)
        
        if data.sale_title is not None:
            poster.sale_title = data.sale_title
        
        if data.theme_text is not None:
            poster.theme_text = data.theme_text
        
        if data.products is not None:
            # Delete existing products
            self.db.query(PosterProduct).filter(
                PosterProduct.poster_id == poster_id
            ).delete()
            
            # Add new products
            for idx, prod_input in enumerate(data.products, 1):
                product = self.db.query(Product).filter(
                    Product.id == prod_input.product_id,
                    Product.company_id == company_id
                ).first()
                
                if not product:
                    raise ValueError(f"Product {prod_input.product_id} not found")
                
                poster_product = PosterProduct(
                    poster_id=poster.id,
                    product_id=prod_input.product_id,
                    display_order=idx,
                    display_name=prod_input.display_name or product.german_name,
                    display_weight=prod_input.display_weight or product.weight,
                    sale_price=prod_input.sale_price,
                    old_price=prod_input.old_price or product.old_price
                )
                self.db.add(poster_product)
        
        poster.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(poster)
        
        return poster
    
    def get_poster(self, poster_id: UUID, company_id: UUID) -> Optional[Poster]:
        """Get poster with all relationships loaded."""
        return self._get_poster_for_company(poster_id, company_id)
    
    def _get_poster_for_company(self, poster_id: UUID, company_id: UUID) -> Poster:
        """Internal helper to get poster and validate company."""
        poster = self.db.query(Poster).filter(
            Poster.id == poster_id
        ).first()
        
        if not poster:
            raise ValueError("Poster not found")
        
        # Check company through store
        if poster.store.company_id != company_id:
            raise ValueError("Poster not found")
        
        return poster
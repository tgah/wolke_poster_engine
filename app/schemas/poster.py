"""Poster schemas."""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.schemas.product import ProductResponse


class PosterProductInput(BaseModel):
    product_id: UUID
    sale_price: Decimal = Field(gt=0)
    display_name: Optional[str] = None
    display_weight: Optional[str] = None
    old_price: Optional[Decimal] = None
    
    @field_validator('sale_price', 'old_price')
    def validate_prices(cls, v):
        if v is not None and v < 0:
            raise ValueError('Price cannot be negative')
        return v


class PosterCreate(BaseModel):
    store_id: UUID
    template_key: str  # "two_product" or "three_product"
    theme_text: Optional[str] = None
    sale_title: str = Field(min_length=1, max_length=500)
    products: List[PosterProductInput] = Field(min_length=1, max_length=3)
    use_uploaded_background: bool = False


class PosterUpdate(BaseModel):
    sale_title: Optional[str] = Field(None, min_length=1, max_length=500)
    theme_text: Optional[str] = None
    products: Optional[List[PosterProductInput]] = None


class BackgroundGenerateRequest(BaseModel):
    theme_text: str = Field(min_length=5, max_length=2000)


class PosterExportRequest(BaseModel):
    format: str = Field(default="png", pattern="^(png|pdf)$")
    resolution: str = Field(default="digital", pattern="^(digital|print)$")


class PosterProductResponse(BaseModel):
    id: UUID
    product_id: UUID
    display_order: int
    display_name: Optional[str]
    display_weight: Optional[str]
    sale_price: Decimal
    old_price: Optional[Decimal]
    
    # Embedded product info
    product: Optional["ProductResponse"] = None
    
    model_config = ConfigDict(from_attributes=True)


class PosterResponse(BaseModel):
    id: UUID
    store_id: UUID
    template_id: UUID
    background_image_id: Optional[UUID]
    background_image_url: Optional[str] = None
    theme_text: Optional[str]
    llm_prompt: Optional[str]
    sale_title: str
    status: str
    created_by_user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    
    # Relationships
    products: List[PosterProductResponse] = []
    template_key: Optional[str] = None
    store_logo_url: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
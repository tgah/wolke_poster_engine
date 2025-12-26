"""Product schemas."""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class ProductBase(BaseModel):
    artikel_nr: str
    chinese_name: Optional[str] = None
    german_name: str
    weight: Optional[str] = None
    old_price: Optional[Decimal] = None
    new_price: Decimal
    image_path: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    chinese_name: Optional[str] = None
    german_name: Optional[str] = None
    weight: Optional[str] = None
    old_price: Optional[Decimal] = None
    new_price: Optional[Decimal] = None
    image_path: Optional[str] = None


class ProductResponse(ProductBase):
    id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


class ProductImportResponse(BaseModel):
    id: UUID
    filename: str
    status: str
    rows_processed: int
    rows_succeeded: int
    rows_failed: int
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)
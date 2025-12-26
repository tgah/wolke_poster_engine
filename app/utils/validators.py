"""Input validation utilities."""
from typing import List, Optional
from decimal import Decimal
from app.config import get_settings

settings = get_settings()


class PriceValidator:
    """Validate pricing rules."""
    
    @staticmethod
    def validate_sale_price(
        sale_price: Decimal,
        old_price: Optional[Decimal]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate sale price against old price.
        Returns (is_valid, error_message).
        """
        if not settings.VALIDATE_SALE_PRICE_LTE_OLD_PRICE:
            return True, None
        
        if old_price is not None and sale_price > old_price:
            return False, (
                f"Sale price ({sale_price}) cannot be higher than "
                f"old price ({old_price})"
            )
        
        return True, None


class ImageValidator:
    """Validate image uploads."""
    
    @staticmethod
    def validate_image_type(mime_type: str) -> tuple[bool, Optional[str]]:
        """Validate image MIME type."""
        if mime_type not in settings.ALLOWED_IMAGE_TYPES:
            return False, (
                f"Invalid image type. Allowed types: "
                f"{', '.join(settings.ALLOWED_IMAGE_TYPES)}"
            )
        return True, None
    
    @staticmethod
    def validate_image_size(
        width: int,
        height: int,
        min_width: Optional[int] = None,
        min_height: Optional[int] = None
    ) -> tuple[bool, Optional[str]]:
        """Validate image dimensions."""
        min_w = min_width or settings.MIN_BACKGROUND_WIDTH
        min_h = min_height or settings.MIN_BACKGROUND_HEIGHT
        
        if width < min_w or height < min_h:
            return False, (
                f"Image too small. Minimum dimensions: "
                f"{min_w}x{min_h}px"
            )
        return True, None
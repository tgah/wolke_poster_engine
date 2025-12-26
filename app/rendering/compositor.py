"""Poster composition and rendering."""
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any, Optional
import io

from app.models.poster import Poster, PosterProduct
from app.models.asset import Asset
from app.config import get_settings

settings = get_settings()


class PosterCompositor:
    """Compose final poster with background and overlays."""
    
    def __init__(self):
        self.default_font_path = settings.EXPORT_FONT_PATH
        self.bold_font_path = settings.EXPORT_FONT_BOLD_PATH
    
    def render_poster(
        self,
        poster: Poster,
        background_image: Asset,
        format: str = "PNG"
    ) -> bytes:
        """
        Render poster to image bytes.
        
        Args:
            poster: Poster model with all relationships loaded
            background_image: Background asset
            format: Output format (PNG or PDF)
        
        Returns:
            Rendered image as bytes
        """
        # Load background
        bg_img = self._load_image_from_asset(background_image)
        
        # Create drawing context
        draw = ImageDraw.Draw(bg_img)
        
        # Get template layout
        layout = poster.template.layout_json
        
        # Draw title
        self._draw_title(draw, poster.sale_title, layout["title"])
        
        # Draw products
        for idx, poster_product in enumerate(sorted(poster.products, key=lambda p: p.display_order)):
            product_layout = layout["products"][idx]
            self._draw_product(
                bg_img,
                draw,
                poster_product,
                product_layout
            )
        
        # Draw logo if available
        if poster.store.settings and poster.store.settings.logo:
            self._draw_logo(bg_img, poster.store.settings.logo, layout["logo"])
        
        # Convert to bytes
        output = io.BytesIO()
        bg_img.save(output, format=format, quality=95, dpi=(300, 300))
        return output.getvalue()
    
    def _load_image_from_asset(self, asset: Asset) -> Image.Image:
        """Load image from asset storage."""
        from pathlib import Path
        
        if asset.storage_backend.value == "local":
            path = Path(settings.STORAGE_BASE_PATH) / asset.path
            return Image.open(path).convert("RGBA")
        else:
            # Load from S3
            raise NotImplementedError("S3 loading not implemented")
    
    def _draw_title(self, draw: ImageDraw, title: str, layout: Dict):
        """Draw sale title."""
        font = ImageFont.truetype(self.bold_font_path, layout["font_size"])
        
        # Get text color
        color = layout.get("color", "#FFFFFF")
        
        # Draw text
        draw.text(
            (layout["x"], layout["y"]),
            title,
            font=font,
            fill=color
        )
    
    def _draw_product(
        self,
        img: Image.Image,
        draw: ImageDraw,
        poster_product: PosterProduct,
        layout: Dict
    ):
        """Draw product with image, name, and price."""
        # Load product image if available
        if poster_product.product.image_path:
            try:
                product_img = self._load_product_image(poster_product.product.image_path)
                # Resize to fit layout
                product_img = product_img.resize(
                    (layout["width"], layout["height"]),
                    Image.Resampling.LANCZOS
                )
                # Paste onto poster
                img.paste(product_img, (layout["x"], layout["y"]), product_img)
            except Exception:
                pass  # Skip if image not found
        
        # Draw product name below image
        name_y = layout["y"] + layout["height"] + 10
        font = ImageFont.truetype(self.default_font_path, 24)
        draw.text(
            (layout["x"], name_y),
            poster_product.display_name or poster_product.product.german_name,
            font=font,
            fill="#FFFFFF"
        )
        
        # Draw price
        price_y = name_y + 30
        price_font = ImageFont.truetype(self.bold_font_path, 32)
        price_text = f"€{poster_product.sale_price:.2f}"
        
        draw.text(
            (layout["x"], price_y),
            price_text,
            font=price_font,
            fill="#FFD700"  # Gold color for price
        )
        
        # Draw old price if available
        if poster_product.old_price:
            old_price_text = f"€{poster_product.old_price:.2f}"
            old_price_font = ImageFont.truetype(self.default_font_path, 20)
            
            # Draw strikethrough
            x_pos = layout["x"] + 150
            draw.text(
                (x_pos, price_y + 5),
                old_price_text,
                font=old_price_font,
                fill="#AAAAAA"
            )
            
            # Strikethrough line
            bbox = draw.textbbox((x_pos, price_y), old_price_text, font=old_price_font)
            draw.line(
                [(bbox[0], bbox[1] + 10), (bbox[2], bbox[1] + 10)],
                fill="#AAAAAA",
                width=2
            )
    
    def _load_product_image(self, image_path: str) -> Image.Image:
        """Load product image from path."""
        from pathlib import Path
        
        full_path = Path(settings.STORAGE_BASE_PATH) / image_path
        return Image.open(full_path).convert("RGBA")
    
    def _draw_logo(self, img: Image.Image, logo_asset: Asset, layout: Dict):
        """Draw store logo."""
        logo_img = self._load_image_from_asset(logo_asset)
        
        # Resize to fit
        logo_img.thumbnail(
            (layout["max_width"], layout["max_height"]),
            Image.Resampling.LANCZOS
        )
        
        # Paste logo
        img.paste(logo_img, (layout["x"], layout["y"]), logo_img)

"""Poster composition with base64 embedded images."""
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any, Optional
import io
import os
import base64

from app.models.poster import Poster, PosterProduct
from app.models.asset import Asset
from app.config import get_settings

settings = get_settings()


class PosterCompositor:
    """Compose final poster with background and overlays."""
    
    def __init__(self):
        self.default_font_path = settings.EXPORT_FONT_PATH
        self.bold_font_path = settings.EXPORT_FONT_BOLD_PATH
        
        # Font fallback paths for Mac
        self.font_fallbacks = [
            (self.default_font_path, self.bold_font_path),
            ("/System/Library/Fonts/Supplemental/Arial.ttf", 
             "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
            ("/System/Library/Fonts/Helvetica.ttc", 
             "/System/Library/Fonts/Helvetica.ttc"),
            ("./fonts/Arial.ttf", "./fonts/Arial-Bold.ttf"),
        ]
    
    def _get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """Get font with fallback support."""
        for regular_path, bold_path in self.font_fallbacks:
            font_path = bold_path if bold else regular_path
            
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, size)
                except Exception:
                    continue
        
        print(f"⚠️  Warning: Using default font")
        return ImageFont.load_default()
    
    def render_poster(
        self,
        poster: Poster,
        background_image: Asset,
        format: str = "PNG"
    ) -> bytes:
        """Render poster to image bytes with base64 product images."""
        
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
            if idx < len(layout["products"]):
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
        bg_img.save(output, format=format, quality=95)
        output.seek(0)
        return output.getvalue()
    
    def _load_image_from_asset(self, asset: Asset) -> Image.Image:
        """Load image from asset storage."""
        from pathlib import Path
        
        if asset.storage_backend.value == "local":
            path = Path(settings.STORAGE_BASE_PATH) / asset.path
            return Image.open(path).convert("RGBA")
        else:
            raise NotImplementedError("S3 loading not implemented")
    
    def _load_image_from_base64(self, base64_str: str) -> Image.Image:
        """Load image from base64 string."""
        try:
            img_bytes = base64.b64decode(base64_str)
            img = Image.open(io.BytesIO(img_bytes))
            return img.convert("RGBA")
        except Exception as e:
            print(f"⚠️  Failed to decode base64 image: {e}")
            return None
    
    def _draw_title(self, draw: ImageDraw, title: str, layout: Dict):
        """Draw sale title."""
        font = self._get_font(layout["font_size"], bold=True)
        color = layout.get("color", "#FFFFFF")
        
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
        """Draw product with base64 image, name, and price."""
        
        # Load product image from base64
        if poster_product.product_image_base64:
            try:
                product_img = self._load_image_from_base64(
                    poster_product.product_image_base64
                )
                
                if product_img:
                    # Resize to fit layout
                    product_img = product_img.resize(
                        (layout["width"], layout["height"]),
                        Image.Resampling.LANCZOS
                    )
                    # Paste onto poster
                    img.paste(product_img, (layout["x"], layout["y"]), product_img)
            
            except Exception as e:
                print(f"⚠️  Failed to load product image: {e}")
        
        # Draw product name below image
        name_y = layout["y"] + layout["height"] + 10
        font = self._get_font(24, bold=False)
        draw.text(
            (layout["x"], name_y),
            poster_product.german_name,
            font=font,
            fill="#FFFFFF"
        )
        
        # Draw price
        price_y = name_y + 30
        price_font = self._get_font(32, bold=True)
        price_text = f"€{float(poster_product.sale_price):.2f}"
        
        draw.text(
            (layout["x"], price_y),
            price_text,
            font=price_font,
            fill="#FFD700"
        )
        
        # Draw old price if available
        if poster_product.old_price:
            old_price_text = f"€{float(poster_product.old_price):.2f}"
            old_price_font = self._get_font(20, bold=False)
            
            x_pos = layout["x"] + 150
            draw.text(
                (x_pos, price_y + 5),
                old_price_text,
                font=old_price_font,
                fill="#AAAAAA"
            )
            
            # Strikethrough line
            try:
                bbox = draw.textbbox((x_pos, price_y), old_price_text, font=old_price_font)
                draw.line(
                    [(bbox[0], bbox[1] + 10), (bbox[2], bbox[1] + 10)],
                    fill="#AAAAAA",
                    width=2
                )
            except:
                pass
    
    def _draw_logo(self, img: Image.Image, logo_asset: Asset, layout: Dict):
        """Draw store logo."""
        try:
            logo_img = self._load_image_from_asset(logo_asset)
            logo_img.thumbnail(
                (layout["max_width"], layout["max_height"]),
                Image.Resampling.LANCZOS
            )
            img.paste(logo_img, (layout["x"], layout["y"]), logo_img)
        except Exception as e:
            print(f"⚠️  Failed to load logo: {e}")
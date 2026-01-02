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
        print(f"🎨 Template layout has {len(layout.get('products', []))} product slots")
        print(f"📦 Poster has {len(poster.products)} products to render")

        # Draw title
        self._draw_title(draw, poster.sale_title, layout["title"])

        # Draw products
        for idx, poster_product in enumerate(sorted(poster.products, key=lambda p: p.display_order)):
            print(f"  📍 Rendering product {idx + 1}: {poster_product.german_name}")
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
            img = Image.open(path)

            # Convert to RGB mode for proper rendering (remove alpha channel)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            else:
                img = img.convert("RGB")

            # Auto-upscale old backgrounds to A3 if needed (backward compatibility)
            if img.width < 3508 or img.height < 4961:
                original_size = f"{img.width}x{img.height}"
                img = img.resize((3508, 4961), Image.Resampling.LANCZOS)
                print(f"⚠️  Upscaled background from {original_size} to 3508x4961 for A3 compatibility")

            return img
        else:
            raise NotImplementedError("S3 loading not implemented")
    
    def _load_image_from_base64(self, base64_str: str) -> Image.Image:
        """Load image from base64 string."""
        try:
            img_bytes = base64.b64decode(base64_str)
            img = Image.open(io.BytesIO(img_bytes))
            # Convert to RGB for consistency (product images are JPEGs, should be RGB)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            return img
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
        print(f"    Drawing product: {poster_product.german_name} at ({layout['x']}, {layout['y']})")

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
                    # Paste onto poster (no mask needed for RGB images)
                    img.paste(product_img, (layout["x"], layout["y"]))
                    print(f"    ✅ Product image pasted at ({layout['x']}, {layout['y']}) with size {layout['width']}x{layout['height']}")
                else:
                    print(f"⚠️  Product image is None for: {poster_product.artikel_nr}")

            except Exception as e:
                print(f"⚠️  Failed to load product image for {poster_product.artikel_nr}: {e}")
        else:
            print(f"⚠️  No base64 image data for product: {poster_product.artikel_nr}")
        
        # Draw product name below image (scaled for A3) with stroke for visibility
        name_y = layout["y"] + layout["height"] + 30
        font = self._get_font(72, bold=False)

        # Draw stroke (black outline) for text visibility on any background
        stroke_width = 3
        for offset_x in range(-stroke_width, stroke_width + 1):
            for offset_y in range(-stroke_width, stroke_width + 1):
                if offset_x != 0 or offset_y != 0:
                    draw.text(
                        (layout["x"] + offset_x, name_y + offset_y),
                        poster_product.german_name,
                        font=font,
                        fill="#000000"
                    )

        # Draw main text (white)
        draw.text(
            (layout["x"], name_y),
            poster_product.german_name,
            font=font,
            fill="#FFFFFF"
        )

        # Draw price (scaled for A3) with stroke for visibility
        price_y = name_y + 90
        price_font = self._get_font(96, bold=True)
        price_text = f"€{float(poster_product.sale_price):.2f}"

        # Draw stroke (black outline) for price
        for offset_x in range(-stroke_width, stroke_width + 1):
            for offset_y in range(-stroke_width, stroke_width + 1):
                if offset_x != 0 or offset_y != 0:
                    draw.text(
                        (layout["x"] + offset_x, price_y + offset_y),
                        price_text,
                        font=price_font,
                        fill="#000000"
                    )

        # Draw main price (gold)
        draw.text(
            (layout["x"], price_y),
            price_text,
            font=price_font,
            fill="#FFD700"
        )

        # Draw old price if available (scaled for A3) with stroke
        if poster_product.old_price:
            old_price_text = f"€{float(poster_product.old_price):.2f}"
            old_price_font = self._get_font(60, bold=False)

            x_pos = layout["x"] + 450

            # Draw stroke for old price
            for offset_x in range(-stroke_width, stroke_width + 1):
                for offset_y in range(-stroke_width, stroke_width + 1):
                    if offset_x != 0 or offset_y != 0:
                        draw.text(
                            (x_pos + offset_x, price_y + 15 + offset_y),
                            old_price_text,
                            font=old_price_font,
                            fill="#000000"
                        )

            # Draw main old price (gray)
            draw.text(
                (x_pos, price_y + 15),
                old_price_text,
                font=old_price_font,
                fill="#AAAAAA"
            )

            # Strikethrough line
            try:
                bbox = draw.textbbox((x_pos, price_y), old_price_text, font=old_price_font)
                draw.line(
                    [(bbox[0], bbox[1] + 30), (bbox[2], bbox[1] + 30)],
                    fill="#FF0000",  # Red strikethrough for better visibility
                    width=6
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
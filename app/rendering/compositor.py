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
    
    A3_WIDTH_PX = 3508
    A3_HEIGHT_PX = 4961

    def __init__(self):
        self.default_font_path = settings.EXPORT_FONT_PATH
        self.bold_font_path = settings.EXPORT_FONT_BOLD_PATH

        # Font fallback paths for Mac (including CJK support)
        self.font_fallbacks = [
            (self.default_font_path, self.bold_font_path),
            # macOS fonts with Chinese character support
            ("/System/Library/Fonts/Hiragino Sans GB.ttc",
             "/System/Library/Fonts/Hiragino Sans GB.ttc"),
            ("/System/Library/Fonts/STHeiti Light.ttc",
             "/System/Library/Fonts/STHeiti Medium.ttc"),
            ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
             "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
            # Standard fallbacks
            ("/System/Library/Fonts/Supplemental/Arial.ttf",
             "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
            ("/System/Library/Fonts/Helvetica.ttc",
             "/System/Library/Fonts/Helvetica.ttc"),
            ("./fonts/Arial.ttf", "./fonts/Arial-Bold.ttf"),
        ]
    
    def _get_font(self, size: int, bold: bool = False, require_cjk: bool = False) -> ImageFont.FreeTypeFont:
        """Get font with fallback support.

        Args:
            size: Font size in pixels
            bold: Use bold variant if available
            require_cjk: If True, prefer fonts with CJK (Chinese/Japanese/Korean) support
        """
        # If CJK support is required, prioritize CJK-compatible fonts
        if require_cjk:
            cjk_fonts = [
                # macOS system fonts with Chinese character support
                ("/System/Library/Fonts/Hiragino Sans GB.ttc",
                 "/System/Library/Fonts/Hiragino Sans GB.ttc"),
                ("/System/Library/Fonts/STHeiti Light.ttc",
                 "/System/Library/Fonts/STHeiti Medium.ttc"),
                ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
                 "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
            ]

            for regular_path, bold_path in cjk_fonts:
                font_path = bold_path if bold else regular_path
                if os.path.exists(font_path):
                    try:
                        return ImageFont.truetype(font_path, size)
                    except Exception:
                        continue

        # Try all fallback fonts
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
        
        # Load background image
        bg_img = self._load_image_from_asset(background_image)

        # Create explicit A3 canvas
        canvas = Image.new("RGBA",(self.A3_WIDTH_PX, self.A3_HEIGHT_PX),(0, 0, 0, 255))

        # Resize background to exactly fill A3 canvas
        bg_img = bg_img.resize((self.A3_WIDTH_PX, self.A3_HEIGHT_PX),Image.Resampling.LANCZOS)

        # Paste background onto canvas
        canvas.paste(bg_img, (0, 0))

        # Create drawing context
        draw = ImageDraw.Draw(canvas)
        
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
                    canvas,
                    draw,
                    poster_product,
                    product_layout
                )
        
        # Draw logo if available
        if poster.store.settings and poster.store.settings.logo:
            self._draw_logo(canvas, poster.store.settings.logo, layout["logo"])
        
        # Convert to bytes
        output = io.BytesIO()
        canvas.save(output, format=format, quality=95)
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

    def _draw_text_with_stroke(
        self,
        draw: ImageDraw,
        x: int,
        y: int,
        text: str,
        font_size: int,
        color: str,
        bold: bool = False,
        stroke_width: int = 3,
        stroke_color: str = "#000000",
        require_cjk: bool = False
    ):
        """Draw text with stroke outline for visibility."""
        font = self._get_font(font_size, bold=bold, require_cjk=require_cjk)

        # Draw stroke (outline)
        for offset_x in range(-stroke_width, stroke_width + 1):
            for offset_y in range(-stroke_width, stroke_width + 1):
                if offset_x != 0 or offset_y != 0:
                    draw.text(
                        (x + offset_x, y + offset_y),
                        text,
                        font=font,
                        fill=stroke_color
                    )

        # Draw main text
        draw.text(
            (x, y),
            text,
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

        # Start text rendering 30px below product image
        text_start_y = layout["y"] + layout["height"] + 30

        # Draw artikel_nr (first line - always present)
        artikel_y = text_start_y
        self._draw_text_with_stroke(
            draw,
            layout["x"],
            artikel_y,
            poster_product.artikel_nr,
            font_size=60,
            color="#CCCCCC"  # Light gray for metadata
        )
        print(f"    ✏️  Drew artikel_nr: {poster_product.artikel_nr}")

        # Draw chinese_name (second line - if present)
        chinese_y = artikel_y + 75  # 60px font + 15px gap
        if poster_product.chinese_name:
            self._draw_text_with_stroke(
                draw,
                layout["x"],
                chinese_y,
                poster_product.chinese_name,
                font_size=60,
                color="#CCCCCC",
                require_cjk=True  # Use CJK-compatible font
            )
            print(f"    ✏️  Drew chinese_name: {poster_product.chinese_name}")
        else:
            print(f"    ⚠️  No chinese_name for product")

        # Draw weight (third line - if present)
        weight_y = chinese_y + 75
        if poster_product.weight:
            self._draw_text_with_stroke(
                draw,
                layout["x"],
                weight_y,
                str(poster_product.weight),
                font_size=60,
                color="#CCCCCC"
            )
            print(f"    ✏️  Drew weight: {poster_product.weight}")
        else:
            print(f"    ⚠️  No weight for product")

        # Draw german_name (fourth line - larger gap for visual separation)
        name_y = weight_y + 90
        self._draw_text_with_stroke(
            draw,
            layout["x"],
            name_y,
            poster_product.german_name,
            font_size=72,
            color="#FFFFFF"
        )
        print(f"    ✏️  Drew german_name: {poster_product.german_name}")

        # Draw sale price (scaled for A3)
        price_y = name_y + 90
        price_text = f"€{float(poster_product.sale_price):.2f}"
        self._draw_text_with_stroke(
            draw,
            layout["x"],
            price_y,
            price_text,
            font_size=96,
            color="#FFD700",  # Gold
            bold=True
        )
        print(f"    ✏️  Drew sale_price: {price_text}")

        # Draw old price if available (scaled for A3)
        if poster_product.old_price:
            old_price_text = f"€{float(poster_product.old_price):.2f}"
            x_pos = layout["x"] + 450

            self._draw_text_with_stroke(
                draw,
                x_pos,
                price_y + 15,
                old_price_text,
                font_size=60,
                color="#AAAAAA"  # Gray
            )
            print(f"    ✏️  Drew old_price: {old_price_text}")

            # Strikethrough line
            try:
                old_price_font = self._get_font(60, bold=False)
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

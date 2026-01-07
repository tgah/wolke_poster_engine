#!/usr/bin/env python
"""Update poster templates to A3 portrait dimensions."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.poster import PosterTemplate


def update_templates():
    """Update existing templates to A3 portrait dimensions (3508 × 4961 pixels at 300 DPI)."""
    db = SessionLocal()

    try:
        # Update two_product template
        two_product = db.query(PosterTemplate).filter(
            PosterTemplate.key == "two_product"
        ).first()

        if two_product:
            two_product.description = "A3 portrait layout for 2 products in lower 40%"
            # Canvas: 3508 × 4961 pixels
            # Lower 40% starts at: 4961 × 0.6 = 2976px
            # Product images positioned in lower 40% with all labels fitting
            two_product.layout_json = {
                "background": {"x": 0, "y": 0, "width": 3508, "height": 4961},
                "title": {
                    "x": 150, "y": 150,
                    "font_size": 140,
                    "color": "#FFFFFF",
                    "max_width": 3208
                },
                "products": [
                    "products": [
                        {"x": 444, "y": 2600, "width": 1120, "height": 1120},
                        {"x": 1944, "y": 2600, "width": 1120, "height": 1120}
                    ]
                ],
                "logo": {"x": 3008, "y": 4511, "max_width": 400, "max_height": 300}
            }
            print(f"✅ Updated template: {two_product.name} (products in lower 40%)")
        else:
            print("⚠️  Two product template not found")

        # Update three_product template
        three_product = db.query(PosterTemplate).filter(
            PosterTemplate.key == "three_product"
        ).first()

        if three_product:
            three_product.description = "A3 portrait layout for 3 products in lower 40%"
            # Canvas: 3508 × 4961 pixels
            # Lower 40% starts at: 4961 × 0.6 = 2976px
            # 3 products side by side: 150px margins, 100px gaps, 1000×1000 product images
            # Positions: x = 154, 1254, 2354 (150 + 1000 + 100 + 1000 + 100 + 1000 + 154 = 3508)
            three_product.layout_json = {
                "background": {"x": 0, "y": 0, "width": 3508, "height": 4961},
                "title": {
                    "x": 150, "y": 150,
                    "font_size": 140,
                    "color": "#FFFFFF",
                    "max_width": 3208
                },
                "products": [
                    {"x": 154, "y": 3100, "width": 1000, "height": 1000},
                    {"x": 1254, "y": 3100, "width": 1000, "height": 1000},
                    {"x": 2354, "y": 3100, "width": 1000, "height": 1000}
                ],
                "logo": {"x": 3008, "y": 4511, "max_width": 400, "max_height": 300}
            }
            print(f"✅ Updated template: {three_product.name} (products in lower 40%)")
        else:
            print("⚠️  Three product template not found")

        db.commit()
        print("\n✅ Templates updated successfully to A3 portrait dimensions!")
        print("   Canvas: 3508 × 4961 pixels (297mm × 420mm at 300 DPI)")
        print("   Products positioned in lower 40% of canvas")
        print("   Two-product: 1400×1400px images at y=3000")
        print("   Three-product: 1000×1000px images at y=3100")

    except Exception as e:
        print(f"❌ Error updating templates: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    update_templates()

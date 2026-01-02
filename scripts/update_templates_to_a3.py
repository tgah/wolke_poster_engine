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
            two_product.description = "A3 portrait layout for 2 products"
            two_product.layout_json = {
                "background": {"x": 0, "y": 0, "width": 3508, "height": 4961},
                "title": {
                    "x": 150, "y": 150,
                    "font_size": 140,
                    "color": "#FFFFFF",
                    "max_width": 3208
                },
                "products": [
                    {"x": 304, "y": 1200, "width": 1400, "height": 1400},
                    {"x": 1804, "y": 1200, "width": 1400, "height": 1400}
                ],
                "logo": {"x": 3008, "y": 4511, "max_width": 400, "max_height": 300}
            }
            print(f"✅ Updated template: {two_product.name}")
        else:
            print("⚠️  Two product template not found")

        # Update three_product template
        three_product = db.query(PosterTemplate).filter(
            PosterTemplate.key == "three_product"
        ).first()

        if three_product:
            three_product.description = "A3 portrait layout for 3 products"
            three_product.layout_json = {
                "background": {"x": 0, "y": 0, "width": 3508, "height": 4961},
                "title": {
                    "x": 150, "y": 150,
                    "font_size": 140,
                    "color": "#FFFFFF",
                    "max_width": 3208
                },
                "products": [
                    {"x": 154, "y": 800, "width": 1050, "height": 1050},
                    {"x": 1229, "y": 800, "width": 1050, "height": 1050},
                    {"x": 2304, "y": 800, "width": 1050, "height": 1050}
                ],
                "logo": {"x": 3008, "y": 4511, "max_width": 400, "max_height": 300}
            }
            print(f"✅ Updated template: {three_product.name}")
        else:
            print("⚠️  Three product template not found")

        db.commit()
        print("\n✅ Templates updated successfully to A3 portrait dimensions!")
        print("   Canvas: 3508 × 4961 pixels (297mm × 420mm at 300 DPI)")

    except Exception as e:
        print(f"❌ Error updating templates: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    update_templates()

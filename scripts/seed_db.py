#!/usr/bin/env python
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.company import Company
from app.models.store import Store
from app.models.user import User, UserRole
from app.models.poster import PosterTemplate
from app.utils.security import hash_password
import uuid

def seed_database():
    db = SessionLocal()
    
    try:
        # Check if already seeded
        existing_company = db.query(Company).first()
        if existing_company:
            print("Database already seeded. Skipping.")
            return
        
        # Create default company
        company = Company(
            id=uuid.uuid4(),
            name="AsRopa Wholesale"
        )
        db.add(company)
        db.flush()
        
        print(f"Created company: {company.name} (ID: {company.id})")
        
        # Create default store
        store = Store(
            id=uuid.uuid4(),
            company_id=company.id,
            name="Main Store",
            slug="main-store"
        )
        db.add(store)
        db.flush()
        
        print(f"Created store: {store.name} (ID: {store.id})")
        
        # Create test user
        user = User(
            id=uuid.uuid4(),
            company_id=company.id,
            store_id=store.id,
            email="admin@asropa.com",
            password_hash=hash_password("admin123"),
            role=UserRole.STORE_USER,
            is_active=True
        )
        db.add(user)
        db.flush()
        
        print(f"Created user: {user.email} (password: admin123)")
        
        # Create poster templates (A3 Portrait: 3508 × 4961 pixels at 300 DPI)
        two_product_template = PosterTemplate(
            id=uuid.uuid4(),
            key="two_product",
            name="Two Product Layout",
            description="A3 portrait layout for 2 products",
            max_products=2,
            layout_json={
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
        )
        db.add(two_product_template)

        three_product_template = PosterTemplate(
            id=uuid.uuid4(),
            key="three_product",
            name="Three Product Layout",
            description="A3 portrait layout for 3 products",
            max_products=3,
            layout_json={
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
        )
        db.add(three_product_template)
        
        db.commit()
        
        print("\\n✅ Database seeded successfully!")
        print(f"\\nCompany ID: {company.id}")
        print(f"Store ID: {store.id}")
        print(f"Test User: {user.email} / admin123")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
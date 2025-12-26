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
        
        # Create poster templates
        two_product_template = PosterTemplate(
            id=uuid.uuid4(),
            key="two_product",
            name="Two Product Layout",
            description="Standard layout for 2 products",
            max_products=2,
            layout_json={
                "background": {"x": 0, "y": 0, "width": 1024, "height": 1024},
                "title": {
                    "x": 50, "y": 50, 
                    "font_size": 48, 
                    "color": "#FFFFFF", 
                    "max_width": 924
                },
                "products": [
                    {"x": 100, "y": 300, "width": 400, "height": 400},
                    {"x": 524, "y": 300, "width": 400, "height": 400}
                ],
                "logo": {"x": 850, "y": 900, "max_width": 150, "max_height": 100}
            }
        )
        db.add(two_product_template)
        
        three_product_template = PosterTemplate(
            id=uuid.uuid4(),
            key="three_product",
            name="Three Product Layout",
            description="Standard layout for 3 products",
            max_products=3,
            layout_json={
                "background": {"x": 0, "y": 0, "width": 1024, "height": 1024},
                "title": {
                    "x": 50, "y": 50,
                    "font_size": 48,
                    "color": "#FFFFFF",
                    "max_width": 924
                },
                "products": [
                    {"x": 50, "y": 200, "width": 300, "height": 300},
                    {"x": 362, "y": 200, "width": 300, "height": 300},
                    {"x": 674, "y": 200, "width": 300, "height": 300}
                ],
                "logo": {"x": 850, "y": 900, "max_width": 150, "max_height": 100}
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
from app.database import SessionLocal
from app.models.user import User
from app.models.company import Company
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

db = SessionLocal()

try:
    # Create company
    company = Company(name="ASROPA")
    db.add(company)
    db.commit()
    db.refresh(company)
    print(f"Created company: {company.name} (ID: {company.id})")

    # Create admin user
    user = User(
        email="admin@asropa.com",
        full_name="Admin User",
        hashed_password=pwd_context.hash("admin123"),
        role="admin",
        company_id=company.id,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"Created user: {user.email} (ID: {user.id})")
    print("Done! You can now login.")
    
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()

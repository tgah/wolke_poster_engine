#!/usr/bin/env python
'''Run database migration manually'''
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import engine
from sqlalchemy import text

def run_migration():
    with engine.connect() as conn:
        # Execute migration
        conn.execute(text('''
            ALTER TABLE poster_products
            ADD COLUMN IF NOT EXISTS artikel_nr VARCHAR(100),
            ADD COLUMN IF NOT EXISTS german_name VARCHAR(500),
            ADD COLUMN IF NOT EXISTS chinese_name VARCHAR(500),
            ADD COLUMN IF NOT EXISTS weight VARCHAR(100),
            ADD COLUMN IF NOT EXISTS product_image_base64 TEXT;
        '''))
        
        conn.execute(text('''
            ALTER TABLE poster_products
            ALTER COLUMN product_id DROP NOT NULL;
        '''))
        
        conn.execute(text('''
            ALTER TABLE poster_products
            DROP CONSTRAINT IF EXISTS poster_products_product_id_fkey;
        '''))
        
        conn.execute(text('''
            DROP TABLE IF EXISTS product_imports CASCADE;
            DROP TABLE IF EXISTS products CASCADE;
        '''))
        
        conn.execute(text('''
            CREATE INDEX IF NOT EXISTS idx_poster_products_artikel_nr 
            ON poster_products(artikel_nr);
        '''))
        
        conn.commit()
        
    print("✅ Migration completed successfully!")

if __name__ == "__main__":
    response = input("⚠️  This will drop products and product_imports tables. Continue? (yes/no): ")
    if response.lower() == "yes":
        run_migration()
    else:
        print("Migration cancelled.")
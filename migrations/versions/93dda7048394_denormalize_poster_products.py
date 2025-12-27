"""denormalize_poster_products

Revision ID: 93dda7048394
Revises: 
Create Date: 2025-12-27 00:59:44.565040

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '93dda7048394'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("""
        ALTER TABLE poster_products
        ADD COLUMN IF NOT EXISTS artikel_nr VARCHAR(100),
        ADD COLUMN IF NOT EXISTS german_name VARCHAR(500),
        ADD COLUMN IF NOT EXISTS chinese_name VARCHAR(500),
        ADD COLUMN IF NOT EXISTS weight VARCHAR(100),
        ADD COLUMN IF NOT EXISTS product_image_base64 TEXT;
    """)

    op.execute("""
        ALTER TABLE poster_products
        ALTER COLUMN product_id DROP NOT NULL;
    """)

    op.execute("""
        ALTER TABLE poster_products
        DROP CONSTRAINT IF EXISTS poster_products_product_id_fkey;
    """)

    op.execute("""
        DROP TABLE IF EXISTS product_imports CASCADE;
        DROP TABLE IF EXISTS products CASCADE;
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_poster_products_artikel_nr 
        ON poster_products(artikel_nr);
    """)


def downgrade():
    op.execute("""
        ALTER TABLE poster_products
        DROP COLUMN IF EXISTS artikel_nr,
        DROP COLUMN IF EXISTS german_name,
        DROP COLUMN IF EXISTS chinese_name,
        DROP COLUMN IF EXISTS weight,
        DROP COLUMN IF EXISTS product_image_base64;
    """)

    op.execute("""
        ALTER TABLE poster_products
        ALTER COLUMN product_id SET NOT NULL;
    """)

    op.execute("""
        CREATE TABLE products (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID NOT NULL REFERENCES companies(id),
            artikel_nr VARCHAR(100) NOT NULL,
            chinese_name VARCHAR(500),
            german_name VARCHAR(500) NOT NULL,
            weight VARCHAR(100),
            old_price NUMERIC(10, 2),
            new_price NUMERIC(10, 2) NOT NULL,
            image_path VARCHAR(500),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,
            CONSTRAINT uq_company_artikel UNIQUE (company_id, artikel_nr)
        );
    """)

    op.execute("""
        CREATE TABLE product_imports (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID NOT NULL REFERENCES companies(id),
            uploaded_by_user_id UUID NOT NULL REFERENCES users(id),
            filename VARCHAR(500) NOT NULL,
            status VARCHAR(50) NOT NULL,
            rows_processed INTEGER DEFAULT 0,
            rows_succeeded INTEGER DEFAULT 0,
            rows_failed INTEGER DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            completed_at TIMESTAMP WITH TIME ZONE
        );
    """)


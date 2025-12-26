### Running the Application

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start API server
uvicorn app.main:app --reload

# Start Celery worker
celery -A app.workers.celery_app worker --loglevel=info

--------------------------------------------------------------

### Migration Commands

# Initialize Alembic
alembic init migrations

# Create migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

--------------------------------------------------------------

# Poster Generator Backend

AI-assisted promotional poster generation system for grocery stores.

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- (Optional) NVIDIA GPU for Stable Diffusion

### Installation

1. Clone and setup:
```bash
git clone <repo>
cd poster-backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Setup database:
```bash
# Start PostgreSQL and Redis (or use Docker)
docker-compose up -d postgres redis

# Run migrations
alembic upgrade head

# Seed default data
python scripts/seed_db.py
```

4. Download fonts:
```bash
mkdir fonts
# Download Arial.ttf and Arial-Bold.ttf to fonts/
```

5. Run application:
```bash
# Terminal 1: API Server
uvicorn app.main:app --reload

# Terminal 2: Celery Worker
celery -A app.workers.celery_app worker --loglevel=info
```

6. Access API docs:
```
http://localhost:8000/docs
```

## Using Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

## API Usage

See documentation at `/docs` or `/redoc`

## Testing

```bash
pytest tests/
```
127.0.0.1
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@asropa.com","password":"admin123"}'


TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiMTRkODllMy1hMGY3LTQyZDItYTg1Zi1jYjI4ZmRmMTRiNjAiLCJlbWFpbCI6ImFkbWluQGFzcm9wYS5jb20iLCJyb2xlIjoic3RvcmVfdXNlciIsImNvbXBhbnlfaWQiOiJlMDIxYzAzZC1kN2YxLTRjNDAtOTA5Mi1lY2M0OTRmZjcwNGYiLCJleHAiOjE3NjY1MTg4OTAsImlhdCI6MTc2NjQzMjQ5MH0.RhQM8-lcY9AHcIGEWSfg5rEA8AuNUunHJHgCLlYc1fs"

{"id":"b14d89e3-a0f7-42d2-a85f-cb28fdf14b60","email":"admin@asropa.com","role":"store_user","company_id":"e021c03d-d7f1-4c40-9092-ecc494ff704f","store_id":"6444c66d-fc91-44b9-a9a4-6f7ef4246200","twofa_enabled":false,"created_at":"2025-12-23T01:10:25.589480+05:30","last_login_at":"2025-12-22T20:01:03.256575+05:30"}%         

[
    {"artikel_nr":"A001","chinese_name":"酱油","german_name":"Sojasauce","weight":"500ml","old_price":"3.99","new_price":"2.99","image_path":null,"id":"47d3623a-1bb0-48b7-9c69-789640cf53c1","company_id":"e021c03d-d7f1-4c40-9092-ecc494ff704f","created_at":"2025-12-23T01:13:42.534936+05:30","updated_at":null},
    {"artikel_nr":"A002","chinese_name":"米饭","german_name":"Reis","weight":"1kg","old_price":"5.49","new_price":"4.49","image_path":null,"id":"ddb4e371-772f-42f7-a377-58eff4053e66","company_id":"e021c03d-d7f1-4c40-9092-ecc494ff704f","created_at":"2025-12-23T01:13:42.534936+05:30","updated_at":null},
    {"artikel_nr":"A003","chinese_name":"面条","german_name":"Nudeln","weight":"500g","old_price":"2.99","new_price":"1.99","image_path":null,"id":"f9cd809c-8a0f-4f31-8eb7-fec8d27b4ddd","company_id":"e021c03d-d7f1-4c40-9092-ecc494ff704f","created_at":"2025-12-23T01:13:42.534936+05:30","updated_at":null}
]%


# First, get product IDs and store ID from previous responses
PRODUCT_ID_1="47d3623a-1bb0-48b7-9c69-789640cf53c1"
PRODUCT_ID_2="ddb4e371-772f-42f7-a377-58eff4053e66"
STORE_ID="6444c66d-fc91-44b9-a9a4-6f7ef4246200"

curl -X POST http://127.0.0.1:8000/posters \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "store_id": "'"$STORE_ID"'",
    "template_key": "two_product",
    "theme_text": "Christmas special, cozy warm colors, minimal snowflakes, blue gradient background, festive winter atmosphere",
    "sale_title": "Weihnachtsangebot",
    "products": [
      {
        "product_id": "'"$PRODUCT_ID_1"'",
        "sale_price": 2.99
      },
      {
        "product_id": "'"$PRODUCT_ID_2"'",
        "sale_price": 1.99
      }
    ],
    "use_uploaded_background": false
  }'

curl "http://127.0.0.1:8000/posters/$POSTER_ID" \
  -H "Authorization: Bearer $TOKEN"

  curl -X POST "http://127.0.0.1:8000/posters/$POSTER_ID/export" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "format": "png",
    "resolution": "digital"
  }'

  curl "http://127.0.0.1:8000/assets/poster_export/poster_export_20251223_065707_e8044bb4f0704687.png" \
  -H "Authorization: Bearer $TOKEN" \
  -o my_poster.png
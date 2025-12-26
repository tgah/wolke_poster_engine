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

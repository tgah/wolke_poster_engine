SHELL := /bin/bash

run-redis:
	@/opt/homebrew/bin/redis-server

run-all:
	@/opt/homebrew/bin/redis-server &
	venv/bin/python -m celery -A app.workers.celery_app worker --loglevel=info &
	@venv/bin/python -m uvicorn app.main:app --reload --port 8000

run-celery:
	@venv/bin/python -m celery -A app.workers.celery_app worker --loglevel=info
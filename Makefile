.PHONY: help install dev test lint format docker-up docker-down push

help:
	@echo "MEMBRA CompanyOS — Available Commands"
	@echo ""
	@echo "  make install      Install backend dependencies"
	@echo "  make dev          Start backend in development mode"
	@echo "  make test         Run test suite"
	@echo "  make lint         Run linting (black, flake8, mypy)"
	@echo "  make format       Auto-format code with black"
	@echo "  make docker-up    Start Docker Compose stack"
	@echo "  make docker-down  Stop Docker Compose stack"
	@echo "  make push         Push to GitHub (requires token)"

install:
	cd backend && pip install -r requirements.txt

dev:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	cd backend && pytest tests/ -v --cov=app --cov-report=term-missing

lint:
	cd backend && black --check app/ && flake8 app/ --max-line-length=120 && mypy app/ --ignore-missing-imports

format:
	cd backend && black app/

docker-up:
	docker-compose up -d --build

docker-down:
	docker-compose down

push:
	@echo "Run: cd /Users/alep/membra-companyos && git push origin main"
	@echo "See PUSH_GUIDE.md for token setup instructions"

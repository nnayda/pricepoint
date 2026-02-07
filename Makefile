.PHONY: up up-infra up-all down lint test test-unit test-integration test-docker test-all test-coverage migrate migration build frontend-install frontend-lint frontend-test frontend-test-coverage

# --- Docker Compose -----------------------------------------------------------

up: ## Start app services only (api, frontend, mlflow)
	docker compose up -d

up-infra: ## Start app services + core infrastructure (postgres, minio, valkey) - no Airflow
	docker compose --profile infra up -d

up-all: ## Start everything including bundled Airflow + its database
	docker compose --profile infra --profile airflow up -d

down: ## Stop all services
	docker compose --profile infra --profile airflow down

# --- Python -------------------------------------------------------------------

lint: ## Run ruff linter and formatter check
	uv run ruff check src/ dags/ tests/
	uv run ruff format --check src/ dags/ tests/

test: ## Run pytest
	uv run pytest

test-unit: ## Run unit tests only
	uv run pytest tests/unit/ -m unit -v

test-integration: ## Run integration tests only (requires Docker for testcontainers)
	uv run pytest tests/integration/ -m integration -v

test-docker: ## Run Docker build smoke tests
	uv run pytest tests/docker/ -m docker -v

test-all: ## Run all tests
	uv run pytest -v

test-coverage: ## Run tests with coverage report
	uv run pytest --cov=src/pricepoint --cov-report=html --cov-report=term -v

migrate: ## Run alembic migrations
	uv run alembic upgrade head

migration: ## Create a new alembic migration (usage: make migration MSG="add foo table")
	uv run alembic revision --autogenerate -m "$(MSG)"

# --- Docker Build -------------------------------------------------------------

build: ## Build all Docker images
	docker compose build

# --- Frontend -----------------------------------------------------------------

frontend-install: ## Install frontend dependencies
	cd frontend && npm install

frontend-lint: ## Run eslint and prettier check on frontend
	cd frontend && npm run lint && npm run format:check

frontend-test: ## Run frontend tests
	cd frontend && npm test

frontend-test-coverage: ## Run frontend tests with coverage
	cd frontend && npm run test:coverage

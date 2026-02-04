.PHONY: up up-all down lint test migrate migration build frontend-install frontend-lint

# --- Docker Compose -----------------------------------------------------------

up: ## Start app services (api, frontend, mlflow)
	docker compose up -d

up-all: ## Start app services + bundled infrastructure
	docker compose --profile infra up -d

down: ## Stop all services
	docker compose --profile infra down

# --- Python -------------------------------------------------------------------

lint: ## Run ruff linter and formatter check
	uv run ruff check src/ dags/ tests/
	uv run ruff format --check src/ dags/ tests/

test: ## Run pytest
	uv run pytest

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

# PricePoint

Residential home value forecasting system. Predicts property values by combining geospatial data (police incidents, schools, POIs), housing data (Redfin listings, county assessments), and economic indicators (FRED/mortgage rates) through an ML pipeline.

**Status:** Fully scaffolded. Infrastructure, API, frontend, and Airflow DAGs are wired up. Core business logic (data collectors, feature engineering, model training) are stubs raising `NotImplementedError`.

## Tech Stack

| Layer          | Technologies                                                    |
|----------------|-----------------------------------------------------------------|
| Backend        | Python 3.12, FastAPI, Uvicorn                                   |
| Database       | PostgreSQL + PostGIS, SQLAlchemy 2.0, GeoAlchemy2, Alembic      |
| Frontend       | React 18, TypeScript 5.5, Vite 5.3, Leaflet, Axios             |
| ML             | MLflow 2.14+ (tracking, model registry)                         |
| Orchestration  | Apache Airflow 2.9 (3 DAGs: collection -> features -> training) |
| Storage        | MinIO (S3-compatible)                                           |
| Infra          | Docker Compose, Kubernetes/Helm, GitLab CI/CD                   |
| Dev Tools      | uv (packages), Ruff (lint/format), mypy, pytest                 |

## Project Structure

```
src/pricepoint/
  api/              # FastAPI app, routes, schemas, dependencies
  config/           # Pydantic Settings (env-based configuration)
  db/               # SQLAlchemy models, engine, Alembic migrations
  data/
    geospatial/     # Police incidents, schools, nearby features, capital projects
    housing/        # Redfin listings, county assessments, property photos
    economic/       # Macroeconomic indicators (FRED)
  features/         # Feature engineering (geospatial, housing, economic, assembly)
  models/           # ML training, validation, evaluation, MLflow registry
frontend/           # React SPA (pages, components, hooks, services)
dags/               # Airflow DAGs + common task helpers
tests/
  unit/             # API and config tests (no external deps)
  integration/      # DB connectivity tests (skip if DB unavailable)
docker/             # Dockerfiles (api, frontend, mlflow, airflow)
helm/               # Kubernetes Helm chart with dev/prod values
```

## Commands

### Python

```sh
uv sync --frozen          # Install dependencies
make test                 # Run pytest
make lint                 # Ruff check + format check
uv run mypy src/          # Type checking
```

### Database

```sh
make migrate              # Apply migrations (alembic upgrade head)
make migration MSG="..."  # Generate new migration (autogenerate)
```

### Frontend

```sh
make frontend-install     # npm install
cd frontend && npm run dev       # Dev server (port 5173)
cd frontend && npm run build     # Production build
make frontend-lint               # ESLint + Prettier check
```

### Docker

```sh
make up                   # Start app services (api, frontend, mlflow)
make up-all               # Start with infrastructure (postgres, minio, airflow)
make down                 # Stop all services
make build                # Build all Docker images
```

## Additional Documentation

Check these files for detailed conventions when working in specific areas:

- [Architectural Patterns](.claude/docs/architectural_patterns.md) — dependency injection, API design, DB conventions, data pipeline interfaces, Airflow DAG structure, frontend patterns, and testing conventions with file:line references

# PricePoint

Residential home value forecasting system. Predicts property values by combining geospatial data (police incidents, schools, POIs), housing data (Redfin listings, county assessments), and economic indicators (FRED/mortgage rates) through an ML pipeline.

## Tech Stack

| Layer          | Technologies                                                    |
|----------------|-----------------------------------------------------------------|
| Backend        | Python 3.12, FastAPI, Uvicorn                                   |
| Database       | PostgreSQL + PostGIS, SQLAlchemy 2.0, GeoAlchemy2, Alembic      |
| Frontend       | React 18, TypeScript 5.5, Vite 5.3, Leaflet, Axios              |
| ML             | MLflow 2.14+ (tracking, model registry)                         |
| Orchestration  | Apache Airflow 2.9 (3 DAGs: collection -> features -> training) |
| Storage        | MinIO (S3-compatible)                                           |
| Infra          | Docker Compose, Kubernetes/Helm, GitLab CI/CD                   |
| Dev Tools      | uv (packages), Ruff (lint/format), mypy, pytest                 |

## Workflow
- Run `uv sync` first to ensure the python environment is the same
- Use `uv add` to install python dependencies that are not installed
- Be sure to typecheck when you're done making a series of code changes
- Ensure to run linting and tests when done, and fix the code to ensure all tests pass. Address the route issues and don't ignore errors.

## Commands

### Python

```sh
uv sync --frozen          # Install dependencies
make test                 # Run pytest
make lint                 # Ruff check + format check
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
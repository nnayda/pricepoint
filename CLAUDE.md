# PricePoint

Residential home search tool system. Allows for viewing property data and important metrics to evaluate when considering to buy a property. The key feature of this app is the home value prediction system. Predicts property values by combining geospatial data (police incidents, schools, POIs), housing data (Redfin listings, county assessments), and economic indicators (FRED/mortgage rates) through an ML pipeline.

## Tech Stack

| Layer          | Technologies                                                    |
|----------------|-----------------------------------------------------------------|
| Backend        | Python 3.12, FastAPI, Uvicorn                                   |
| Database       | PostgreSQL + PostGIS, SQLAlchemy 2.0, GeoAlchemy2, Alembic      |
| Frontend       | React 18, TypeScript 5.5, Vite 5.3, Leaflet, Axios              |
| ML             | MLflow 2.14+ (tracking, model registry)                         |
| Orchestration  | Apache Airflow 2.9 (3 DAGs: collection -> features -> training) |
| Storage        | MinIO (S3-compatible), Valkey (Redis-compatible cache)           |
| Infra          | Docker Compose, Kubernetes/Helm, GitLab CI/CD                   |
| Dev Tools      | uv (packages), Ruff (lint/format), mypy, pytest                 |

## Architecture

```
src/pricepoint/
├── api/           # FastAPI routes, schemas, dependencies
├── config/        # Pydantic Settings (env-driven)
├── db/            # SQLAlchemy models, engine, Alembic migrations
├── data/          # Data collectors (geospatial, housing, economic)
├── features/      # Feature engineering (assembly, geo, housing, econ)
└── models/        # ML training, evaluation, validation, registry
frontend/src/
├── components/    # React components (co-located __tests__/)
├── hooks/         # Custom React hooks
├── pages/         # LandingPage, ResultsPage, ForecastPage, SettingsPage
├── services/      # API client (Axios) + service modules
└── types/         # TypeScript type definitions
dags/              # Airflow DAGs (collection, features, training, TIGER)
tests/             # Backend tests (unit/, integration/, docker/)
```

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
make test-unit            # Unit tests only
make test-integration     # Integration tests only
make test-coverage        # Tests with HTML coverage report
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
make frontend-test               # Run vitest
make frontend-test-coverage      # Vitest with coverage
```

### Docker

```sh
make up                   # Start app services (api, frontend, mlflow)
make up-all               # Start with infrastructure (postgres, minio, airflow)
make down                 # Stop all services
make build                # Build all Docker images
```

## Environment

Copy `.env.example` to `.env`. Key variables:
- `DATABASE_URL` — PostgreSQL + PostGIS connection string
- `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET` — MinIO/S3
- `MLFLOW_TRACKING_URI` — MLflow server
- `VALKEY_URL` — Redis-compatible cache (optional)

## Gotchas

- **Airflow deps:** Airflow is installed separately in its Dockerfile to avoid SQLAlchemy version conflicts — don't add it to `pyproject.toml`
- **Docker profiles:** `make up` starts app services only; infrastructure (Postgres, MinIO, Airflow, Valkey) requires `make up-all` (uses `--profile infra`)
- **Test markers:** Tests auto-tagged by path (`unit/`, `integration/`, `docker/`). Run subsets with `make test-unit` etc.
- **Alembic connection:** DB URL set programmatically from `settings.py`, not from `alembic.ini`
- **Frontend tests:** Must run from `frontend/` directory, not project root
- **Ruff config:** 100-char line length, target py311
- **Docker Host** You are running in a container with an attached docker in docker host
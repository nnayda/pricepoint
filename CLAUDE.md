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
| Infra          | Docker Compose, Kubernetes/Helm, GitHub Actions                 |
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
docs/
└── FEATURE_CATALOG.md  # ML feature data dictionary (94 features, derivation logic, data sources)
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
make up                   # Start app services only (api, frontend, mlflow) - requires external infra
make up-infra             # Start app + core infra (postgres, minio, valkey) - use external Airflow
make up-all               # Start everything including bundled Airflow + its database
make down                 # Stop all services
make build                # Build all Docker images
make dev-sync-api         # Copy local src/ into running API container and restart (~5s)
make dev-sync-frontend    # Rebuild and restart frontend container with latest code
```

> **Tip:** After editing backend code in `src/`, run `make dev-sync-api` instead of `make build` to push changes into the running container without a full image rebuild. This uses `docker cp` + restart, which is much faster. For frontend changes, use `make dev-sync-frontend`.

## Environment

Copy `.env.example` to `.env`. Key variables:
- `DATABASE_URL` — PostgreSQL + PostGIS connection string (app database)
- `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN` — Airflow metadata database (separate from app)
- `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET` — MinIO/S3
- `MLFLOW_TRACKING_URI` — MLflow server
- `VALKEY_URL` — Redis-compatible cache (optional)

## Production Deployment

The app is deployed to Kubernetes via Helm (GitOps-friendly; works with Flux/Argo `HelmRelease` pointing at the OCI chart).

### Deployment Structure

- **Helm chart:** `helm/pricepoint/`, published to `oci://ghcr.io/nnayda/pricepoint/charts/pricepoint` on each release
- **Images:** `ghcr.io/nnayda/pricepoint/{api,frontend,mlflow,airflow}:<version>`, published by the release workflow
- **Namespace:** `pricepoint`

### Accessing Pods & Debugging

```sh
# List all pods
kubectl get pods -n pricepoint

# Get pod details / events (useful for crash loops, scheduling failures)
kubectl describe pod <pod-name> -n pricepoint

# Logs
kubectl logs <pod-name> -n pricepoint                    # Main container
kubectl logs <pod-name> -n pricepoint -c migrate         # Init container (API migration)
kubectl logs <pod-name> -n pricepoint -c wait-for-db     # Init container (DB wait)
kubectl logs <pod-name> -n pricepoint -c db-migrate      # Init container (Airflow DB migration)
kubectl logs <pod-name> -n pricepoint --previous         # Previous crashed container
kubectl logs <pod-name> -n pricepoint -f                 # Stream logs

# Port-forward for local debugging (bypasses ingress)
kubectl port-forward svc/pricepoint-api 8000:8000 -n pricepoint
kubectl port-forward svc/pricepoint-postgres 5432:5432 -n pricepoint
kubectl port-forward svc/pricepoint-airflow 8080:8080 -n pricepoint

# Check Helm release status (via Flux)
kubectl get helmrelease -n pricepoint
kubectl describe helmrelease pricepoint -n pricepoint

# View resource usage
kubectl top pods -n pricepoint

# Check PVCs
kubectl get pvc -n pricepoint

# Run a one-off database query
kubectl exec -it <postgres-pod> -n pricepoint -- psql -U pricepoint -d pricepoint

# Check Airflow DAG runs
kubectl exec -it <airflow-webserver-pod> -n pricepoint -- airflow dags list
kubectl exec -it <airflow-scheduler-pod> -n pricepoint -- airflow tasks list <dag_id>
```

## Gotchas

- **Airflow deps:** Airflow is installed separately in its Dockerfile to avoid SQLAlchemy version conflicts — don't add it to `pyproject.toml`
- **Docker profiles:** Three deployment modes:
  - `make up` — app only (requires external infrastructure)
  - `make up-infra` — app + core infra using `--profile infra` (postgres, minio, valkey), use external Airflow
  - `make up-all` — everything bundled using `--profile infra --profile airflow` (includes postgres-airflow database)
- **Separate databases:** Single PostgreSQL instance with two databases: `pricepoint` (app data) and `airflow` (metadata)
- **Test markers:** Tests auto-tagged by path (`unit/`, `integration/`, `docker/`). Run subsets with `make test-unit` etc.
- **Alembic connection:** DB URL set programmatically from `settings.py`, not from `alembic.ini`
- **Frontend tests:** Must run from `frontend/` directory, not project root
- **Ruff config:** 100-char line length, target py311
- **PostGIS geography casts:** Never use `func.cast(col, func.geography)` or `cast(col, text("geography"))` — both break SQLAlchemy 2.0's query cache (`_static_cache_key` error). Always use `from geoalchemy2 import Geography` then `cast(col, Geography())`.
- **Docker Host** You are running in a container with an attached docker in docker host
- **Airflow DAG retries:** Data collection DAGs must use `"retries": 0` — errors in data downloads likely need manual review, not automatic retries. Only processing/transform DAGs (feature engineering, model training, scoring, etc.) should use retries.
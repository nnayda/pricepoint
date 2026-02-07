# PricePoint Deployment Guide

This guide explains the different deployment options for PricePoint using Docker Compose.

## Overview

PricePoint supports three deployment modes to accommodate different infrastructure setups:

1. **App-Only Mode** — Minimal deployment, requires external infrastructure
2. **Core Infrastructure Mode** — Includes database and storage, uses external Airflow
3. **Fully Bundled Mode** — Everything runs locally including Airflow

## Deployment Modes

### 1. App-Only Mode

**Use case:** You have existing external infrastructure (database, S3, Airflow)

**Command:**
```bash
make up
```

**Services started:**
- API server (port 8000)
- Frontend (port 3000)
- MLflow tracking server (port 5001)

**Required external services:**
- PostgreSQL + PostGIS database
- S3-compatible object storage (MinIO, Ceph, AWS S3)
- Apache Airflow instance
- (Optional) Redis/Valkey cache

**Configuration:**
Update `.env` with your external service URLs:
```env
DATABASE_URL=postgresql://user:password@your-postgres:5432/pricepoint
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql://airflow:airflow@your-airflow-db:5432/airflow
S3_ENDPOINT_URL=https://your-s3-endpoint.com
VALKEY_URL=redis://your-redis:6379/0
```

---

### 2. Core Infrastructure Mode

**Use case:** You want to use bundled database and storage, but have external Airflow

**Command:**
```bash
make up-infra
```

**Services started:**
- All app services (API, frontend, MLflow)
- PostgreSQL + PostGIS (port 5432) — Application database
- MinIO (ports 9000, 9001) — S3-compatible storage
- Valkey (port 6379) — Redis-compatible cache
- pgAdmin (port 5050) — Database management UI

**Required external services:**
- Apache Airflow instance with its own database

**Configuration:**
Use default settings for bundled services, update Airflow connection:
```env
# Use bundled services (defaults)
DATABASE_URL=postgresql://pricepoint:pricepoint@postgres:5432/pricepoint
S3_ENDPOINT_URL=http://minio:9000
VALKEY_URL=redis://valkey:6379/0

# Point to external Airflow
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql://airflow:airflow@your-airflow-db:5432/airflow
```

---

### 3. Fully Bundled Mode

**Use case:** Local development, testing, or self-contained deployment

**Command:**
```bash
make up-all
```

**Services started:**
- All app services (API, frontend, MLflow)
- PostgreSQL + PostGIS (port 5432) — **Application database**
- PostgreSQL + PostGIS (port 5433) — **Airflow metadata database** (separate!)
- MinIO (ports 9000, 9001)
- Valkey (port 6379)
- pgAdmin (port 5050) — Pre-configured with both databases
- Airflow webserver/API (port 8080)
- Airflow scheduler
- Airflow init

**No external services required** — Everything runs in Docker.

**Configuration:**
Use the default `.env` settings (copy from `.env.example`):
```env
DATABASE_URL=postgresql://pricepoint:pricepoint@postgres:5432/pricepoint
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql://airflow:airflow@postgres-airflow:5432/airflow
S3_ENDPOINT_URL=http://minio:9000
# ... (see .env.example for full config)
```

---

## Database Separation

PricePoint uses **separate databases** for the application and Airflow:

| Database | Service | Port | Credentials | Purpose |
|----------|---------|------|-------------|---------|
| **Application** | `postgres` | 5432 | pricepoint/pricepoint | Property data, ML features, predictions |
| **Airflow** | `postgres-airflow` | 5433 | airflow/airflow | DAG metadata, task history, logs |

**Why separate databases?**
- Prevents Airflow metadata from interfering with application data
- Allows independent scaling and backup strategies
- Enables using external Airflow with bundled app database
- Simplifies migrations and version management

---

## Access Points

After running `make up-all`, you can access:

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | N/A |
| API | http://localhost:8000 | N/A |
| API Docs | http://localhost:8000/docs | N/A |
| MLflow UI | http://localhost:5001 | N/A |
| Airflow UI | http://localhost:8080 | admin / admin |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |
| pgAdmin | http://localhost:5050 | admin@pricepoint.local / admin |

---

## Stopping Services

To stop all services (including infrastructure):
```bash
make down
```

This stops services across all profiles (`infra` and `airflow`).

---

## Common Scenarios

### Scenario: Local Development
**Recommendation:** `make up-all`
- Full stack running locally
- Easy debugging and testing
- No external dependencies

### Scenario: Staging Environment with Managed Airflow
**Recommendation:** `make up-infra`
- Use AWS RDS or Cloud SQL for application database
- Use managed Airflow (AWS MWAA, Cloud Composer, Astronomer)
- Run app containers in ECS/GKE/AKS

### Scenario: Production with All External Services
**Recommendation:** `make up`
- Managed database (RDS, Cloud SQL)
- Managed object storage (S3, GCS, Azure Blob)
- Managed Airflow (MWAA, Composer)
- Managed cache (ElastiCache, Memorystore)
- Deploy containers to orchestration platform (Kubernetes, ECS)

---

## Docker Compose Profiles

Under the hood, the `make` commands use Docker Compose profiles:

```bash
# make up
docker compose up -d

# make up-infra
docker compose --profile infra up -d

# make up-all
docker compose --profile infra --profile airflow up -d
```

**Profiles:**
- `infra` — Core infrastructure (postgres, minio, valkey, pgadmin)
- `airflow` — Airflow components (postgres-airflow, airflow-init, airflow-scheduler, airflow-api-server)

---

## Environment Variables Reference

See `.env.example` for the complete list of environment variables.

**Critical variables:**
- `DATABASE_URL` — Application database connection
- `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN` — Airflow metadata database
- `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` — Object storage
- `MLFLOW_TRACKING_URI` — MLflow server location

**When using bundled infrastructure:**
Use the defaults from `.env.example` (localhost service names like `postgres`, `minio`, etc.)

**When using external infrastructure:**
Override with your external service URLs and credentials.

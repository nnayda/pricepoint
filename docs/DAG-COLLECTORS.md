# DAG Collector Architecture Guide

Guidelines for building and maintaining Airflow DAGs and data collectors in PricePoint.

## Overview

Data flows through a three-layer architecture:

```
Airflow DAG (orchestration)
  └── Collector module (fetch + transform logic)
        └── PostGIS via SQLAlchemy (storage)
```

**DAGs** live in `dags/` and handle scheduling, task dependencies, and verification.
**Collectors** live in `src/pricepoint/data/` and contain all business logic.
**Models** live in `src/pricepoint/db/models.py` with geometry columns via GeoAlchemy2.

---

## Transaction Safety

### The Problem

Never commit a DELETE separately from its corresponding INSERT. This pattern is **unsafe**:

```python
# BAD — if the insert fails, the table is empty
session.execute(delete(Model))
session.commit()              # ← Data is gone. Point of no return.

records = fetch_from_api()    # ← If this fails, table is empty.
session.add_all(records)
session.commit()
```

### Choose the Right Strategy

Pick a loading strategy based on dataset characteristics:

| Strategy | When to Use | Tradeoffs |
|---|---|---|
| **Single transaction** | Small/medium datasets (<100k rows), fast fetches (<5 min) | Simple; holds row locks during fetch |
| **Staging + upsert swap** | Large datasets, slow fetches, or tables referenced by FKs | Production never empty; preserves PKs for FK safety; requires staging table |
| **Upsert** | Small/medium datasets with stable natural keys, incremental loads | No staging table needed; slightly more complex SQL |

**FK consideration:** If any other table holds foreign keys to the production table (e.g., user preferences linking to `places.id`), you **must** use staging + upsert swap or direct upsert — never a truncate-based swap, which regenerates primary keys and breaks FK references.

### Strategy 1: Single Transaction

Wrap delete + insert in one transaction. If anything fails, the delete rolls back.

```python
def fetch_dataset() -> None:
    session = SessionLocal()
    try:
        session.execute(delete(Model))
        # No commit here — same transaction

        offset = 0
        while True:
            features = fetch_page(offset)
            if not features:
                break
            records = [Model(**parse(f)) for f in features]
            session.add_all(records)
            offset += len(features)

        session.commit()  # Atomic: all or nothing
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

Use `session.flush()` (not `commit()`) between pages if you need to release ORM memory without ending the transaction:

```python
session.add_all(records)
session.flush()  # Writes to DB but stays in the same transaction
```

### Strategy 2: Staging + Upsert Swap

For large or slow datasets, load into a staging table first, validate, then upsert into production. This is the **preferred strategy** for production tables that are referenced by foreign keys (e.g., user preferences), because it preserves primary key values for existing rows.

```python
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Columns to update on conflict (everything except the PK and natural key)
UPDATABLE_COLUMNS = ["name", "category", "address", "city", "state", ...]

def fetch_dataset() -> None:
    run_started = datetime.now(tz=UTC)
    session = SessionLocal()
    try:
        # 1. Load into staging (safe to truncate — not serving queries)
        session.execute(delete(StagingModel))
        session.commit()

        offset = 0
        total = 0
        while True:
            features = fetch_page(offset)
            if not features:
                break
            session.add_all([StagingModel(**parse(f)) for f in features])
            session.commit()  # Per-page commit is fine for staging
            total += len(features)
            offset += len(features)

        # 2. Validate before touching production
        count = session.scalar(select(func.count()).select_from(StagingModel))
        if count < MINIMUM_EXPECTED:
            raise RuntimeError(f"Only {count} staging rows, expected >= {MINIMUM_EXPECTED}")

        # 3. Upsert from staging into production (preserves PKs + FK references)
        staging_rows = session.execute(select(StagingModel)).scalars().all()
        for batch in batched(staging_rows, BATCH_SIZE):
            values = [row_to_dict(r) | {"loaded_at": run_started} for r in batch]
            stmt = pg_insert(ProductionModel).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["natural_key"],
                set_={col: stmt.excluded[col] for col in UPDATABLE_COLUMNS}
                    | {"loaded_at": stmt.excluded.loaded_at},
            )
            session.execute(stmt)
        session.commit()

        # 4. Remove stale rows not seen in this run
        session.execute(
            delete(ProductionModel).where(ProductionModel.loaded_at < run_started)
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

**Why upsert swap instead of truncate swap:**
- `DELETE + INSERT` regenerates auto-increment `id` values, breaking any FK references from other tables (e.g., user preferences linking to `places.id`)
- `ON CONFLICT DO UPDATE` preserves the existing `id` for matched rows, so all FK references remain valid
- The `loaded_at` timestamp marks which rows were refreshed, enabling stale-row cleanup without breaking references to active rows

### Strategy 3: Upsert (ON CONFLICT)

For datasets with a reliable natural key. No destructive delete needed.

```python
from sqlalchemy.dialects.postgresql import insert as pg_insert

def fetch_dataset() -> None:
    run_started = datetime.now(tz=UTC)
    session = SessionLocal()
    try:
        offset = 0
        while True:
            features = fetch_page(offset)
            if not features:
                break

            values = [parse(f) | {"loaded_at": run_started} for f in features]
            stmt = pg_insert(Model).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["natural_key"],
                set_={col: stmt.excluded[col] for col in updatable_columns},
            )
            session.execute(stmt)
            session.commit()
            offset += len(features)

        # Remove stale rows not seen in this run
        session.execute(delete(Model).where(Model.loaded_at < run_started))
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

Good natural key candidates: `geoid` (TIGER), `nces_id` (NCES), `case_number` (police), `globalid` (ArcGIS/HIFLD), `address` (Redfin).

---

## DAG Structure

### Standard Template

Every collection DAG follows this structure:

```python
"""DAG: Collect <dataset description>.

<One sentence explaining the data source and what it loads.>
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="<source>_<dataset>_collection",
    description="<Short description for Airflow UI>",
    schedule=None,  # or "@daily", "@weekly", [Asset("...")]
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["data", "collection", "<source>", "<dataset>"],
)
def dataset_collection():
    @task()
    def fetch_data():
        """Fetch <dataset> from <source>."""
        from pricepoint.data.<module> import fetch_<dataset>

        fetch_<dataset>()

    @task()
    def verify_load():
        """Verify records were loaded."""
        from pricepoint.data.<module> import verify_<dataset>

        verify_<dataset>()

    fetch_data() >> verify_load()


dataset_collection()
```

### Key Rules

1. **Imports inside tasks.** Import collector modules inside `@task` functions, not at module level. Airflow parses all DAG files on every scheduler heartbeat — top-level imports of heavy dependencies (SQLAlchemy, geopandas, httpx) slow down the scheduler.

2. **All logic in the collector module.** DAG files should only contain orchestration. No data parsing, API calls, or DB queries beyond simple verification counts.

3. **Always include a verify task.** Chain it after the fetch task with `>>`. Verify tasks should count rows and raise `RuntimeError` if the count is zero or below an expected minimum.

4. **Use `schedule=None` for reference data** that changes infrequently (boundaries, school directories, infrastructure). Use `@daily`/`@weekly` for operational data. Use `Asset` triggers for transforms and gold builders.

### Scheduling

| Schedule | Use Case | Examples |
|---|---|---|
| `schedule=None` | Manual-trigger reference data | TIGER boundaries, NCES schools, HIFLD |
| `@daily` | Operational data refreshed daily | Redfin listings, police incidents |
| `@weekly` | Slower-changing data | Economic indicators |
| `schedule=[Asset("...")]` | Downstream of another DAG | Transforms, gold table builders |

### Asset-Triggered DAGs

Use `Asset` for producer/consumer data dependencies between DAGs:

```python
# Producer DAG — declares an outlet
STAGING_DATASET = Asset("staging_redfin_listings")

@task(outlets=[STAGING_DATASET])
def fetch_listings():
    ...

# Consumer DAG — triggers on the asset
@dag(schedule=[Asset("staging_redfin_listings")])
def transform_dag():
    ...
```

### Task Dependencies

```python
# Sequential
fetch() >> verify()

# Fan-out (parallel)
fetch() >> [transform_a(), transform_b()]

# Fan-in
[fetch_a(), fetch_b()] >> combine()

# Independent parallel chains
fetch_a() >> verify_a()
fetch_b() >> verify_b()
```

---

## Collector Module Structure

### File Organization

```
src/pricepoint/data/
├── geospatial/
│   ├── arcgis_client.py       # Shared ArcGIS helpers (pagination, geometry conversion)
│   ├── tiger_boundaries.py    # US Census TIGER/Line
│   ├── nces_schools.py        # NCES school directory
│   └── ...
├── housing/
│   ├── redfin_listings.py     # Redfin HTML parsing
│   ├── redfin_transformer.py  # Staging → production transform
│   └── ...
└── economic/
    └── macro_indicators.py    # FRED economic data
```

### Required Function Signatures

Every collector must expose two functions:

```python
def fetch_<dataset>() -> None:
    """Fetch and load <dataset> into PostGIS."""
    ...

def verify_<dataset>() -> None:
    """Verify records were loaded. Raises RuntimeError if table is empty."""
    session = SessionLocal()
    try:
        count = session.execute(select(func.count()).select_from(Model)).scalar()
        if not count:
            raise RuntimeError(f"No records found in <table> after load")
        logger.info("Verified %d records in <table>", count)
    finally:
        session.close()
```

### Session Management

Always use try/except/finally:

```python
session = SessionLocal()
try:
    # ... work ...
    session.commit()
except Exception:
    session.rollback()
    raise
finally:
    session.close()
```

Never let a session leak. The `finally: session.close()` block is mandatory.

### Geometry Handling

All geometry is stored in SRID 4326 (WGS84). Use GeoAlchemy2's `from_shape` for conversion:

```python
from geoalchemy2.shape import from_shape
from shapely.geometry import Point, MultiPolygon

# Points (schools, POIs, incidents)
location = from_shape(Point(longitude, latitude), srid=4326)

# Polygons (boundaries, parcels) — always promote to Multi
if geom.geom_type == "Polygon":
    geom = MultiPolygon([geom])
wkb = from_shape(geom, srid=4326)
```

For ArcGIS data sources, use the shared helpers in `arcgis_client.py`:
- `build_point_wkb(geometry_dict)` — ArcGIS `{"x": ..., "y": ...}` to WKB Point
- `build_multipolygon_wkb(rings)` — ArcGIS rings to WKB MultiPolygon
- `build_multilinestring_wkb(paths)` — ArcGIS paths to WKB MultiLineString
- `parse_arcgis_timestamp(epoch_ms)` — ArcGIS epoch milliseconds to UTC datetime

### ArcGIS Pagination

For ArcGIS REST API sources, use the shared `fetch_arcgis_dataset` helper or follow its pagination pattern:

```python
offset = 0
while True:
    data = query_arcgis_page(base_url, offset, PAGE_SIZE)
    features = data.get("features", [])
    if not features:
        break

    records = [mapper(f) for f in features]
    session.add_all(records)
    # flush() or commit() depending on transaction strategy

    offset += len(features)
    if len(features) < PAGE_SIZE:
        break
```

Standard page size is 2000 for ArcGIS MapServer/FeatureServer endpoints.

---

## Medallion Architecture

Data progresses through three layers:

```
Bronze (staging)  →  Silver (cleaned)  →  Gold (production)
```

| Layer | Naming Convention | Purpose |
|---|---|---|
| **Bronze** | `staging_*` tables, `Staging*` models | Raw data as-received from external sources |
| **Silver** | Source-specific names (e.g., `nces_schools`, `tiger_tracts`) | Cleaned, typed, indexed — one model per source |
| **Gold** | Domain names (e.g., `schools`, `greenspaces`) | Merged from multiple sources, API-ready |

### When to Use Each Layer

- **Single source, no transformation needed**: Load directly into a silver table. Most geospatial collectors do this (TIGER, HIFLD, Wake amenities).
- **Raw data needs parsing/validation**: Load into bronze, transform to silver via a separate DAG triggered by `Asset`.
- **Multiple sources merged**: Silver tables feed a gold builder DAG (e.g., NCES + Redfin → `schools` gold table).

### Gold Builder Pattern

Gold builders receive a session and return a count:

```python
def build_schools_gold(session: Session) -> int:
    """Build gold schools table from silver NCES + Redfin data."""
    session.execute(delete(School))
    # ... merge logic ...
    session.add_all(gold_records)
    return len(gold_records)
    # Caller commits
```

The DAG task wraps this with commit/rollback:

```python
@task()
def build_gold():
    session = SessionLocal()
    try:
        count = build_schools_gold(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

---

## Configuration

All collector settings go in `src/pricepoint/config/settings.py` as Pydantic fields with sensible defaults:

```python
# In Settings class
tiger_base_url: str = "https://www2.census.gov/geo/tiger"
tiger_year: int = 2025
```

Access via `get_settings()` inside collector functions:

```python
from pricepoint.config.settings import get_settings

def fetch_dataset():
    settings = get_settings()
    url = f"{settings.tiger_base_url}/TIGER{settings.tiger_year}/..."
```

---

## Database Migrations

When adding a new model:

1. Add the model class to `src/pricepoint/db/models.py`
2. Generate a migration: `make migration MSG="add <table_name> table"`
3. Apply it: `make migrate`

### Required Indexes

- **GiST spatial index** on every geometry column:
  ```python
  __table_args__ = (
      Index("ix_<table>_geom", "geom", postgresql_using="gist"),
  )
  ```
- **B-tree index** on columns used in WHERE clauses or JOIN conditions (foreign keys, natural keys, status fields)

### Standard Metadata Columns

Every collector model should include:

```python
loaded_at = Column(DateTime(timezone=True), server_default=func.now())
```

---

## Error Handling

### In Collectors

- Log progress per page/batch: `logger.info("Loaded %d records (total: %d)", batch, total)`
- Log and skip individual geometry conversion failures (don't abort the whole load):
  ```python
  try:
      wkb = from_shape(geom, srid=4326)
  except (TypeError, ValueError) as exc:
      logger.warning("Skipping record %s: %s", record_id, exc)
      continue
  ```
- Raise on HTTP errors — let Airflow retry handle transient failures

### In DAGs

- Set `retries` in `default_args` (1-2 for collections, 2 for transforms)
- Set `retry_delay` to 5-10 minutes
- Verification tasks should `raise RuntimeError(...)` on failure — this marks the DAG run as failed and prevents downstream Asset triggers

---

## Checklist for New Collectors

- [ ] Collector module in `src/pricepoint/data/{geospatial,housing,economic}/`
- [ ] `fetch_*()` and `verify_*()` functions exported
- [ ] Transaction-safe loading strategy (single tx, staging+upsert swap, or direct upsert)
- [ ] SQLAlchemy model in `db/models.py` with GiST spatial index
- [ ] Alembic migration generated and tested
- [ ] Settings added to `config/settings.py` with defaults
- [ ] DAG file in `dags/` following the standard template
- [ ] `fetch >> verify` task chain
- [ ] Tags include `["data", "collection", "<source>", "<dataset>"]`
- [ ] If production table is FK-referenced, use staging+upsert swap (never truncate swap)
- [ ] Unit tests for parsing/mapping logic (mock HTTP, test with fixtures)
- [ ] DAG parse test updated with new DAG count

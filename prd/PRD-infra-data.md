# HIFLD Infrastructure + Overture Places Data Collection

## Context

PricePoint needs two types of geospatial data:

1. **Utility infrastructure** (power lines, cell towers, power plants, pipelines) — displayed as "negative POIs" on the dashboard, factored into the nuisance score
2. **Commercial POIs** (Costco, grocery stores, restaurants, etc.) — user-specified POI search, showing nearest location and distance on the dashboard

**Data sources chosen**:
- **HIFLD** for infrastructure — free, government-maintained, served via ArcGIS REST APIs (reuses existing `arcgis_client.py`). Most complete US source for power lines, cell towers, pipelines.
- **Overture Maps Places** for commercial POIs — free, 64M+ places worldwide (Foursquare + Meta + Microsoft sourced). Far more complete than raw OSM (~26% retail). Distributed as GeoParquet, bulk-loaded into PostGIS.

**Scope**: Nationwide, pre-loaded into PostGIS. Extend `/api/utilities` for infrastructure, new `/api/pois/search` for user-specified POI search.

---

## Part 1: HIFLD Infrastructure

### Verified HIFLD ArcGIS Endpoints

All at `services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services/`:

| Dataset | Service Name | Geometry | Key Fields |
|---------|-------------|----------|------------|
| Cell Towers | `Cellular_Towers_in_the_United_States/FeatureServer/0` | POINT | Licensee, LocCity, LocState, LocCounty, StrucType, AllStruc (height) |
| Transmission Lines | `US_Electric_Power_Transmission_Lines/FeatureServer/0` | POLYLINE | TYPE, STATUS, OWNER, VOLTAGE, VOLT_CLASS, SUB_1, SUB_2 |
| Power Plants | `Power_Plants_in_the_US/FeatureServer/0` | POINT | Plant_Name, State, County, PrimSource, Install_MW, Total_MW |
| Natural Gas Pipelines | `Natural_Gas_Interstate_and_Intrastate_Pipelines_1/FeatureServer/0` | POLYLINE | TYPEPIPE, Operator, Status |
| Petroleum Pipelines | `Petroleum_Products_Pipelines_1/FeatureServer/0` | POLYLINE | Opername, Pipename |

### Step 1.1: Extend `arcgis_client.py`

**File**: `src/pricepoint/data/geospatial/arcgis_client.py`

Add optional `where_clause: str = "1=1"` and `geometry_envelope: tuple[float,float,float,float] | None = None` parameters to `query_arcgis_page()` and `fetch_arcgis_dataset()`. Backward-compatible — existing callers unaffected. When `geometry_envelope` is provided, adds `geometry`, `geometryType=esriGeometryEnvelope`, `spatialRel=esriSpatialRelIntersects`, `inSR=4326` to the request params.

### Step 1.2: Add 5 HIFLD models

**File**: `src/pricepoint/db/models.py`

```
HifldCellTower        — POINT: licensee, callsign, city, state, county, structure_type, height_ft
HifldTransmissionLine — MULTILINESTRING: line_type, status, owner, voltage, volt_class, sub_1, sub_2
HifldPowerPlant       — POINT: plant_code, name, utility_name, state, county, primary_source, install_mw, total_mw
HifldNatGasPipeline   — MULTILINESTRING: pipe_type, operator, status
HifldPetroleumPipeline — MULTILINESTRING: operator, pipe_name
```

Each with: `id` PK, `objectid` indexed, `geom` with GiST spatial index, `loaded_at`.

### Step 1.3: Create Alembic migration

Generate with `make migration MSG="add hifld infrastructure tables"`. Creates 5 tables with GiST indexes.

### Step 1.4: Add settings

**File**: `src/pricepoint/config/settings.py`

5 URL settings with full FeatureServer URLs as defaults.

### Step 1.5: Create collector module

**File**: `src/pricepoint/data/geospatial/hifld_infrastructure.py`

Follow `wake_transportation.py` pattern — single file, 5 sections, each with `_map_*`, `fetch_*`, `verify_*`. Reuses `fetch_arcgis_dataset()`, `verify_arcgis_dataset()`, `build_point_wkb()`, `build_multilinestring_wkb()` from `arcgis_client.py`.

### Step 1.6: Create Airflow DAG

**File**: `dags/dag_hifld_infrastructure_collection.py`

`schedule=None`, 10 tasks (5 fetch + 5 verify), tags: `["data", "collection", "hifld", "infrastructure"]`.

### Step 1.7: Extend `/api/utilities` endpoint

**File**: `src/pricepoint/api/routes/utilities.py`

- Add 5 new sub-queries to `_build_features_query()` UNION ALL
- Update `_compute_nuisance_score()` with new weights: transmission_line=3, power_plant=3, cell_tower=2, pipeline=1 (existing: railroad=3, highway=2, easement=1). `max_raw` from 6 → 15.

**File**: `src/pricepoint/api/schemas/utilities.py`

Add optional fields: `nearest_cell_tower_miles`, `nearest_transmission_line_miles`, `nearest_power_plant_miles`, `nearest_pipeline_miles`.

### Step 1.8: Write HIFLD tests

**File**: `tests/unit/test_data/test_hifld_infrastructure.py` — ~25 tests (mapper + fetch per type)
**File**: `tests/unit/test_dags/test_dag_parsing.py` — update DAG count
**File**: `tests/unit/test_api/test_utilities.py` — update nuisance score tests

---

## Part 2: Overture Places (User-Specified POI Search)

### Data Access

Overture distributes as GeoParquet on S3 (no auth needed):
```
s3://overturemaps-us-west-2/release/2026-02-18.0/theme=places/type=place/*.parquet
```

Python CLI for bbox-filtered download:
```bash
overturemaps download --bbox=-84.4,33.8,-75.4,36.6 -f geoparquet --type=place -o places.geoparquet
```

DuckDB can also query S3 directly with bbox filter and stream results.

### Overture Places Schema

Key fields: `id`, `names.primary` (business name), `categories.primary` (category), `confidence` (0-1), `geometry` (Point), `addresses` (freeform, locality, postcode, region), `brand`, `websites`, `phones`.

### Step 2.1: Add Overture Places model

**File**: `src/pricepoint/db/models.py`

```
OverturePlacesPoi — POINT: overture_id (unique), name, category, confidence, address,
                    city, state, postcode, brand_name, website, phone,
                    geom (GiST index), loaded_at
```

Plus B-tree indexes on `name`, `category`, `state` for fast text search.

### Step 2.2: Create Alembic migration

Generate with `make migration MSG="add overture places table"`. Single table with spatial + text indexes.

### Step 2.3: Add settings

**File**: `src/pricepoint/config/settings.py`

```python
overture_places_s3_path: str = "s3://overturemaps-us-west-2/release/2026-02-18.0/theme=places/type=place/*"
overture_places_min_confidence: float = 0.5  # Skip low-quality entries
```

### Step 2.4: Create Overture Places collector

**File**: `src/pricepoint/data/geospatial/overture_places.py`

This collector differs from ArcGIS collectors — it reads GeoParquet from S3:

1. Use `overturemaps` Python CLI or `duckdb` + `pyarrow` to stream GeoParquet from S3 with bbox filter
2. Filter by `confidence >= min_confidence`
3. Map each record to `OverturePlacesPoi` model
4. Truncate-and-reload into PostGIS (matching existing pattern)
5. Batch insert (1000 records at a time for memory efficiency)

**Dependencies**: `overturemaps` (PyPI package) or `duckdb` + `pyarrow` + `geopandas`

### Step 2.5: Create Airflow DAG

**File**: `dags/dag_overture_places_collection.py`

`schedule=None`, 2 tasks (fetch + verify), tags: `["data", "collection", "overture", "places", "pois"]`.

### Step 2.6: Create `/api/pois/search` endpoint

**File**: `src/pricepoint/api/routes/pois.py` (extend existing)

New route: `GET /api/pois/search?lat=...&lon=...&query=...&radius_miles=5&limit=20`

Logic:
1. PostGIS query on `overture_places_pois` table
2. Filter: `ST_DWithin` for radius + `name ILIKE '%query%'` or `category ILIKE '%query%'` for text search
3. Order by distance, limit results
4. Return using existing `PoisResponse` schema (PointOfInterest items)
5. Cache in Valkey with key hash of `poi-search:{lat}:{lon}:{query}:{radius}`

### Step 2.7: Update frontend

**File**: `frontend/src/services/property.ts` — add `searchPois(lat, lon, query, radius)` service function
**File**: `frontend/src/types/index.ts` — types already support this (PointOfInterest has category, distance)

Frontend component changes (for the POI tab on dashboard):
- Add search input to PoisTab allowing user to type a POI name
- Call `/api/pois/search` with debounced input
- Display results in existing POI card format with distance

### Step 2.8: Write Overture tests

**File**: `tests/unit/test_data/test_overture_places.py` — test mapper, mock S3/DuckDB calls
**File**: `tests/unit/test_api/test_pois_search.py` — test search endpoint with mock DB

---

## Key Files to Modify/Create

| File | Action |
|------|--------|
| `src/pricepoint/data/geospatial/arcgis_client.py` | Extend with `where_clause` + `geometry_envelope` |
| `src/pricepoint/db/models.py` | Add 5 HIFLD + 1 Overture model |
| `src/pricepoint/config/settings.py` | Add 5 HIFLD URLs + 2 Overture settings |
| `src/pricepoint/data/geospatial/hifld_infrastructure.py` | **New** — 5-type HIFLD collector |
| `src/pricepoint/data/geospatial/overture_places.py` | **New** — Overture Places GeoParquet collector |
| `dags/dag_hifld_infrastructure_collection.py` | **New** — HIFLD DAG |
| `dags/dag_overture_places_collection.py` | **New** — Overture Places DAG |
| `src/pricepoint/api/routes/utilities.py` | Extend UNION ALL + nuisance score |
| `src/pricepoint/api/schemas/utilities.py` | Add 4 nearest-distance fields |
| `src/pricepoint/api/routes/pois.py` | Add `/api/pois/search` route |
| `frontend/src/services/property.ts` | Add `searchPois()` service |
| `tests/unit/test_data/test_hifld_infrastructure.py` | **New** — ~25 tests |
| `tests/unit/test_data/test_overture_places.py` | **New** — collector tests |
| `tests/unit/test_api/test_pois_search.py` | **New** — search API tests |
| `tests/unit/test_dags/test_dag_parsing.py` | Update DAG count |

## Verification

1. `make lint` — ruff check + format
2. `uv run mypy src/` — type checking
3. `make test-unit` — all tests pass
4. `make migration MSG="add hifld infrastructure tables"` + `make migration MSG="add overture places table"`
5. `make migrate` — apply migrations
6. Trigger HIFLD DAG → verify infrastructure records loaded
7. Trigger Overture Places DAG → verify POI records loaded
8. `GET /api/utilities?lat=35.78&lon=-78.64&radius_miles=3` → see new infrastructure types
9. `GET /api/pois/search?lat=35.78&lon=-78.64&query=Costco&radius_miles=10` → see Costco results with distance

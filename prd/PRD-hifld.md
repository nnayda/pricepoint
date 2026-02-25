# HIFLD Infrastructure Data Collection

## Context

PricePoint needs geospatial data:

1. **Utility infrastructure** (power lines, cell towers, power plants, pipelines) — displayed as "negative POIs" on the dashboard, factored into the nuisance score

**Data sources chosen**:
- **HIFLD** for infrastructure — free, government-maintained, served via ArcGIS REST APIs (reuses existing `arcgis_client.py`). Most complete US source for power lines, cell towers, pipelines.

**Scope**: Nationwide, pre-loaded into PostGIS. Extend `/api/utilities` for infrastructure.

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

## Key Files to Modify/Create

| File | Action |
|------|--------|
| `src/pricepoint/data/geospatial/arcgis_client.py` | Extend with `where_clause` + `geometry_envelope` |
| `src/pricepoint/db/models.py` | Add 5 HIFLD |
| `src/pricepoint/config/settings.py` | Add 5 HIFLD URLs |
| `src/pricepoint/data/geospatial/hifld_infrastructure.py` | **New** — 5-type HIFLD collector |
| `dags/dag_hifld_infrastructure_collection.py` | **New** — HIFLD DAG |
| `src/pricepoint/api/routes/utilities.py` | Extend UNION ALL + nuisance score |
| `src/pricepoint/api/schemas/utilities.py` | Add 4 nearest-distance fields |
| `tests/unit/test_data/test_hifld_infrastructure.py` | **New** — ~25 tests |
| `tests/unit/test_dags/test_dag_parsing.py` | Update DAG count |

## Verification

1. `make lint` — ruff check + format
2. `uv run mypy src/` — type checking
3. `make test-unit` — all tests pass
4. `make migration MSG="add hifld infrastructure tables"`
5. `make migrate` — apply migrations

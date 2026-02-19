# PricePoint - Final Phase PRD

## Context

PricePoint is a residential home search and valuation tool for Wake County, NC. The app predicts property values by combining geospatial data (police incidents, schools, POIs), housing data (Redfin listings, county assessments), and economic indicators (FRED/mortgage rates) through an ML pipeline.

**What's been built:** A solid data collection infrastructure (27 Airflow DAGs, 40+ DB models, 24 working collectors), a complete frontend with 5 pages/26 components/9 hooks, and a staging-to-production Redfin transform pipeline with 94 documented features. LLM-based description and photo scoring are operational.

**What's missing:** The core value proposition - the ML prediction pipeline is entirely stubbed. API endpoints for crime/POIs/greenspace/utilities return hardcoded data instead of querying the collected data. There is no authentication, no monitoring, and the ForecastPage needs a complete redesign as the primary property experience.

**This PRD covers all remaining work across 6 phases to bring PricePoint to production.**

---

## Phase 1: Wire Real Data to API Endpoints

**Goal:** Replace all hardcoded stub endpoints with real PostGIS queries against the data already collected in the database. This delivers immediate user-visible improvement.

### Task 1.1: Crime API - Real PostGIS Queries
**Owner:** Backend Developer
**Files:** `src/pricepoint/api/routes/crime.py`, `src/pricepoint/api/schemas/crime.py`

Replace the hardcoded 98 heatmap points and 25 sample incidents with real spatial queries:
- Query `staging_cary_police_incidents`, `staging_raleigh_police_incidents`, `staging_morrisville_police_incidents` tables using `ST_DWithin(location::geography, property_point, radius_meters)`
- Create a SQL CTE that unions all three police staging tables into a normalized view with `(id, location, occurred_at, description, category, source_city)` columns
- Return heatmap points as `[lat, lon, intensity]` where intensity is derived from incident recency (exponential decay: more recent = higher weight)
- Return incidents with proper pagination (default 50, max 200) sorted by date desc
- Compute real metrics: `total_incidents`, `incidents_per_sq_km`, `violent_pct`, `trend_vs_prior_year`
- Accept `radius_miles` (default 1.0) and `days_back` (default 365) query parameters
- Add Valkey caching with 6-hour TTL keyed on `(lat, lon, radius, days_back)`

**Acceptance criteria:**
- Endpoint returns real data from DB, not hardcoded stubs
- Response shape matches existing `CrimeResponse` TypeScript type (no frontend changes needed)
- Heatmap renders correctly on map with real incident locations
- Performance: P95 < 500ms for 1-mile radius query

**Tests:** 8-10 new unit tests mocking DB session, 2 integration tests with testcontainers

---

### Task 1.2: POIs API - Real PostGIS Queries
**Owner:** Backend Developer
**Files:** `src/pricepoint/api/routes/pois.py`, `src/pricepoint/api/schemas/pois.py`

Replace hardcoded 15 POIs with real spatial queries against all Wake County amenity tables:
- Query `wake_farmers_markets`, `wake_libraries`, `wake_hospitals`, `wake_parks`, `raleigh_parks`, `cary_parks` using spatial proximity
- Map each table to a POI category: `grocery` (farmers markets), `library`, `medical` (hospitals), `park`
- Accept `radius_miles` (default 2.0) query parameter
- Return POIs with `{id, name, category, lat, lon, distance_miles, address}` for each result
- Compute metrics: `total_count`, `categories_represented`, `nearest_distance_miles`

**Acceptance criteria:**
- Returns real amenity data from 6+ tables
- Response shape matches existing `PoisResponse` TypeScript type
- Map POI markers display at correct locations
- Frontend POI preference filtering still works (filtering happens client-side)

**Tests:** 6-8 unit tests, 1 integration test

---

### Task 1.3: Greenspace API - Real PostGIS Queries
**Owner:** Backend Developer
**Files:** `src/pricepoint/api/routes/greenspace.py`, `src/pricepoint/api/schemas/greenspace.py`

Replace hardcoded 6 park/trail features with real spatial queries:
- Query `wake_parks`, `raleigh_parks`, `cary_parks` (POINT geometries) and `wake_greenways`, `raleigh_greenways`, `cary_greenways` (MULTILINESTRING geometries) using `ST_DWithin`
- For parks: return centroid point, name, acres, amenity flags (restroom, ADA, playground, etc.)
- For greenways: return geometry simplified via `ST_Simplify` for map rendering, name, length
- Compute metrics: `total_parks`, `total_greenways`, `total_acres`, `nearest_park_miles`, `nearest_greenway_miles`
- Accept `radius_miles` (default 2.0) query parameter

**Acceptance criteria:**
- Returns real park and greenway data
- Greenway linestrings render as polylines on the map layer
- Park polygons or markers display correctly
- Cary parks with 30+ amenity flags are returned as structured data

**Tests:** 6-8 unit tests, 1 integration test

---

### Task 1.4: Utilities API - Real PostGIS Queries
**Owner:** Backend Developer
**Files:** `src/pricepoint/api/routes/utilities.py`, `src/pricepoint/api/schemas/utilities.py`

Replace hardcoded 5 utility features with real spatial queries:
- Query `wake_highways`, `wake_major_roads`, `wake_railroads`, `wake_utility_easements` (all MULTILINESTRING) using `ST_DWithin`
- Return simplified geometries for map rendering
- Compute distance to nearest of each type using `ST_Distance(location::geography, geom::geography)`
- Compute nuisance score: weighted combination of proximity to railroad (high impact), highway (medium), utility easement (low)
- Accept `radius_miles` (default 3.0) query parameter

**Acceptance criteria:**
- Returns real infrastructure data
- Linestrings render correctly on the utilities map layer
- Nuisance metrics are computed from actual distances

**Tests:** 6-8 unit tests, 1 integration test

---

### Task 1.5: Fix Police Incidents Collector
**Owner:** Backend Developer
**Files:** `src/pricepoint/data/geospatial/police_incidents.py`

The main `fetch_police_incidents()` function raises `NotImplementedError`. Implement it to:
- Call the existing city-specific collectors (Cary, Raleigh, Morrisville)
- Ensure each collector geocodes incidents that lack lat/lon
- Fix the 8 pre-existing test failures related to `get_whole_dataset`
- Update test mocks to match current function signatures

**Acceptance criteria:**
- `fetch_police_incidents()` successfully collects from all 3 cities
- All 8 previously-failing police incidents tests now pass
- Geocode cache TTL tests also verified (2 failures may already be resolved)

**Tests:** Fix 8 existing tests + add 4 new integration tests

---

### Task 1.6: Frontend - Dynamic Map Controls
**Owner:** Frontend Developer
**Files:** `frontend/src/components/PropertyMap/PropertyMap.tsx`, `frontend/src/services/property.ts`

Enhance the map UI now that real data will be flowing:
- Add radius control (slider or dropdown: 0.5, 1, 2, 3, 5 miles) above the map
- Add date range filter for crime tab (last 30, 90, 365 days)
- Pass `radius_miles` and `days_back` params through to service functions
- Handle empty results gracefully (show "No data found within X miles" message)
- Add loading indicators per tab (existing skeleton pattern)

**Acceptance criteria:**
- User can change radius and see map data update
- Crime tab has date range selector
- Empty states display friendly messages
- No regressions in existing map functionality

**Tests:** 8-10 new component tests for controls and empty states

---

## Phase 2: Economic Data Collection & Feature Engineering

**Goal:** Implement the economic data collector and all three feature engineering modules, producing the feature matrix needed for ML training.

### Task 2.1: Economic Data Collector (FRED API)
**Owner:** Backend Developer
**Files:** `src/pricepoint/data/economic/macro_indicators.py`, `src/pricepoint/db/models.py`, `src/pricepoint/config/settings.py`, `dags/dag_economic_collection.py`

Implement the FRED macroeconomic data collector:
- **New model** `EconomicIndicator`: `(id, series_id, observation_date, value, loaded_at)` with unique constraint on `(series_id, observation_date)`
- **New migration** with B-tree index on `(series_id, observation_date)`
- **Settings**: `fred_api_key: str`, `fred_series_ids: list[str]` (defaults below), `fred_lookback_years: int = 10`
- **Series to collect:**
  - `MORTGAGE30US` - 30-Year Fixed Mortgage Rate (weekly)
  - `MORTGAGE15US` - 15-Year Fixed Mortgage Rate (weekly)
  - `CPIAUCSL` - Consumer Price Index (monthly)
  - `UNRATE` - US Unemployment Rate (monthly)
  - `NCUR` - NC Unemployment Rate (monthly)
  - `HOUST` - Housing Starts (monthly)
  - `PERMIT` - Building Permits (monthly)
  - `CSUSHPISA` - Case-Shiller Home Price Index (monthly)
  - `UMCSENT` - Consumer Sentiment (monthly)
- **Collector logic**: Incremental fetch - query max `observation_date` per series, fetch only new observations. Use `fredapi.Fred` client. Bulk insert with `ON CONFLICT DO NOTHING`.
- **Airflow DAG**: `schedule="@weekly"`, single task calling `fetch_macro_indicators()`
- **Dependency**: Add `fredapi>=0.5,<1` to `pyproject.toml`

**Acceptance criteria:**
- `EconomicIndicator` table created via Alembic migration
- Collector fetches all 9 series from FRED API
- Incremental fetch works (doesn't re-download existing data)
- DAG parses and runs successfully

**Tests:** 12-15 unit tests (mock FRED API responses, incremental logic, error handling)

---

### Task 2.2: Geospatial Feature Engineering
**Owner:** Data Scientist / Backend Developer
**Files:** `src/pricepoint/features/geospatial.py`

Replace `NotImplementedError` with real PostGIS-based spatial feature computation. Process properties in batches of 100.

**Features to compute (per property in `redfin_listings`):**

| Feature | Type | Source Table(s) | PostGIS Strategy |
|---------|------|----------------|-----------------|
| `dist_nearest_school_m` | Float | `schools` | KNN with `<->` operator + GiST |
| `dist_nearest_elementary_m` | Float | `schools` (filtered) | Same, WHERE type='Elementary' |
| `dist_nearest_middle_m` | Float | `schools` (filtered) | Same |
| `dist_nearest_high_m` | Float | `schools` (filtered) | Same |
| `avg_school_rating_2mi` | Float | `schools` | AVG(rating) WHERE ST_DWithin(..., 3218m) |
| `count_schools_2mi` | Int | `schools` | COUNT within 2 miles |
| `crime_count_500m_1yr` | Int | `staging_*_police_incidents` (union CTE) | COUNT WHERE ST_DWithin AND occurred > now-1yr |
| `crime_count_1km_1yr` | Int | Same | Same at 1km |
| `crime_count_2km_1yr` | Int | Same | Same at 2km |
| `crime_density_1km` | Float | Derived | crime_count_1km / (pi * 1.0^2) |
| `dist_nearest_park_m` | Float | `*_parks` (3 tables) | Min distance to any park |
| `count_parks_2km` | Int | `*_parks` | COUNT within 2km |
| `total_park_acres_2km` | Float | `*_parks` | SUM(acres) within 2km |
| `dist_nearest_greenway_m` | Float | `*_greenways` (3 tables) | ST_Distance to nearest linestring |
| `dist_nearest_hospital_m` | Float | `wake_hospitals` | KNN |
| `dist_nearest_library_m` | Float | `wake_libraries` | KNN |
| `dist_nearest_highway_m` | Float | `wake_highways` | ST_Distance to linestring |
| `dist_nearest_railroad_m` | Float | `wake_railroads` | ST_Distance to linestring |
| `census_tract_geoid` | String | `tiger_tracts` | ST_Contains |
| `census_block_group_geoid` | String | `tiger_block_groups` | ST_Contains |
| `subdivision_name` | String | `wake_subdivisions` | ST_Contains |
| `has_utility_easement_100m` | Bool | `wake_utility_easements` | ST_DWithin(..., 100) |
| `llm_description_score` | Int | `llm_quality_scores` | JOIN on listing_id, latest version |
| `llm_photo_score` | Int | `llm_photo_scores` | JOIN on listing_id, latest version |

**Implementation pattern:** Use CROSS JOIN LATERAL for efficient KNN queries leveraging GiST indexes. Union police tables into a CTE before computing crime counts.

**Acceptance criteria:**
- Function returns a DataFrame with property_id index and all 24 geo features
- All distance features use `ST_Distance(::geography)` for meters
- Crime union CTE normalizes all 3 city tables
- Batch processing handles 1000+ properties without OOM

**Tests:** 20-25 unit tests with mock DB sessions returning known geometries

---

### Task 2.3: Housing Feature Engineering
**Owner:** Data Scientist / Backend Developer
**Files:** `src/pricepoint/features/housing.py`

Replace `NotImplementedError` with derived housing features from Redfin listings, sale/tax history, and county assessment data.

**Features to compute:**

| Feature | Type | Derivation |
|---------|------|-----------|
| `property_age` | Int | `current_year - year_built` |
| `is_renovated` | Bool | `year_renovated IS NOT NULL` |
| `years_since_renovation` | Int | `current_year - year_renovated` (NULL if never) |
| `days_on_market` | Int | `sold_date - contract_date` or `NOW() - contract_date` |
| `listing_premium_pct` | Float | `(listing_price - latest_assessment) / latest_assessment * 100` |
| `sale_premium_pct` | Float | `(sold_price - listing_price) / listing_price * 100` |
| `tax_assessed_value` | Float | Latest from `tax_history` |
| `land_to_improvements_ratio` | Float | `land_value / improvements_value` |
| `effective_tax_rate` | Float | `property_tax / assessment_value` |
| `price_yoy_change_pct` | Float | YoY change from last two SOLD events |
| `num_prior_sales` | Int | COUNT of sale_history WHERE event='SOLD' |
| `years_since_last_sale` | Float | `(NOW - max_sold_date) / 365.25` |
| `redfin_estimate_diff_pct` | Float | `(listing_price - redfin_estimate) / redfin_estimate * 100` |
| `bed_bath_ratio` | Float | `beds / baths` (handle div by zero) |
| `sqft_per_bedroom` | Float | `sqft / beds` |
| `lot_to_building_ratio` | Float | `lot_sqft / building_sqft` |
| `luxury_feature_count` | Int | SUM of premium booleans (pool, outdoor kitchen, sport court, etc.) |
| `amenity_score` | Int | SUM of all positive boolean features |
| `zip_median_price` | Float | PERCENTILE_CONT(0.5) within same zip, last 12 months |
| `zip_median_price_per_sqft` | Float | Same for price_per_sqft |
| `zip_price_rank_pct` | Float | PERCENT_RANK within zip |
| `city_median_price` | Float | Same median by city |

**Implementation:** Use SQLAlchemy window functions and subqueries. Zip/city medians use `PERCENTILE_CONT` partitioned by location.

**Acceptance criteria:**
- Returns DataFrame with property_id index and all 22 housing features
- Window functions correctly partition by zip/city
- Handles edge cases: div-by-zero, NULL renovation year, no sale history

**Tests:** 18-22 unit tests covering each feature's edge cases

---

### Task 2.4: Economic Feature Engineering
**Owner:** Data Scientist / Backend Developer
**Files:** `src/pricepoint/features/economic.py`

Replace `NotImplementedError` with temporal economic feature joins. For each property, find the most recent economic observation on or before the property's reference date (`sold_date` for sold properties, `processed_at` for current listings).

**Features to compute:**

| Feature | Source Series | Derivation |
|---------|-------------|-----------|
| `mortgage_rate_30yr` | `MORTGAGE30US` | Latest value <= property date |
| `mortgage_rate_15yr` | `MORTGAGE15US` | Same |
| `cpi` | `CPIAUCSL` | Latest value |
| `cpi_yoy_pct` | `CPIAUCSL` | `(current - 12mo_ago) / 12mo_ago * 100` |
| `unemployment_rate_us` | `UNRATE` | Latest value |
| `unemployment_rate_nc` | `NCUR` | Latest value |
| `housing_starts` | `HOUST` | Latest value |
| `case_shiller_index` | `CSUSHPISA` | Latest value |
| `case_shiller_yoy_pct` | `CSUSHPISA` | YoY % change |
| `consumer_sentiment` | `UMCSENT` | Latest value |

**Implementation:** Use correlated subquery pattern: `SELECT value FROM economic_indicators WHERE series_id = :s AND observation_date <= :d ORDER BY observation_date DESC LIMIT 1`. For YoY, fetch value at `property_date - INTERVAL '12 months'`.

**Acceptance criteria:**
- Returns DataFrame with property_id index and all 10 economic features
- "As of" date semantics correctly applied (no future data leakage)
- Forward-fill handles missing observations gracefully

**Tests:** 10-12 unit tests

---

### Task 2.5: Feature Assembly Pipeline
**Owner:** Data Scientist / Backend Developer
**Files:** `src/pricepoint/features/assembly.py`

Replace `NotImplementedError` with the full assembly pipeline that joins all feature sets into a training-ready matrix.

**Implementation:**
1. Fetch base listing data (94 columns from `redfin_listings`)
2. Call `build_geospatial_features()` -> merge on property_id
3. Call `build_housing_features()` -> merge on property_id
4. Call `build_economic_features()` -> merge on property_id
5. Drop internal/text columns not useful for ML (description, agent info, staging_hash, etc.)
6. Cast all booleans to int (0/1)
7. Apply missing value strategy:
   - Drop rows where `sqft IS NULL OR sold_price IS NULL OR year_built IS NULL OR location IS NULL`
   - Fill boolean NaN with 0, numeric distance NaN with 50000 (sentinel), economic NaN with forward-fill
   - Fill LLM scores NaN with median of non-null values
8. Apply variance threshold filter (drop zero-variance features)
9. Apply correlation filter (drop one of any pair with Pearson > 0.95, keeping higher target correlation)
10. Return DataFrame with `property_id` index + all features + `sold_price` target column

**Acceptance criteria:**
- Produces a clean feature matrix with no NaN values
- Includes ~120+ features (94 base + 24 geo + 22 housing + 10 economic - exclusions)
- Only includes SOLD properties with non-null prices for training
- Feature list is logged for reproducibility

**Tests:** 8-10 unit tests covering assembly, missing value handling, and filtering

---

### Task 2.6: Feature Engineering Airflow DAG
**Owner:** Backend Developer
**Files:** `dags/dag_feature_engineering.py`

Replace all `NotImplementedError` stubs in the feature engineering DAG:
- Task 1: `build_geospatial_features()` -> save to S3 as parquet
- Task 2: `build_housing_features()` -> save to S3 as parquet
- Task 3: `build_economic_features()` -> save to S3 as parquet
- Task 4: `assemble_feature_matrix(geo, housing, econ)` -> save assembled matrix to S3
- Set task dependencies: tasks 1-3 run in parallel, task 4 depends on all three
- Trigger: Dataset-triggered from redfin transform DAG completion, or manual

**Acceptance criteria:**
- All 4 tasks execute successfully
- Parquet files written to S3 with execution date partitioning
- DAG visible and triggerable in Airflow UI

**Tests:** DAG parsing test (update expected DAG count), 2-4 task-level unit tests

---

## Phase 3: ML Training Pipeline

**Goal:** Implement the complete model training, evaluation, and registry pipeline, producing a deployable home value prediction model.

### Task 3.1: Model Training Implementation
**Owner:** Data Scientist
**Files:** `src/pricepoint/models/training.py`
**Dependencies:** `lightgbm>=4.3,<5`, `scikit-learn>=1.5,<2`, `optuna>=3.6,<4`

Replace `NotImplementedError` with LightGBM training pipeline:

**Algorithm:** LightGBM (`LGBMRegressor`) as primary model
- Rationale: Handles mixed types natively, fast training, built-in categorical support, feature importance for interpretability, handles missing values internally

**Target variable:** `log1p(sold_price)` - log-transform to handle right-skewed distribution. Inverse transform predictions with `expm1()`.

**Train/test split:** Temporal split (NOT random) - sort by `sold_date`, train on first 80% chronologically, test on last 20%. Prevents future data leakage.

**Confidence intervals:** Train 3 models simultaneously:
- `model_median`: `objective="regression"` (point estimate)
- `model_lower`: `objective="quantile", alpha=0.1` (10th percentile)
- `model_upper`: `objective="quantile", alpha=0.9` (90th percentile)
This produces an 80% prediction interval.

**Hyperparameter tuning:** Optuna Bayesian optimization, 50 trials with early stopping:
```
n_estimators: (100, 2000), learning_rate: (0.01, 0.3),
max_depth: (3, 12), num_leaves: (15, 255),
min_child_samples: (5, 100), subsample: (0.6, 1.0),
colsample_bytree: (0.5, 1.0), reg_alpha: (1e-8, 10.0), reg_lambda: (1e-8, 10.0)
```

**Acceptance criteria:**
- `train_model()` returns a dict containing 3 fitted models (median, lower, upper)
- Log-transform applied to target, inverse-transform on predictions
- Temporal split correctly separates train/test
- Optuna logs each trial to MLflow as a child run

**Tests:** 10-12 unit tests (mock data, split logic, model interface)

---

### Task 3.2: Model Evaluation Implementation
**Owner:** Data Scientist
**Files:** `src/pricepoint/models/evaluation.py`

Replace `NotImplementedError` with comprehensive evaluation:

**Metrics computed (on dollar-scale after inverse log transform):**
- MAE (Mean Absolute Error)
- RMSE (Root Mean Squared Error)
- MAPE (Mean Absolute Percentage Error)
- R-squared
- Median Absolute Error
- P90 Absolute Error (90th percentile of errors)
- `within_5pct`: % of predictions within 5% of actual
- `within_10pct`: % of predictions within 10% of actual

**Segmented evaluation** - compute all metrics separately for:
- Price tiers: <$300K, $300K-$500K, $500K-$750K, >$750K
- Property age: Pre-2000 vs. post-2000
- City: Cary, Raleigh, Morrisville, other
- Property size: <1500 sqft, 1500-2500 sqft, >2500 sqft

**Baseline model:** Zip code median price (predict every property at its zip's median sale price from the last 12 months). LightGBM must beat this by >20% on MAE.

**Target performance thresholds:**
- MAE < $25,000
- MAPE < 8%
- R-squared > 0.85
- within_10pct > 70%

**Acceptance criteria:**
- `evaluate_model()` returns metrics dict with all 8 metrics + segmented breakdowns
- Baseline comparison is included
- All metrics are in dollar-scale (not log-scale)

**Tests:** 8-10 unit tests with synthetic predictions

---

### Task 3.3: Cross-Validation Implementation
**Owner:** Data Scientist
**Files:** `src/pricepoint/models/validation.py`

Replace `NotImplementedError` with time-series aware cross-validation:

- Use `sklearn.model_selection.TimeSeriesSplit(n_splits=5)` to respect temporal ordering
- Train on earlier data, validate on later data in each fold
- Compute all evaluation metrics per fold
- Return mean and std of all metrics across folds
- Flag instability if `std(MAPE) > 5` percentage points

**Acceptance criteria:**
- `cross_validate()` returns per-fold and aggregated metrics
- Temporal ordering is respected in every fold
- Instability warning logged when variance is high

**Tests:** 6-8 unit tests

---

### Task 3.4: MLflow Registry Integration
**Owner:** Data Scientist / Backend Developer
**Files:** `src/pricepoint/models/registry.py`

Replace `NotImplementedError` with MLflow experiment tracking and model registry:

**`log_model()` implementation:**
- Set experiment: `pricepoint-home-value`
- Log all hyperparameters, training metrics, segmented metrics
- Log all 3 models (median, lower, upper) as a single artifact directory
- Log feature importance as a table artifact
- Log feature schema (ordered list of feature names) for inference reproducibility
- Log training data shape (n_samples, n_features)
- Register model as `pricepoint-home-value` in MLflow Model Registry
- Return run_id

**`promote_model()` implementation:**
- Compare new model's MAPE against current Production model
- Only promote if new MAPE < current MAPE
- Archive previous Production version
- Transition new version to Production stage
- Log promotion event

**Acceptance criteria:**
- Models are logged with all metadata to MLflow
- Feature schema artifact ensures inference reproducibility
- Promotion gate prevents accuracy regression
- MLflow UI shows experiment history and model versions

**Tests:** 8-10 unit tests mocking MLflow client

---

### Task 3.5: Model Training Airflow DAG
**Owner:** Backend Developer
**Files:** `dags/dag_model_training.py`

Replace all `NotImplementedError` stubs:
- Task 1: `train` - load assembled features from S3, call `train_model()`
- Task 2: `validate` - run cross-validation, store metrics
- Task 3: `evaluate` - evaluate on holdout test set
- Task 4: `register` - log to MLflow, auto-promote if improved
- Task dependencies: train -> validate -> evaluate -> register
- Trigger: after feature engineering DAG completes, or manual
- Schedule: `@weekly` (after new economic data + listing refreshes)

**Acceptance criteria:**
- All 4 tasks execute end-to-end
- Model artifact stored in MLflow/S3
- Promotion gate works (blocks bad models)
- DAG count updated in parsing test

**Tests:** DAG parsing test, 4 task-level unit tests

---

### Task 3.6: Batch Inference Pipeline
**Owner:** Backend Developer
**Files:** `src/pricepoint/models/inference.py` (new), `dags/dag_batch_scoring.py` (new)

Create batch scoring pipeline that pre-computes predictions for all properties:
- Load Production model from MLflow registry
- Build features for all properties with `location IS NOT NULL`
- Generate predictions (point estimate + confidence interval) using all 3 models
- Upsert into `property_valuations` table with `source='ml_model'`
- Run after each model training DAG completes
- Also run on-demand when new listings are processed

**Acceptance criteria:**
- All properties with location data have ML valuations in `property_valuations`
- Predictions include confidence_low and confidence_high
- Existing Redfin estimates are preserved (different source)
- Performance: handles 5000+ properties in <10 minutes

**Tests:** 6-8 unit tests, 1 integration test

---

## Phase 4: Forecast Page Redesign & Frontend Enhancements

**Goal:** Replace the current minimal ForecastPage with a comprehensive property experience that showcases the ML predictions as the primary feature. Merge ResultsPage content into a redesigned ForecastPage.

### Task 4.1: Redesign ForecastPage as Primary Property Page
**Owner:** UX Designer + Frontend Developer
**Files:** `frontend/src/pages/ForecastPage.tsx` (rewrite), `frontend/src/pages/ResultsPage.tsx` (redirect)

The ForecastPage becomes the single property detail page at `/results`. The current ResultsPage is replaced. The new page layout:

**Section 1 - Property Header + Image Gallery** (top)
- Hero image with gallery trigger (lightbox)
- Address, status badge, core stats (beds/baths/sqft/year/lot)

**Section 2 - Value Forecast** (primary feature, prominently placed)
- Predicted value (large), confidence interval
- Comparison bars: predicted vs. listed vs. Redfin estimate vs. assessed
- Deal assessment badge (Good Deal / Fair / Overpriced)
- Historical + projected value chart (extend existing SaleTaxHistoryChart with dashed forecast line and confidence band)

**Section 3 - Feature Importance / "Why This Price?"**
- Top 5 value drivers (positive): e.g., "Top-rated school district +$18K"
- Top 5 detractors (negative): e.g., "Railroad within 1 mile -$7K"
- Horizontal bar chart visualization
- Requires new backend endpoint (Task 4.5)

**Section 4 - Comparable Properties**
- 3-5 recently sold similar properties nearby
- Mini-cards: address, price, date, beds/baths/sqft, price/sqft
- Map overlay showing comparable locations
- Requires new backend endpoint (Task 4.6)

**Sections 5-10** - Existing sections reorganized:
- Property Description + Highlights
- Nearby Schools
- Property Details (interior/exterior/financial)
- Climate Risk
- Mortgage Calculator
- Interactive Map (5 layers)

**Section Sidebar** - Scrollspy navigation (existing pattern)

**Acceptance criteria:**
- ForecastPage is the primary property view at `/results`
- ML prediction is the most prominent section
- Old ResultsPage route redirects to new page
- All existing ResultsPage sections preserved
- Responsive layout works on mobile

**Tests:** Update existing ResultsPage tests, add 15-20 new tests for forecast sections

---

### Task 4.2: Image Gallery Component
**Owner:** Frontend Developer
**Files:** `frontend/src/components/ImageGallery/ImageGallery.tsx` (new)

Build a lightbox image gallery for property photos:
- Triggered from PropertyHeader hero image click
- Thumbnail strip at bottom
- Keyboard navigation: left/right arrows, Escape to close
- Swipe support on mobile (touch events)
- Lazy loading for non-visible images (`loading="lazy"`)
- Uses existing `PropertyImage[]` type and `/api/photos/{path}` endpoint
- Accessible: focus trap, aria-label, escape to close

**Acceptance criteria:**
- Gallery opens on hero image click
- All property images browsable
- Keyboard and touch navigation work
- Graceful fallback when images fail to load

**Tests:** 10-12 tests (render, navigation, keyboard, accessibility)

---

### Task 4.3: Forecast Visualization Components
**Owner:** Frontend Developer
**Files:** `frontend/src/components/ForecastChart/ForecastChart.tsx` (new), `frontend/src/components/FeatureImportance/FeatureImportance.tsx` (new), `frontend/src/components/ComparableProperties/ComparableProperties.tsx` (new)

Three new components for the forecast section:

**ForecastChart:**
- Recharts ComposedChart extending SaleTaxHistoryChart pattern
- Historical: solid line for sale prices, area for assessed values
- Future: dashed line for predicted values, shaded area for confidence band
- Toggle between 1yr, 3yr, 5yr horizons
- Uses existing Recharts dependency

**FeatureImportance:**
- Horizontal bar chart showing top 10 features
- Positive (green, pointing right) and negative (red, pointing left) bars
- Labels translate feature names to human-readable text (e.g., `dist_nearest_railroad_m` -> "Railroad proximity")
- Tooltip with exact dollar impact

**ComparableProperties:**
- Grid of 3-5 property mini-cards
- Each card: thumbnail, address, sale price, date, beds/baths/sqft
- "View Details" link to that property's page
- Map markers overlay showing comparable locations

**Acceptance criteria:**
- All 3 components render correctly with mock data
- ForecastChart extends historical data with future projection
- Feature names are human-readable
- Comparable cards link to actual property pages

**Tests:** 8-10 tests per component (24-30 total)

---

### Task 4.4: Updated TypeScript Types & Service Functions
**Owner:** Frontend Developer
**Files:** `frontend/src/types/index.ts`, `frontend/src/services/property.ts`, `frontend/src/services/api.ts`

Update types and services for new backend endpoints:

**New types:**
```typescript
interface ForecastTimeline { date: string; value: number; low: number; high: number; }
interface FeatureAttribution { feature: string; display_name: string; impact_dollars: number; }
interface ComparableProperty { id: number; address: string; sale_price: number; sold_date: string; beds: number; baths: number; sqft: number; price_per_sqft: number; lat: number; lon: number; thumbnail_url?: string; }
interface ForecastData { predicted_value: number; confidence_low: number; confidence_high: number; model_version: string; timeline: ForecastTimeline[]; feature_attributions: FeatureAttribution[]; comparables: ComparableProperty[]; }
```

**New service functions:**
- `getComparables(lat, lon, beds, sqft, radius?)` -> `ComparableProperty[]`
- `getFeatureImportance(propertyId)` -> `FeatureAttribution[]`
- Update `getProperty()` to include `ForecastData` in response

**Consolidate Axios clients:** Merge the two separate Axios instances into a single shared client with centralized error handling and timeout configuration.

**Acceptance criteria:**
- All new types defined and exported
- Service functions call correct endpoints
- Single Axios client used throughout
- No TypeScript errors

**Tests:** Update service tests for new endpoints

---

### Task 4.5: Backend - Feature Importance Endpoint
**Owner:** Backend Developer
**Files:** `src/pricepoint/api/routes/forecast.py`, `src/pricepoint/api/schemas/forecast.py`

New endpoint `GET /api/forecast/importance/{property_id}`:
- Load the Production model's feature importance from MLflow artifact
- For the given property, compute SHAP-like local feature attributions (or use the model's built-in feature importance weighted by the property's feature values)
- Return top 10 positive and top 10 negative contributors with dollar impact
- Translate feature names to display names using a mapping dict

**Acceptance criteria:**
- Returns ranked feature attributions for a specific property
- Dollar impacts sum approximately to the difference between predicted and median
- Feature names are human-readable

**Tests:** 6-8 unit tests

---

### Task 4.6: Backend - Comparables Endpoint
**Owner:** Backend Developer
**Files:** `src/pricepoint/api/routes/property.py`, `src/pricepoint/api/schemas/property.py`

New endpoint `GET /api/comparables`:
- Query params: `lat`, `lon`, `beds`, `sqft`, `radius_miles` (default 3), `limit` (default 5)
- Find recently sold properties (last 12 months) within radius
- Filter to similar size (sqft within 25%) and bed count (within +/- 1)
- Sort by similarity score (weighted distance + size difference + recency)
- Return top N comparables with thumbnail URLs

**Acceptance criteria:**
- Returns 3-5 comparable properties sorted by similarity
- Spatial query uses GiST index efficiently
- Only includes SOLD properties with known prices
- Handles edge case: fewer than N comparables available

**Tests:** 8-10 unit tests

---

### Task 4.7: Frontend - Error Boundary & 404 Page
**Owner:** Frontend Developer
**Files:** `frontend/src/components/ErrorBoundary/ErrorBoundary.tsx` (new), `frontend/src/pages/NotFoundPage.tsx` (new), `frontend/src/App.tsx`

- **ErrorBoundary:** React error boundary wrapping major page sections. Shows fallback UI with "Something went wrong" message and retry button. Prevents white-screen crashes from bad data or rendering errors.
- **NotFoundPage:** 404 page for unmatched routes. Friendly message with link back to search.
- **Add catch-all route** in App.tsx: `<Route path="*" element={<NotFoundPage />} />`
- **Add request timeout** to `useApi` hook: abort requests after 15 seconds with user-friendly timeout message
- **Add AbortController** to `useApi` hook to cancel in-flight requests on unmount

**Acceptance criteria:**
- Component errors don't crash the entire page
- Unknown URLs show 404 page
- Timed-out requests show friendly error message
- No "state update on unmounted component" warnings

**Tests:** 10-12 tests for error boundary, 404, and timeout behavior

---

### Task 4.8: Frontend - Mobile Experience Improvements
**Owner:** Frontend Developer
**Files:** `frontend/src/components/NavBar/NavBar.tsx`, `frontend/src/components/MapTabBar/MapTabBar.tsx`, `frontend/src/components/SectionSidebar/SectionSidebar.tsx`

- **NavBar:** Add hamburger menu for screens below `sm` breakpoint. Collapsible menu with upload/settings links.
- **MapTabBar:** Add `overflow-x-auto` for horizontal scrolling on narrow screens. Shorter tab labels on mobile ("Crime" instead of "Crime Density").
- **SectionSidebar:** Convert to bottom navigation pills on mobile (fixed bottom bar with horizontal scroll). Currently hidden below `lg` breakpoint.
- **PropertyHeader stats:** Ensure stats wrap gracefully on narrow screens (2-column grid instead of 5-column).

**Acceptance criteria:**
- All pages usable on 375px-wide viewport
- No horizontal overflow on any page
- Section navigation accessible on mobile
- Map tabs scrollable on narrow screens

**Tests:** 6-8 responsive behavior tests

---

### Task 4.9: Frontend - Recently Viewed Properties
**Owner:** Frontend Developer
**Files:** `frontend/src/hooks/useRecentlyViewed.ts` (new), `frontend/src/components/RecentlyViewed/RecentlyViewed.tsx` (new), `frontend/src/pages/LandingPage.tsx`

- **Hook:** `useRecentlyViewed()` - stores last 10 viewed properties in localStorage keyed on `pricepoint-recently-viewed`. Stores `{address, lat, lon, price, thumbnailUrl, viewedAt}`.
- **Component:** Horizontal scroll of mini-cards shown on LandingPage below the SearchBar.
- **Integration:** ResultsPage/ForecastPage calls `addRecentlyViewed()` on successful data load.

**Acceptance criteria:**
- Recently viewed appears on landing page after viewing at least one property
- Max 10 items, oldest dropped when full
- Cards link to the property's results page
- Empty state: section hidden when no history

**Tests:** 8-10 tests for hook and component

---

## Phase 5: Authentication & Authorization

**Goal:** Implement a full auth system with OAuth2/OIDC, user accounts, saved favorites, and API keys for external consumers.

### Task 5.1: User Model & Auth Backend
**Owner:** Backend Developer
**Files:** `src/pricepoint/db/models.py`, `src/pricepoint/api/auth.py` (new), `src/pricepoint/config/settings.py`
**Dependencies:** `python-jose[cryptography]`, `passlib[bcrypt]`

- **New models:**
  - `User`: `(id, email, hashed_password, display_name, is_active, is_admin, created_at, updated_at)`
  - `ApiKey`: `(id, user_id, key_hash, name, is_active, created_at, last_used_at)`
  - `SavedProperty`: `(id, user_id, property_id, saved_at, notes)`
- **New migration** with unique constraint on email, indexes on API key hash
- **Auth module** (`auth.py`):
  - JWT access token creation (15-min expiry) + refresh token (7-day expiry)
  - `get_current_user` FastAPI dependency (extracts user from JWT)
  - `get_optional_user` dependency (returns None for unauthenticated requests)
  - Password hashing with bcrypt
  - API key validation middleware (checks `X-API-Key` header)
- **Settings:** `jwt_secret_key`, `jwt_algorithm` (HS256), `jwt_access_expire_minutes` (15), `jwt_refresh_expire_days` (7)

**Acceptance criteria:**
- JWT authentication works for all protected endpoints
- Refresh token rotation prevents token theft
- API key authentication works as alternative
- Password hashing uses bcrypt with appropriate rounds

**Tests:** 15-20 unit tests (token creation/validation, password hashing, dependency injection)

---

### Task 5.2: Auth API Endpoints
**Owner:** Backend Developer
**Files:** `src/pricepoint/api/routes/auth.py` (new)

- `POST /api/auth/register` - Create account (email, password, display_name)
- `POST /api/auth/login` - Return access + refresh tokens
- `POST /api/auth/refresh` - Exchange refresh token for new access token
- `POST /api/auth/logout` - Blacklist refresh token
- `GET /api/auth/me` - Return current user profile
- `POST /api/auth/api-keys` - Create API key (authenticated)
- `DELETE /api/auth/api-keys/{id}` - Revoke API key
- `GET /api/auth/api-keys` - List user's API keys

**Endpoint protection:**
- Public (no auth): geocode, property, crime, pois, greenspace, utilities, health
- Authenticated: forecast (for saving results), upload, saved properties, API keys
- Rate limited by tier: unauthenticated (30/min), authenticated (120/min), API key (600/min)

**Acceptance criteria:**
- Full registration/login/refresh flow works
- Protected endpoints return 401 without token
- API key authentication works for programmatic access
- Rate limiting applied per tier

**Tests:** 15-20 tests covering all auth flows

---

### Task 5.3: Saved Properties Endpoints
**Owner:** Backend Developer
**Files:** `src/pricepoint/api/routes/saved.py` (new)

- `GET /api/saved` - List user's saved properties with pagination
- `POST /api/saved/{property_id}` - Save a property (with optional notes)
- `DELETE /api/saved/{property_id}` - Unsave a property
- `GET /api/saved/{property_id}` - Check if property is saved

**Acceptance criteria:**
- Authenticated users can save/unsave properties
- Saved list returns property summary data (address, price, thumbnail)
- Pagination with cursor-based approach

**Tests:** 8-10 unit tests

---

### Task 5.4: OAuth2/OIDC Integration
**Owner:** Backend Developer
**Files:** `src/pricepoint/api/auth.py`, `src/pricepoint/config/settings.py`
**Dependencies:** `authlib`

Integrate with an OIDC provider for social login:
- `GET /api/auth/google` - Redirect to Google OAuth
- `GET /api/auth/google/callback` - Handle OAuth callback, create/link account
- **Settings:** `oauth_google_client_id`, `oauth_google_client_secret`, `oauth_redirect_uri`
- Auto-create user account on first OAuth login
- Link OAuth identity to existing email account if one exists

**Acceptance criteria:**
- Google OAuth login flow works end-to-end
- New users auto-created on first login
- Existing users can link Google account

**Tests:** 8-10 tests (mock OAuth flows)

---

### Task 5.5: Frontend - Auth Integration
**Owner:** Frontend Developer
**Files:** `frontend/src/contexts/AuthContext.tsx` (new), `frontend/src/components/AuthModal/AuthModal.tsx` (new), `frontend/src/components/NavBar/NavBar.tsx`, `frontend/src/hooks/useAuth.ts` (new)

- **AuthContext:** Global auth state provider. Stores JWT in memory (not localStorage for XSS protection), refresh token in httpOnly cookie.
- **useAuth hook:** `login()`, `register()`, `logout()`, `isAuthenticated`, `user`
- **AuthModal:** Login/register modal triggered from NavBar. Tabs for email/password and Google OAuth.
- **NavBar update:** Show user avatar + dropdown (profile, saved properties, API keys, logout) when authenticated. Show "Sign In" button when not.
- **Save button:** Add heart/bookmark icon to property header. Toggles saved state.
- **Saved Properties page:** New page at `/saved` listing bookmarked properties.
- **Axios interceptor:** Attach JWT to requests, auto-refresh on 401.

**Acceptance criteria:**
- Login/register flows work in the UI
- Auth state persists across page navigation
- Save button toggles correctly
- JWT refresh happens transparently
- Protected pages redirect to login

**Tests:** 15-20 tests (auth context, modal, save button, interceptor)

---

### Task 5.6: Rate Limiting
**Owner:** Backend Developer
**Files:** `src/pricepoint/api/main.py`, `src/pricepoint/config/settings.py`
**Dependencies:** `slowapi`

Implement tiered rate limiting using Valkey as the backend:
- Unauthenticated: 30 requests/minute globally, 10/minute for geocode
- Authenticated users: 120 requests/minute
- API key holders: 600 requests/minute
- Per-endpoint overrides: forecast 5/minute unauthenticated
- Return `Retry-After` header on 429 responses

**Acceptance criteria:**
- Rate limits enforced per tier
- Valkey-backed distributed counting
- Graceful fallback if Valkey is down (no rate limiting rather than blocking)
- 429 response includes Retry-After header

**Tests:** 8-10 tests

---

## Phase 6: Infrastructure Hardening & Quality

**Goal:** Bring the infrastructure to production-ready status with monitoring, security, CI enhancements, and comprehensive testing.

### Task 6.1: Secrets Management
**Owner:** DevOps Engineer
**Files:** `helm/home-value-forecast/templates/configmap.yaml`, `helm/home-value-forecast/templates/secret.yaml` (new)

Move sensitive values out of ConfigMap into Kubernetes Secrets:
- Create `secret.yaml` template for: `DATABASE_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `MLFLOW_BACKEND_STORE_URI`, `JWT_SECRET_KEY`, `FRED_API_KEY`, `OAUTH_GOOGLE_CLIENT_SECRET`
- Update deployments to reference secrets via `secretKeyRef`
- Generate Airflow secrets at deploy time (not hardcoded)
- Add `.env` to `.gitignore` verification

**Acceptance criteria:**
- No plaintext secrets in ConfigMap
- All deployments reference secrets correctly
- Helm template renders without errors

---

### Task 6.2: CI/CD Pipeline Enhancements
**Owner:** DevOps Engineer
**Files:** `.gitlab-ci.yml`

Add missing CI stages/jobs:
- **`python-typecheck`** (lint stage): `uv run mypy src/`
- **`python-audit`** (lint stage): `pip-audit` for dependency vulnerability scanning
- **`frontend-audit`** (lint stage): `npm audit --audit-level=moderate`
- **`helm-lint`** (lint stage): `helm lint` + `helm template` validation
- **`migration-test`** (test stage): Spin up testcontainers Postgres, run `alembic upgrade head` + `alembic downgrade -1` + `alembic upgrade head`
- **`container-scan`** (build stage): Trivy vulnerability scan on built images
- **`sast`** (lint stage): Include GitLab SAST template or Semgrep

**Acceptance criteria:**
- All new jobs pass on current codebase
- Container scan blocks builds with CRITICAL vulnerabilities
- Migration test validates up/down reversibility
- mypy passes with no errors

---

### Task 6.3: Monitoring Stack (Prometheus + Grafana)
**Owner:** DevOps Engineer
**Files:** `src/pricepoint/api/main.py`, `docker-compose.yml`, `helm/` templates
**Dependencies:** `prometheus-fastapi-instrumentator`

- **API instrumentation:** Add `prometheus-fastapi-instrumentator` to expose `/metrics` endpoint with: request latency histograms by endpoint, request counts by status code, in-flight request gauge
- **Docker Compose:** Add optional `prometheus` and `grafana` services (new profile: `monitoring`)
- **Grafana dashboards:** Pre-configured dashboards for: API latency P50/P95/P99, error rates, request volume, PostGIS query durations
- **Health endpoint enhancement:** `/health` should check DB connectivity and Valkey ping. `/ready` should verify all critical dependencies.

**Acceptance criteria:**
- `/metrics` endpoint returns Prometheus-format metrics
- Grafana dashboard shows real-time API metrics
- Health endpoints detect degraded dependencies
- Monitoring services optional (profile-based)

---

### Task 6.4: Structured Logging
**Owner:** Backend Developer
**Files:** `src/pricepoint/api/main.py`, all modules using `logging.getLogger()`
**Dependencies:** `structlog`

- Replace stdlib `logging` with `structlog` for JSON-structured output
- Add correlation ID middleware (generate UUID per request, attach to all log entries)
- Add request/response logging middleware (method, path, status, duration)
- Configure log level via `LOG_LEVEL` environment variable
- Update all existing `logger.info/warning/error` calls to use structlog

**Acceptance criteria:**
- All logs output as JSON with timestamp, level, correlation_id, module
- Request logs include duration for performance tracking
- Log level configurable via env var
- Existing log messages preserved with structured format

---

### Task 6.5: Caching Strategy Expansion
**Owner:** Backend Developer
**Files:** `src/pricepoint/api/routes/*.py`, `src/pricepoint/api/cache.py` (new)

Extend Valkey caching beyond geocode:
- Create a reusable `@cached(ttl=...)` decorator for route handlers
- Apply caching with appropriate TTLs:
  - Property details: 24 hours
  - Crime data: 6 hours
  - POIs/greenspace/utilities: 7 days
  - ML predictions: until model version changes (version in cache key)
- Add `Cache-Control` response headers
- Cache invalidation: when Airflow DAGs refresh data, publish Valkey pub/sub event. API subscribes and clears relevant keys.
- Graceful degradation: if Valkey unavailable, skip caching (no errors)

**Acceptance criteria:**
- Repeated requests served from cache
- TTLs appropriate per data type
- Cache invalidation works on data refresh
- No impact when Valkey is down

**Tests:** 8-10 unit tests

---

### Task 6.6: E2E Tests with Playwright
**Owner:** QA Engineer
**Files:** `frontend/e2e/` (new directory)
**Dependencies:** `@playwright/test`

Set up Playwright E2E test suite covering critical user flows:
1. **Search flow:** Type address -> select suggestion -> page transition -> property loads
2. **Map interactions:** Switch tabs -> layers render -> markers/heatmap visible
3. **Mortgage calculator:** Adjust sliders -> payment updates -> pie chart changes
4. **Settings persistence:** Change POI preferences -> navigate away -> return -> preserved
5. **Auth flow:** Register -> login -> save property -> view saved list -> logout
6. **Error states:** Invalid address -> error message displays
7. **Responsive:** Run key flows at mobile viewport (375px)

**CI integration:** Run against dev environment post-deploy as smoke test.

**Acceptance criteria:**
- 7 critical flow tests pass consistently
- Tests run in CI on dev deployments
- Screenshots captured on failure for debugging
- Tests run in <3 minutes

---

### Task 6.7: API Contract Testing
**Owner:** QA Engineer
**Files:** `frontend/scripts/generate-types.sh` (new), `.gitlab-ci.yml`

Ensure frontend/backend API contracts stay in sync:
- Add script that runs `npx openapi-typescript http://localhost:8000/openapi.json -o src/types/api.generated.ts`
- Add CI job that generates types from the built API container and diffs against committed types
- Flag any breaking changes as CI failure
- Document the contract update workflow

**Acceptance criteria:**
- CI detects API contract drift
- Generated types match manually-defined types
- Breaking changes flagged before merge

---

### Task 6.8: Performance Testing
**Owner:** QA Engineer
**Files:** `tests/performance/` (new directory)

Set up k6 load testing for key API endpoints:
- **Geocode:** 50 concurrent users, 2 minutes, P95 < 300ms
- **Property details:** 30 concurrent users, P95 < 500ms
- **Spatial queries (crime/POIs):** 20 concurrent users, P95 < 800ms
- **ML forecast:** 10 concurrent users, P95 < 2000ms
- **Spike test:** Ramp from 0 to 100 users in 30 seconds

Thresholds: `http_req_duration p(95)<threshold`, `http_req_failed rate<0.01`

**CI integration:** Run weekly or before production deploys.

**Acceptance criteria:**
- All endpoints meet latency thresholds
- Error rate < 1%
- Results logged with historical comparison

---

### Task 6.9: Database Operations
**Owner:** DevOps Engineer
**Files:** `helm/` templates, `docker-compose.yml`

- **Backup strategy:** Add PostgreSQL backup CronJob (Kubernetes) running daily `pg_dump` to S3. Keep 30 days of daily backups.
- **Docker Compose:** Add backup service (profile: `ops`) that runs `pg_dump` on schedule
- **PostGIS maintenance:** Add weekly `VACUUM ANALYZE` and `REINDEX` for tables with heavy spatial indexes
- **MLflow backend:** Migrate MLflow from SQLite to PostgreSQL (add `mlflow` schema in existing instance)
- **Connection pooling:** Add PgBouncer as a sidecar for the API deployment to handle connection pooling efficiently

**Acceptance criteria:**
- Automated daily backups to S3
- Restore tested and documented
- MLflow uses PostgreSQL backend
- Spatial index maintenance automated

---

### Task 6.10: Fix Pre-existing Test Failures
**Owner:** QA Engineer
**Files:** `tests/unit/test_api/test_geocode.py`, `tests/unit/test_data/test_*_police_incidents.py`

- **Geocode TTL (2 failures):** Verify if tests now pass after TTL was changed to 2592000s. If tests still assert 86400s, update assertions to match current code.
- **Police incidents (8 failures):** The tests reference `get_whole_dataset` which no longer exists. Update test mocks to patch the correct function names in the current collector module. Verify data shapes match.

**Acceptance criteria:**
- All 10 pre-existing test failures resolved
- No new test failures introduced
- Total test count: 900+ (current 879 + new tests from all phases)

---

### Task 6.11: Dockerfile Layer Caching Fix
**Owner:** DevOps Engineer
**Files:** `docker/api.Dockerfile`

The current Dockerfile copies `src/` before running `uv sync`, which means any source change invalidates the dependency cache. Reorder layers:
```
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev
COPY src/ src/
COPY alembic.ini ./
```

**Acceptance criteria:**
- Source-only changes don't trigger dependency reinstall
- Build time reduced by ~60% for code-only changes

---

## Phase Dependencies

```
Phase 1 (Wire APIs) ──────────────────────────────────┐
Phase 2 (Feature Engineering) ─── depends on Phase 1 ─┤
Phase 3 (ML Pipeline) ─────────── depends on Phase 2 ─┤
Phase 4 (Frontend Redesign) ────── depends on Phase 3 ─┤ (can start UI work in parallel)
Phase 5 (Auth) ─────────────────── independent ────────┤ (can start anytime)
Phase 6 (Infra Hardening) ─────── independent ─────────┘ (can start anytime)
```

**Recommended execution order:**
- Start Phases 1, 5, and 6 in parallel
- Phase 2 starts as Phase 1 completes
- Phase 3 starts as Phase 2 completes
- Phase 4 frontend work can start in parallel with Phase 3 (use mock data), integrate when ML is ready

---

## Verification Plan

After all phases complete, verify end-to-end:

1. **Data pipeline:** Trigger all Airflow DAGs manually. Verify data flows from collectors -> staging -> production -> features -> model training -> MLflow
2. **ML predictions:** Confirm model is registered in MLflow with target metrics (MAPE < 8%, R2 > 0.85). Verify batch scoring populates `property_valuations`.
3. **API endpoints:** Hit every endpoint with real data. Verify no stubs remain. Test spatial queries at various locations in Wake County.
4. **Frontend:** Navigate search -> results -> forecast flow. Verify ML predictions display, feature importance shows, comparables load, map layers show real data.
5. **Auth:** Register, login, save property, view saved list, create API key, use API key, logout.
6. **Performance:** Run k6 load tests. All endpoints meet latency thresholds.
7. **CI/CD:** Push a commit, verify all CI stages pass (lint, typecheck, security scan, tests, build, container scan).
8. **Monitoring:** Check Grafana dashboards show API metrics. Verify structured logs in JSON format.
9. **Run full test suite:** `make test && make frontend-test` - all tests pass, 0 failures.
10. **Build:** `npm run build` succeeds with no TypeScript errors. `make lint && make frontend-lint` pass.

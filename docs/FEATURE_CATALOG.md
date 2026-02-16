# Feature Catalog — `redfin_listings` Production Table

Data dictionary for the **94 engineered features** on the `redfin_listings` table (silver layer). This catalog documents every column's SQL type, source field(s), derivation logic, example values, and defaults.

## Target Audience

- **ML engineers** — feature selection, understanding distributions and defaults
- **Backend developers** — API contract, schema changes, debugging transforms
- **Data scientists** — feature engineering iteration, model interpretability

## References

| Item | Path |
|------|------|
| SQLAlchemy model | `src/pricepoint/db/models.py` → `RedfinListing` |
| Transformer module | `src/pricepoint/data/housing/redfin_transformer.py` |
| HTML collector | `src/pricepoint/data/housing/redfin_listings.py` |
| School enrichment | `src/pricepoint/data/housing/school_enrichment.py` |

## How to Use

- **Finding a feature:** Search this doc for the column name (e.g., `has_garage`). Each feature table lists its SQL type, source field, derivation logic, example value, and default.
- **Adding a feature:** Add a column to `RedfinListing` in `models.py`, write a `parse_*` function in `redfin_transformer.py`, wire it in `transform_listing()`, generate a migration, and update this catalog.
- **ML pipeline:** Exclude internal columns listed in the [Internal Columns](#internal-columns-exclude-from-ml) section. All `Boolean` features default to `false` (absent = unknown = false, no three-state logic).

---

## Data Pipeline

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────────────────────────────┐
│   Redfin HTML    │────▶│  BeautifulSoup   │────▶│   staging_redfin_listings (bronze)        │
│   (S3 / upload)  │     │  + lxml parser   │     │   ~30 columns + JSON blobs               │
└──────────────────┘     └──────────────────┘     └─────────────────┬────────────────────────┘
                                                                    │
                                                          redfin_transformer.py
                                                                    │
                         ┌──────────────────────────────────────────┼───────────────────────┐
                         │                                          ▼                       │
                         │  ┌──────────────────────────────────────────────────────────┐    │
                         │  │          redfin_listings (silver) — 94 features           │    │
                         │  └──────────────────────────────────────────────────────────┘    │
                         │                                          │                       │
                         │     ┌────────────┬────────────┬──────────┴──────────┐            │
                         │     ▼            ▼            ▼                     ▼            │
                         │  sale_history  tax_history  property_valuations  property_schools │
                         └─────────────────────────────────────────────────────────────────┘
```

**Key transform steps:**

1. **Hash check** — SHA-256 of staging columns; skip if unchanged (`compute_staging_hash`)
2. **Parse scalars** — price, dates, listing status from staging columns
3. **Parse ~90 features** — `parse_*` functions extract structured values from `property_details` JSON
4. **Geocode** — resolve lat/lon from `property_details` or Nominatim fallback
5. **Upsert** — insert or update `redfin_listings` row by `(street_address, city, state, zip_code)`
6. **Linked records** — replace `sale_history`, `tax_history`; upsert `property_valuations`
7. **School enrichment** — NCES fuzzy match → Nominatim fallback → OSRM travel times

---

## Feature Summary

| # | Category | Count | SQL Types | Primary Source |
|---|----------|-------|-----------|----------------|
| 1 | [Location & Address](#1-location--address) | 5 | String, Geometry | staging columns |
| 2 | [Listing & Pricing](#2-listing--pricing) | 5 | String, DateTime, Float, Text | staging columns |
| 3 | [Core Stats](#3-core-stats) | 6 | Integer, Float | staging + `property_details` |
| 4 | [Climate Risk](#4-climate-risk) | 4 | String, Integer | staging `climate_*` fields |
| 5 | [Parking](#5-parking) | 9 | Boolean, Integer, String | `property_details.parking_features` |
| 6 | [Fireplace](#6-fireplace) | 6 | Boolean, Integer, String | `property_details.fireplace*` |
| 7 | [Appliances & Energy](#7-appliances--energy) | 6 | Boolean, Integer, String | `property_details.appliances` |
| 8 | [Windows](#8-windows) | 3 | Boolean | `property_details.window_features` |
| 9 | [Laundry](#9-laundry) | 3 | Boolean, String | `property_details.laundry_features` |
| 10 | [Interior Features](#10-interior-features) | 12 | Boolean, String | `property_details.interior_features` |
| 11 | [Flooring](#11-flooring) | 4 | Boolean | `property_details.flooring` |
| 12 | [Exterior & Structure](#12-exterior--structure) | 8 | Boolean, Float, String | `property_details` (various) |
| 13 | [Utilities](#13-utilities) | 4 | Boolean | `property_details.sewer/water/heating/cooling` |
| 14 | [HOA & Community](#14-hoa--community) | 3 | Boolean, Float, String | `property_details.association*` |
| 15 | [Porch & Outdoor](#15-porch--outdoor) | 10 | Boolean | `property_details` (various) |
| 16 | [Agent Information](#16-agent-information) | 4 | String | staging columns |
| 17 | [Identifiers & Metadata](#17-identifiers--metadata) | 2 | String, DateTime | `property_details` |
| | **Total** | **94** | | |

---

## 1. Location & Address

Fields identifying the property's geographic position. Derived from staging columns and Nominatim geocoding.

| Column | SQL Type | Source | Derivation | Example | Default |
|--------|----------|--------|------------|---------|---------|
| `street_address` | `String` (NOT NULL, indexed) | `staging.address` | `parse_street_address()` — splits on first comma, takes street portion | `"123 Main St"` | — (required) |
| `city` | `String` | `staging.city` | Direct copy | `"Charlotte"` | `NULL` |
| `state` | `String(2)` | `staging.state` | Direct copy | `"NC"` | `NULL` |
| `zip_code` | `String(10)` | `staging.zip_code` | Direct copy | `"28202"` | `NULL` |
| `location` | `Geometry(POINT, 4326)` | `property_details.latitude/longitude` or Nominatim | `parse_location_from_details()` tries JSON lat/lon first; falls back to `geocode_address()` via Nominatim with retry/backoff | `SRID=4326;POINT(-80.84 35.22)` | `NULL` |

**Unique constraint:** `(street_address, city, state, zip_code)` — one row per address.

---

## 2. Listing & Pricing

Current listing state and pricing information.

| Column | SQL Type | Source | Derivation | Example | Default |
|--------|----------|--------|------------|---------|---------|
| `listing_status` | `String` | `staging.listing_status` | `normalize_listing_status()` — maps to `SOLD`, `FOR SALE`, `CONTINGENT`, `PENDING`, `COMING SOON`, `FOR RENT`, `UNDER CONTRACT` | `"SOLD"` | `NULL` |
| `sold_date` | `DateTime` | `staging.sold_date` | `parse_sold_date()` — handles `%B %d, %Y`, `%b %d, %Y`, `%Y-%m-%d`, `%m/%d/%Y`, month-only (`%b %Y`) | `2024-06-14` | `NULL` |
| `sold_price` | `Float` | `staging.sold_price` | `parse_price()` — strips `$`, commas; returns float | `721000.0` | `NULL` |
| `listing_price` | `Float` | `staging.listing_price` | `parse_price()` | `749900.0` | `NULL` |
| `description` | `Text` | `staging.description` | Direct copy | `"Beautiful 4BR home..."` | `NULL` |

---

## 3. Core Stats

Fundamental property dimensions. Most have staging-first-then-details fallback logic.

| Column | SQL Type | Source | Derivation | Example | Default |
|--------|----------|--------|------------|---------|---------|
| `year_built` | `Integer` | `staging.year_built` → `property_details.year_built` | `parse_year_built()` — staging value preferred; details fallback via `parse_int()` | `1998` | `NULL` |
| `year_renovated` | `Integer` | `property_details.year_renovated` | `parse_int(details.get("year_renovated"))` | `2019` | `NULL` |
| `num_beds` | `Integer` | `staging.beds` → `property_details.beds` → `num_of_bedrooms` | `parse_num_beds()` — three-level fallback chain | `4` | `NULL` |
| `num_baths` | `Float` | `staging.baths` → `property_details.baths` → `full + half` | `parse_num_baths()` — staging first; details fallback; computes `full + half` if separate fields | `2.5` | `NULL` |
| `sqft` | `Integer` | `staging.sqft` → `building_area_total` → `living_area` | `parse_sqft()` — three-level fallback chain | `2450` | `NULL` |
| `price_per_sqft` | `Float` | `staging.price_per_sqft` or computed | `parse_price_per_sqft()` — staging value first; falls back to `listing_price / sqft` | `306.12` | `NULL` |

---

## 4. Climate Risk

First Street Foundation climate risk data parsed from staging fields.

| Column | SQL Type | Source | Derivation | Example | Default |
|--------|----------|--------|------------|---------|---------|
| `flood_factor` | `String` | `staging.climate_flood_factor` | `map_climate_label()` — normalizes to title case: Minimal, Minor, Moderate, Major, Severe, Extreme | `"Moderate"` | `NULL` |
| `fire_factor` | `String` | `staging.climate_fire_factor` | `map_climate_label()` | `"Minor"` | `NULL` |
| `flood_score` | `Integer` | `staging.climate_flood_factor` | `map_climate_score()` — maps label to 1–6 (Minimal=1, Extreme=6) | `3` | `NULL` |
| `fire_score` | `Integer` | `staging.climate_fire_factor` | `map_climate_score()` | `2` | `NULL` |

---

## 5. Parking

Parsed from `property_details` keys: `garage`, `garage_spaces`, `parking_features`, `attached_garage`, `other_structures`, `parking_total`, `parking_spaces`.

| Column | SQL Type | Source | Derivation | Example | Default |
|--------|----------|--------|------------|---------|---------|
| `has_garage` | `Boolean` | `garage` | `parse_has_garage()` — `true` if `garage == "Yes"` (case-insensitive) | `true` | `false` |
| `num_garage_spaces` | `Integer` | `garage_spaces` | `parse_num_garage_spaces()` — `parse_int()`, 0 if missing | `2` | `0` |
| `parking_type` | `String` | `attached_garage`, `parking_features`, `garage` | `parse_parking_type()` — precedence: Attached Garage → Detached Garage → Carport → Street → Garage | `"Attached Garage"` | `NULL` |
| `garage_entry` | `String` | `parking_features` | `parse_garage_entry()` — checks for "garage faces front/side/rear" | `"Front"` | `NULL` |
| `driveway_surface` | `String` | `parking_features` | `parse_driveway_surface()` — paved keywords (concrete, asphalt, paver, brick) → `"Paved"`; gravel/dirt → `"Unpaved"` | `"Paved"` | `NULL` |
| `has_workshop` | `Boolean` | `parking_features`, `other_structures` | `parse_has_workshop()` — "workshop in garage" in parking OR "workshop" in other_structures | `false` | `false` |
| `has_circular_driveway` | `Boolean` | `parking_features` | `parse_has_circular_driveway()` — "circular driveway" substring check | `false` | `false` |
| `has_ev_charging` | `Boolean` | `parking_features` | `parse_has_ev_charging()` — "electric vehicle charging station(s)" substring check | `false` | `false` |
| `num_parking_spaces` | `Integer` | `parking_total`, `parking_spaces` | `parse_num_parking_spaces()` — tries `parking_total` first, then `parking_spaces` | `4` | `NULL` |

---

## 6. Fireplace

Parsed from `property_details` keys: `fireplace`, `fireplace_features`, `fireplaces_total`.

| Column | SQL Type | Source | Derivation | Example | Default |
|--------|----------|--------|------------|---------|---------|
| `has_fireplace` | `Boolean` | `fireplace` | `parse_has_fireplace()` — `true` if `fireplace == "Yes"` | `true` | `false` |
| `has_outdoor_fireplace` | `Boolean` | `fireplace_features` | `parse_has_outdoor_fireplace()` — "outside" or "fire pit" substring | `false` | `false` |
| `has_primary_fireplace` | `Boolean` | `fireplace_features` | `parse_has_primary_fireplace()` — "primary bedroom", "bedroom", or "bath" substring | `false` | `false` |
| `has_architectural_fireplace` | `Boolean` | `fireplace_features` | `parse_has_architectural_fireplace()` — "double sided" or "see through" substring | `false` | `false` |
| `fireplace_fuel_source` | `String` | `fireplace_features` | `parse_fireplace_fuel_source()` — precedence: Gas (gas log, sealed combustion, propane) → Wood (wood burning, masonry) → Electric → `"Unknown"` | `"Gas"` | `"Unknown"` |
| `num_fireplaces` | `Integer` | `fireplaces_total` | `parse_num_fireplaces()` — `parse_int()`, 0 if missing | `1` | `0` |

---

## 7. Appliances & Energy

Parsed from `property_details.appliances`.

| Column | SQL Type | Source | Derivation | Example | Default |
|--------|----------|--------|------------|---------|---------|
| `water_heater_energy_source` | `String` | `appliances` | `parse_water_heater_energy_source()` — "gas/propane water heater" → `"Gas"`, "electric water heater" → `"Electric"`, "solar hot water" → `"Solar"`, else `"UNKNOWN"` | `"Gas"` | `"UNKNOWN"` |
| `cooktop_energy_source` | `String` | `appliances` | `parse_cooktop_energy_source()` — gas/propane cooktop/range → `"Gas"`, electric/induction → `"Electric"`, else `NULL` | `"Electric"` | `NULL` |
| `oven_energy_source` | `String` | `appliances` | `parse_oven_energy_source()` — gas oven → `"Gas"`, electric oven → `"Electric"`, else `"UNKNOWN"` | `"Electric"` | `"UNKNOWN"` |
| `has_drink_fridge` | `Boolean` | `appliances` | `parse_has_drink_fridge()` — "bar fridge", "wine refrigerator", or "wine cooler" | `false` | `false` |
| `has_stainless_appliances` | `Boolean` | `appliances` | `parse_has_stainless_appliances()` — "stainless steel appliance(s)" substring | `true` | `false` |
| `appliances_included_count` | `Integer` | `appliances` | `parse_appliances_included_count()` — counts presence of refrigerator (0/1) + washer (0/1) + dryer (0/1), range 0–3 | `2` | `NULL` |

---

## 8. Windows

Parsed from `property_details.window_features`.

| Column | SQL Type | Source | Derivation | Example | Default |
|--------|----------|--------|------------|---------|---------|
| `has_efficient_windows` | `Boolean` | `window_features` | `parse_has_efficient_windows()` — "insulated windows", "double pane", "low-emissivity", "energy star qualified", "triple pane" | `true` | `false` |
| `has_skylights` | `Boolean` | `window_features` | `parse_has_skylights()` — "skylight" substring | `false` | `false` |
| `has_bay_window` | `Boolean` | `window_features` | `parse_has_bay_window()` — "bay" or "garden" substring | `false` | `false` |

---

## 9. Laundry

Parsed from `property_details.laundry_features`.

| Column | SQL Type | Source | Derivation | Example | Default |
|--------|----------|--------|------------|---------|---------|
| `laundry_location` | `String` | `laundry_features` | `parse_laundry_location()` — precedence: `"Upper"` → `"Main"` → `"Basement"` (lower/basement) → `"Garage/Out"` (garage/outside) → `"Standard"` | `"Main"` | `"Standard"` |
| `has_laundry_room` | `Boolean` | `laundry_features` | `parse_has_laundry_room()` — "laundry room" substring | `true` | `false` |
| `has_utility_sink` | `Boolean` | `laundry_features` | `parse_has_utility_sink()` — "sink" substring | `false` | `false` |

---

## 10. Interior Features

Parsed from `property_details.interior_features`.

| Column | SQL Type | Source | Derivation | Example | Default |
|--------|----------|--------|------------|---------|---------|
| `countertop_material` | `String` | `interior_features` | `parse_countertop_material()` — "quartz counters" → `"Ultra"`, "granite/stone counters" → `"Premium"`, "tile/laminate counters" → `"Standard"`, else `"Unknown"` | `"Premium"` | `"Unknown"` |
| `is_primary_downstairs` | `Boolean` | `interior_features` | `parse_is_primary_downstairs()` — "primary downstairs" substring | `true` | `false` |
| `has_guest_suite` | `Boolean` | `interior_features` | `parse_has_guest_suite()` — "in-law floorplan", "second primary bedroom", or "apartment/suite, room over garage" | `false` | `false` |
| `has_butler_pantry` | `Boolean` | `interior_features` | `parse_has_butler_pantry()` — "butler's pantry" substring | `false` | `false` |
| `has_walkin_closets` | `Boolean` | `interior_features` | `parse_has_walkin_closets()` — "walk-in closet(s)" substring | `true` | `false` |
| `has_tall_ceilings` | `Boolean` | `interior_features` | `parse_has_tall_ceilings()` — "high ceilings", "vaulted ceiling(s)", or "cathedral ceiling(s)" | `true` | `false` |
| `has_luxury_ceilings` | `Boolean` | `interior_features` | `parse_has_luxury_ceilings()` — "tray ceiling(s)", "coffered ceiling(s)", or "beamed ceilings" | `false` | `false` |
| `has_sauna` | `Boolean` | `interior_features` | `parse_has_sauna()` — "sauna" substring | `false` | `false` |
| `has_bar` | `Boolean` | `interior_features` | `parse_has_bar()` — "bar" substring (**caveat:** may false-positive on "barn", "rebar") | `false` | `false` |
| `has_second_primary` | `Boolean` | `interior_features` | `parse_has_second_primary()` — "second primary bedroom" substring | `false` | `false` |
| `has_room_over_garage` | `Boolean` | `interior_features` | `parse_has_room_over_garage()` — "room over garage" substring | `false` | `false` |
| `has_open_floorplan` | `Boolean` | `interior_features` | `parse_has_open_floorplan()` — "open floorplan" substring | `true` | `false` |

---

## 11. Flooring

Parsed from `property_details.flooring` and `property_details.crawl_space`.

| Column | SQL Type | Source | Derivation | Example | Default |
|--------|----------|--------|------------|---------|---------|
| `is_carpet_free` | `Boolean` | `flooring` | `parse_is_carpet_free()` — `true` if "carpet" is **not** present in flooring string | `true` | `false` |
| `has_premium_stone` | `Boolean` | `flooring` | `parse_has_premium_stone()` — "marble", "slate", "granite", or "stone" | `false` | `false` |
| `has_hardwood` | `Boolean` | `flooring` | `parse_has_hardwood()` — "wood", "bamboo", "parquet", "cork", or "fsc or sfi certified source hardwood" | `true` | `false` |
| `has_crawl_space` | `Boolean` | `crawl_space` | `parse_has_crawl_space()` — `true` if `crawl_space == "Yes"` | `false` | `false` |

---

## 12. Exterior & Structure

Parsed from various `property_details` keys: `construction_materials`, `building_area_total`, `above_grade_finished_area`, `below_grade_finished_area`, `stories`, `levels`, `lot_size*`, `waterfront`, `features`, `buyer_financing`.

| Column | SQL Type | Source | Derivation | Example | Default |
|--------|----------|--------|------------|---------|---------|
| `facade_type` | `String` | `construction_materials` | `parse_facade_type()` — precedence: Masonry (brick, stone, stucco, block, plaster) → Fiber Cement (fiber cement, hardiplank) → Synthetic (vinyl, metal, aluminum) → Wood (masonite, cedar, shake, log, lap siding) | `"Masonry"` | `NULL` |
| `building_area` | `Float` | `building_area_total` | `parse_building_area()` — `parse_float()` | `3200.0` | `NULL` |
| `above_grade_finished_area` | `Float` | `above_grade_finished_area` | `parse_above_grade_finished_area()` — `parse_float()` | `2400.0` | `NULL` |
| `below_grade_finished_area` | `Float` | `below_grade_finished_area` | `parse_below_grade_finished_area()` — `parse_float()` | `800.0` | `NULL` |
| `num_stories` | `Float` | `stories`, `levels` | `parse_num_stories()` — tries numeric parse first; then text map: One=1.0, One and One Half=1.5, Two=2.0, Bi-Level=2.0, Multi/Split=2.0, Three=3.0, Tri-Level=3.0; falls back to `levels` field | `2.0` | `NULL` |
| `lot_size` | `Float` | `lot_size_acres`, `lot_size`, `lot_size_square_feet`, `lot_size_area` + `lot_size_units`, `staging.lot_size` | `parse_lot_size_acres()` with `parse_lot_size_from_staging()` fallback — multi-format parser; always stored in **acres** (sq ft ÷ 43,560) | `0.45` | `NULL` |
| `is_waterfront` | `Boolean` | `waterfront`, `features` | `parse_is_waterfront()` — `waterfront == "Yes"` OR "waterfront" in `features` | `false` | `false` |
| `buyer_financing` | `String` | `buyer_financing` | Direct copy from `property_details.buyer_financing` via `_get_str()` | `"Conventional"` | `NULL` |

---

## 13. Utilities

Parsed from `property_details` keys: `sewer`, `water_source`, `heating`, `cooling`.

| Column | SQL Type | Source | Derivation | Example | Default |
|--------|----------|--------|------------|---------|---------|
| `is_septic` | `Boolean` | `sewer` | `parse_is_septic()` — "septic" or "private sewer" substring | `false` | `false` |
| `is_well_water` | `Boolean` | `water_source` | `parse_is_well_water()` — "well" or "private" substring | `false` | `false` |
| `no_heating` | `Boolean` | `heating` | `parse_no_heating()` — `true` only if `heating == "No"` exactly | `false` | `false` |
| `no_cooling` | `Boolean` | `cooling` | `parse_no_cooling()` — `true` only if `cooling == "No"` exactly | `false` | `false` |

---

## 14. HOA & Community

Parsed from `property_details` keys: `association`, `association_fee`, `association_fee_frequency`, `association_fee_2`, `association_fee_2_frequency`, `hoa_dues`, `association_name`.

| Column | SQL Type | Source | Derivation | Example | Default |
|--------|----------|--------|------------|---------|---------|
| `has_hoa` | `Boolean` | `association` | `parse_has_hoa()` — `true` if `association == "Yes"` | `true` | `false` |
| `association_fee` | `Float` | `association_fee`, `association_fee_2`, `hoa_dues` | `parse_association_fee_yearly()` — sums fee 1 + fee 2 (each with frequency); falls back to `hoa_dues`; always **normalized to yearly** via `_fee_to_yearly()` (monthly ×12, quarterly ×4, semi-annual ×2, annual ×1) | `3600.0` | `NULL` |
| `hoa_name` | `String` | `association_name` | Direct copy via `_get_str()` | `"Ballantyne HOA"` | `NULL` |

---

## 15. Porch & Outdoor

Parsed from various `property_details` keys: `patio_and_porch_features`, `fencing`, `exterior_features`, `other_structures`, `features`, `pool_features`, `community_features`, `association_amenities`.

| Column | SQL Type | Source | Derivation | Example | Default |
|--------|----------|--------|------------|---------|---------|
| `has_enclosed_porch` | `Boolean` | `patio_and_porch_features` | `parse_has_enclosed_porch()` — "screened" or "enclosed" substring | `false` | `false` |
| `has_front_porch` | `Boolean` | `patio_and_porch_features` | `parse_has_front_porch()` — "front porch" or "wrap around" substring | `true` | `false` |
| `has_fenced_yard` | `Boolean` | `fencing`, `exterior_features` | `parse_has_fenced_yard()` — fencing present AND not "none/invisible/partial/electric"; OR exterior has "fence/private yard/dog run" | `true` | `false` |
| `has_outdoor_kitchen` | `Boolean` | `exterior_features`, `other_structures` | `parse_has_outdoor_kitchen()` — "kitchen", "built-in barbecue", or "gas grill" in exterior; OR "outdoor kitchen" in other_structures | `false` | `false` |
| `has_sport_court` | `Boolean` | `exterior_features` | `parse_has_sport_court()` — "tennis court(s)", "basketball court", or "arena" | `false` | `false` |
| `has_private_pool` | `Boolean` | `exterior_features`, `features`, `pool_features` | `parse_has_private_pool()` — "pool" in exterior or features; OR pool_features present and not community/association/none | `false` | `false` |
| `has_community_pool` | `Boolean` | `community_features`, `pool_features`, `association_amenities` | `parse_has_community_pool()` — "pool" in community; OR "swimming pool com/fee/community/association" in pool_features; OR "pool" in association_amenities | `false` | `false` |
| `has_clubhouse` | `Boolean` | `community_features`, `association_amenities` | `parse_has_clubhouse()` — "clubhouse" in community; OR "clubhouse/recreation facilities/fitness center" in association_amenities | `false` | `false` |
| `has_exterior_storage` | `Boolean` | `other_structures`, `exterior_features` | `parse_has_exterior_storage()` — "shed/storage/workshop/outbuilding/barn/second garage" in other_structures; OR "storage/barn/equestrian/outbuilding/shed/stable" in exterior | `false` | `false` |
| `has_garden` | `Boolean` | `exterior_features`, `other_structures` | `parse_has_garden()` — "garden" or "greenhouse" in exterior; OR "greenhouse" in other_structures | `false` | `false` |

---

## 16. Agent Information

Direct copies from staging record fields.

| Column | SQL Type | Source | Derivation | Example | Default |
|--------|----------|--------|------------|---------|---------|
| `listing_agent` | `String` | `staging.listing_agent` | Direct copy | `"Jane Smith"` | `NULL` |
| `listing_brokerage` | `String` | `staging.listing_brokerage` | Direct copy | `"Keller Williams"` | `NULL` |
| `buying_agent` | `String` | `staging.buying_agent` | Direct copy | `"John Doe"` | `NULL` |
| `buying_brokerage` | `String` | `staging.buying_brokerage` | Direct copy | `"RE/MAX"` | `NULL` |

---

## 17. Identifiers & Metadata

| Column | SQL Type | Source | Derivation | Example | Default |
|--------|----------|--------|------------|---------|---------|
| `apn` | `String` | `property_details.apn` | `parse_apn()` — returns `NULL` for placeholder values ("See Plat", "N/A", "TBD", etc.) | `"0421-34-5678"` | `NULL` |
| `contract_date` | `DateTime` | `property_details.contract_status_change_date` | `parse_contract_date()` — reuses `parse_sold_date()` date parsing | `2024-05-01` | `NULL` |

---

## Internal Columns (Exclude from ML)

These columns are for system bookkeeping and should be excluded from ML feature sets:

| Column | SQL Type | Purpose |
|--------|----------|---------|
| `id` | `Integer` (PK) | Auto-increment primary key |
| `property_details` | `JSON` | Raw property details JSON blob for UI display |
| `property_photos` | `JSON` | S3 paths for property photos |
| `source_file` | `String` | Original HTML source file path |
| `staging_hash` | `String(64)` | SHA-256 hash for change detection (skip re-processing unchanged records) |
| `processed_at` | `DateTime(tz)` | Timestamp of last transform, `server_default=now()` |

---

## Linked Tables

### `sale_history`

Sale event records linked to `redfin_listings` via `property_id`. Replaced in full on each transform.

| Column | SQL Type | Derivation |
|--------|----------|------------|
| `id` | `Integer` (PK) | Auto-increment |
| `property_id` | `Integer` (indexed) | FK to `redfin_listings.id` |
| `date` | `DateTime` | `parse_sale_date()` — normalized via `_normalize_date()` |
| `event` | `String` | Event type uppercased (e.g., `"SOLD"`, `"LISTED"`) |
| `price` | `Float` | `parse_price()` |
| `source` | `String` | Always `"Redfin"` |

### `tax_history`

Annual tax assessment records linked via `property_id`. Replaced in full on each transform.

| Column | SQL Type | Derivation |
|--------|----------|------------|
| `id` | `Integer` (PK) | Auto-increment |
| `property_id` | `Integer` (indexed) | FK to `redfin_listings.id` |
| `date` | `DateTime` | `parse_tax_date()` — tax year → Jan 1 of that year |
| `property_tax` | `Float` | `parse_price()` |
| `assessment_value_land` | `Float` | `parse_price()` |
| `assessment_value_additions` | `Float` | `parse_price()` |
| `assessment_value` | `Float` | `parse_price()` |
| `source` | `String` | Always `"Redfin"` |

### `property_valuations`

Estimated property values from multiple sources. Upserted by `(property_id, source)`.

| Column | SQL Type | Derivation |
|--------|----------|------------|
| `id` | `Integer` (PK) | Auto-increment |
| `property_id` | `Integer` (indexed) | FK to `redfin_listings.id` |
| `source` | `String` (NOT NULL) | Source identifier (e.g., `"redfin"`, `"ml_model"`) |
| `value` | `Float` (NOT NULL) | Estimated property value in dollars |
| `model_version` | `String` | ML model version (NULL for Redfin estimates) |
| `confidence_low` | `Float` | Lower bound of confidence interval |
| `confidence_high` | `Float` | Upper bound of confidence interval |
| `estimated_at` | `DateTime(tz)` | Timestamp of valuation, `server_default=now()` |

### `property_schools`

Linkage between properties and nearby schools with travel times. Enriched via `school_enrichment.py`.

| Column | SQL Type | Derivation |
|--------|----------|------------|
| `id` | `Integer` (PK) | Auto-increment |
| `property_id` | `Integer` (indexed) | FK to `redfin_listings.id` |
| `school_id` | `Integer` (indexed) | FK to `schools.id` |
| `distance_miles` | `Float` | `parse_school_desc()` — extracted from description (e.g., `"0.3mi"`) |
| `drive_minutes` | `Integer` | OSRM car route duration |
| `walk_minutes` | `Integer` | OSRM foot route duration |

**Unique constraint:** `(property_id, school_id)`

---

## Data Sources

| Source | Format | Collector Module | Refresh Cadence |
|--------|--------|------------------|-----------------|
| Redfin | HTML pages | `data/housing/redfin_listings.py` | Daily (Airflow DAG) or manual upload |
| Nominatim (OpenStreetMap) | JSON API | `data/housing/redfin_transformer.py` → `geocode_address()` | On-demand during transform |
| NCES EDGE (schools) | ArcGIS JSON API | `data/geospatial/nces_schools.py` | Manual trigger (Airflow DAG) |
| OSRM (routing) | JSON API | `data/housing/school_enrichment.py` → `get_osrm_route()` | On-demand during enrichment |
| First Street Foundation | Embedded in Redfin HTML | `data/housing/redfin_listings.py` (extracted by HTML parser) | Per-listing |

---

## Conventions & Notes

### Boolean defaults
All `Boolean` columns default to `false` via `server_default=text("false")`. This means **absent = unknown = false** — there is no three-state logic. A `false` value cannot distinguish "confirmed absent" from "not mentioned in listing."

### Energy source defaults
- `water_heater_energy_source` and `oven_energy_source` default to `"UNKNOWN"` when no keyword match is found
- `cooktop_energy_source` defaults to `NULL` when no keyword match is found (inconsistency — the other two return `"UNKNOWN"`)

### Numeric defaults
- `num_garage_spaces` and `num_fireplaces` default to `0` when missing (via `or 0` in parse functions)
- All other numeric fields are nullable and default to `NULL`

### Case-insensitive matching
All `parse_*` functions lowercase both the source text and keywords before comparison. This handles inconsistent casing in Redfin HTML data.

### Lot size units
`lot_size` is always stored in **acres**. The multi-format parser (`parse_lot_size_acres`) handles:
- Direct acres values
- `"X.XX Acres"` text
- `"X,XXX Sq. Ft."` text (÷ 43,560)
- Separate `lot_size_area` + `lot_size_units` fields

### Stories text mapping
`num_stories` maps text values to floats:
| Text | Value |
|------|-------|
| One | 1.0 |
| One and One Half | 1.5 |
| Two | 2.0 |
| Bi-Level | 2.0 |
| Multi/Split | 2.0 |
| Three | 3.0 |
| Three or More | 3.0 |
| Tri-Level | 3.0 |

### Association fee normalization
`association_fee` is always normalized to a **yearly** amount:
- Monthly × 12
- Quarterly × 4
- Semi-annual × 2
- Annual × 1
- Multiple fees (fee 1 + fee 2) are summed after normalization

### Change detection
`staging_hash` is a SHA-256 computed over all staging data columns (`compute_staging_hash()`). If the hash matches the existing record, the transform is skipped entirely. This prevents unnecessary writes and preserves `processed_at` timestamps.

### Known limitations
- **`has_bar`** checks for the substring "bar" in `interior_features`, which can false-positive on words like "barn", "rebar", or "barricade"
- **`is_carpet_free`** returns `false` (not carpet-free) when no flooring data is present, since "carpet" is not found in an empty string — which actually means `true` (carpet not present). This is a minor semantic inversion for missing data.

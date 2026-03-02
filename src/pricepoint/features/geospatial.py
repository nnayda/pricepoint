"""Geospatial feature engineering.

Transforms raw geospatial data into model-ready features:
distance to nearest school, crime density within radius, nearby amenity counts, etc.
"""

from __future__ import annotations

import logging
import time

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

BATCH_SIZE = 100

# 2 miles in meters
TWO_MILES_M = 3218.0

# --- Individual distance queries (one CROSS JOIN LATERAL each) ---
# Each query computes a single distance feature for a batch of properties.
# Running them individually avoids a massive combined query plan that PostgreSQL
# struggles to execute against large reference tables (530K trails, 244K parks).

_DIST_SCHOOL_SQL = """
SELECT p.property_id,
       s.dist AS dist_nearest_school_m
FROM ({props_sql}) p
CROSS JOIN LATERAL (
    SELECT ST_Distance(p.location::geography, s.location::geography) AS dist
    FROM schools s
    WHERE s.location IS NOT NULL
    ORDER BY p.location <-> s.location
    LIMIT 1
) s
"""

_DIST_ELEMENTARY_SQL = """
SELECT p.property_id,
       s.dist AS dist_nearest_elementary_m
FROM ({props_sql}) p
CROSS JOIN LATERAL (
    SELECT ST_Distance(p.location::geography, s.location::geography) AS dist
    FROM schools s
    WHERE s.location IS NOT NULL AND s.school_type = 'Elementary'
    ORDER BY p.location <-> s.location
    LIMIT 1
) s
"""

_DIST_MIDDLE_SQL = """
SELECT p.property_id,
       s.dist AS dist_nearest_middle_m
FROM ({props_sql}) p
CROSS JOIN LATERAL (
    SELECT ST_Distance(p.location::geography, s.location::geography) AS dist
    FROM schools s
    WHERE s.location IS NOT NULL AND s.school_type = 'Middle'
    ORDER BY p.location <-> s.location
    LIMIT 1
) s
"""

_DIST_HIGH_SQL = """
SELECT p.property_id,
       s.dist AS dist_nearest_high_m
FROM ({props_sql}) p
CROSS JOIN LATERAL (
    SELECT ST_Distance(p.location::geography, s.location::geography) AS dist
    FROM schools s
    WHERE s.location IS NOT NULL AND s.school_type = 'High'
    ORDER BY p.location <-> s.location
    LIMIT 1
) s
"""

# Park query: use ST_DWithin pre-filter (20km) so the GiST index on geom
# narrows candidates before the expensive ST_Distance calculation.
# Without this, CROSS JOIN LATERAL scans all 244K greenspace rows per property.
_DIST_PARK_SQL = """
SELECT p.property_id,
       pk.dist AS dist_nearest_park_m
FROM ({props_sql}) p
CROSS JOIN LATERAL (
    SELECT ST_Distance(p.location::geography, pk.geom::geography) AS dist
    FROM greenspaces pk
    WHERE pk.geom IS NOT NULL
      AND ST_DWithin(p.location, pk.geom, 0.2)
    ORDER BY p.location <-> pk.geom
    LIMIT 1
) pk
"""

# Greenway/trail query: same ST_DWithin pre-filter for 530K trails.
_DIST_GREENWAY_SQL = """
SELECT p.property_id,
       g.dist AS dist_nearest_greenway_m
FROM ({props_sql}) p
CROSS JOIN LATERAL (
    SELECT ST_Distance(p.location::geography, g.geom::geography) AS dist
    FROM trails g
    WHERE g.geom IS NOT NULL
      AND ST_DWithin(p.location, g.geom, 0.2)
    ORDER BY p.location <-> g.geom
    LIMIT 1
) g
"""

# Hospital query: pre-filter to ~50km (0.5 degrees) since hospitals are sparse (7.5K).
_DIST_HOSPITAL_SQL = """
SELECT p.property_id,
       h.dist AS dist_nearest_hospital_m
FROM ({props_sql}) p
CROSS JOIN LATERAL (
    SELECT ST_Distance(p.location::geography, h.geom::geography) AS dist
    FROM hospitals h
    WHERE h.geom IS NOT NULL
      AND ST_DWithin(p.location, h.geom, 0.5)
    ORDER BY p.location <-> h.geom
    LIMIT 1
) h
"""

_DISTANCE_QUERIES: list[tuple[str, str]] = [
    ("dist_nearest_school_m", _DIST_SCHOOL_SQL),
    ("dist_nearest_elementary_m", _DIST_ELEMENTARY_SQL),
    ("dist_nearest_middle_m", _DIST_MIDDLE_SQL),
    ("dist_nearest_high_m", _DIST_HIGH_SQL),
    ("dist_nearest_park_m", _DIST_PARK_SQL),
    ("dist_nearest_greenway_m", _DIST_GREENWAY_SQL),
    ("dist_nearest_hospital_m", _DIST_HOSPITAL_SQL),
]

# Aggregate query: split into two separate queries to avoid computing
# park centroids for all 244K greenspaces in a single CTE.
_AGG_SCHOOLS_SQL = """
WITH props AS (
    SELECT id AS property_id, location
    FROM redfin_listings
    WHERE location IS NOT NULL
    {filter_clause}
)
SELECT
    p.property_id,
    AVG(s.rating) AS avg_school_rating_2mi,
    COUNT(*) AS count_schools_2mi
FROM props p
JOIN schools s ON s.location IS NOT NULL
    AND ST_DWithin(p.location::geography, s.location::geography, :two_miles_m)
GROUP BY p.property_id
"""

# Park aggregate: use ST_DWithin on the raw geom column (indexed) instead of
# computing centroids in a CTE. 0.018 degrees ~ 2km at NC latitude.
_AGG_PARKS_SQL = """
WITH props AS (
    SELECT id AS property_id, location
    FROM redfin_listings
    WHERE location IS NOT NULL
    {filter_clause}
)
SELECT
    p.property_id,
    COUNT(*) AS count_parks_2km,
    COALESCE(SUM(pk.gis_acres), 0) AS total_park_acres_2km
FROM props p
JOIN greenspaces pk ON pk.geom IS NOT NULL
    AND ST_DWithin(p.location, pk.geom, 0.018)
GROUP BY p.property_id
"""

_CONTAINMENT_SQL = """
WITH props AS (
    SELECT id AS property_id
    FROM redfin_listings
    WHERE location IS NOT NULL
    {filter_clause}
)
SELECT
    p.property_id,
    gl.census_tract_geoid,
    gl.census_block_group_geoid,
    gl.subdivision_name
FROM props p
LEFT JOIN property_geo_lookups gl ON gl.property_id = p.property_id
"""

_LLM_SCORES_SQL = """
WITH props AS (
    SELECT id AS property_id
    FROM redfin_listings
    WHERE location IS NOT NULL
    {filter_clause}
),
latest_quality AS (
    SELECT DISTINCT ON (qs.listing_id)
        qs.listing_id,
        qs.quality_score
    FROM llm_quality_scores qs
    JOIN props p ON p.property_id = qs.listing_id
    ORDER BY qs.listing_id, qs.extracted_at DESC
),
latest_photo AS (
    SELECT DISTINCT ON (ps.listing_id)
        ps.listing_id,
        ps.visual_quality_score
    FROM llm_photo_scores ps
    JOIN props p ON p.property_id = ps.listing_id
    ORDER BY ps.listing_id, ps.extracted_at DESC
)
SELECT
    p.property_id,
    lq.quality_score AS llm_description_score,
    lp.visual_quality_score AS llm_photo_score
FROM props p
LEFT JOIN latest_quality lq ON lq.listing_id = p.property_id
LEFT JOIN latest_photo lp ON lp.listing_id = p.property_id
"""


def _build_filter_clause(property_ids: list[int] | None) -> str:
    """Return SQL filter clause for property IDs."""
    if property_ids is None:
        return ""
    return "AND id = ANY(:property_ids)"


def _build_params(
    property_ids: list[int] | None,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build parameter dict for SQL queries."""
    params: dict[str, object] = {}
    if property_ids is not None:
        params["property_ids"] = property_ids
    if extra:
        params.update(extra)
    return params


def _get_all_property_ids(db: Session) -> list[int]:
    """Fetch all property IDs that have a location."""
    rows = db.execute(
        text("SELECT id FROM redfin_listings WHERE location IS NOT NULL ORDER BY id")
    ).fetchall()
    return [row[0] for row in rows]


def build_geospatial_features(
    db: Session,
    *,
    property_ids: list[int] | None = None,
) -> pd.DataFrame:
    """Compute geospatial features for the given properties.

    Queries PostGIS for distance, count/aggregate, containment, and LLM score
    features. Always processes in batches to avoid long-running monolithic queries.

    Returns a DataFrame indexed by property_id with 16 feature columns.
    """
    if property_ids is not None and len(property_ids) == 0:
        return _empty_frame()

    # Always resolve the full ID list so we can batch
    if property_ids is None:
        t0 = time.monotonic()
        property_ids = _get_all_property_ids(db)
        logger.info(
            "Loaded %d property IDs in %.1fs",
            len(property_ids),
            time.monotonic() - t0,
        )

    if not property_ids:
        return _empty_frame()

    total_batches = (len(property_ids) + BATCH_SIZE - 1) // BATCH_SIZE
    logger.info(
        "Processing %d properties in %d batches of %d",
        len(property_ids),
        total_batches,
        BATCH_SIZE,
    )

    frames: list[pd.DataFrame] = []
    for i, start in enumerate(range(0, len(property_ids), BATCH_SIZE)):
        batch = property_ids[start : start + BATCH_SIZE]
        batch_start = time.monotonic()
        logger.info("  Batch %d/%d (%d properties)...", i + 1, total_batches, len(batch))
        frames.append(_query_batch(db, batch))
        logger.info(
            "  Batch %d/%d done in %.1fs",
            i + 1,
            total_batches,
            time.monotonic() - batch_start,
        )

    return pd.concat(frames)


def _query_batch(
    db: Session,
    property_ids: list[int],
) -> pd.DataFrame:
    """Execute all query groups for a single batch and merge results."""
    filter_clause = _build_filter_clause(property_ids)
    params = _build_params(property_ids)

    # --- Distance features (run each KNN lookup individually) ---
    props_sql = (
        "SELECT id AS property_id, location FROM redfin_listings "
        "WHERE location IS NOT NULL AND id = ANY(:property_ids)"
    )

    dist_frames: list[pd.DataFrame] = []
    for feat_name, sql_template in _DISTANCE_QUERIES:
        t0 = time.monotonic()
        sql = sql_template.format(props_sql=props_sql)
        df = _exec_query(db, sql, params)
        elapsed = time.monotonic() - t0
        logger.info(
            "      %s: %d rows in %.1fs",
            feat_name,
            len(df),
            elapsed,
        )
        dist_frames.append(df)

    # Merge all distance DataFrames
    if dist_frames:
        dist_df = dist_frames[0]
        for other in dist_frames[1:]:
            if not other.empty:
                dist_df = dist_df.merge(other, on="property_id", how="outer")
    else:
        dist_df = pd.DataFrame(columns=["property_id"])

    # Aggregate features — school ratings (separate from parks for performance)
    t0 = time.monotonic()
    school_agg_df = _exec_query(
        db,
        _AGG_SCHOOLS_SQL.format(filter_clause=filter_clause),
        _build_params(property_ids, {"two_miles_m": TWO_MILES_M}),
    )
    logger.info(
        "      school_aggregates: %d rows in %.1fs",
        len(school_agg_df),
        time.monotonic() - t0,
    )

    # Aggregate features — park counts (uses geometry index pre-filter)
    t0 = time.monotonic()
    park_agg_df = _exec_query(
        db,
        _AGG_PARKS_SQL.format(filter_clause=filter_clause),
        params,
    )
    logger.info(
        "      park_aggregates: %d rows in %.1fs",
        len(park_agg_df),
        time.monotonic() - t0,
    )

    # Merge school + park aggregates
    agg_df = school_agg_df
    if not park_agg_df.empty:
        if agg_df.empty:
            agg_df = park_agg_df
        else:
            agg_df = agg_df.merge(park_agg_df, on="property_id", how="outer")

    # Fill missing aggregate counts with 0
    for col in ["count_schools_2mi", "count_parks_2km", "total_park_acres_2km"]:
        if col in agg_df.columns:
            agg_df[col] = agg_df[col].fillna(0)

    # Containment features (census tract, block group, subdivision)
    t0 = time.monotonic()
    contain_df = _exec_query(
        db,
        _CONTAINMENT_SQL.format(filter_clause=filter_clause),
        params,
    )
    logger.info(
        "      containment: %d rows in %.1fs",
        len(contain_df),
        time.monotonic() - t0,
    )

    # LLM scores
    t0 = time.monotonic()
    llm_df = _exec_query(
        db,
        _LLM_SCORES_SQL.format(filter_clause=filter_clause),
        params,
    )
    logger.info(
        "      llm_scores: %d rows in %.1fs",
        len(llm_df),
        time.monotonic() - t0,
    )

    # Merge all DataFrames on property_id
    result = dist_df
    for other in (agg_df, contain_df, llm_df):
        if not other.empty:
            result = result.merge(other, on="property_id", how="left")

    if result.empty:
        return _empty_frame()

    result = result.set_index("property_id")

    # Ensure column order
    return result.reindex(columns=FEATURE_COLUMNS)


def _exec_query(
    db: Session,
    sql: str,
    params: dict[str, object],
) -> pd.DataFrame:
    """Execute a raw SQL query and return as DataFrame."""
    result = db.execute(text(sql), params)
    rows = result.fetchall()
    columns = list(result.keys())
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns)


def _empty_frame() -> pd.DataFrame:
    """Return an empty DataFrame with the expected feature columns."""
    return pd.DataFrame(columns=FEATURE_COLUMNS)


FEATURE_COLUMNS = [
    "dist_nearest_school_m",
    "dist_nearest_elementary_m",
    "dist_nearest_middle_m",
    "dist_nearest_high_m",
    "dist_nearest_park_m",
    "dist_nearest_greenway_m",
    "dist_nearest_hospital_m",
    "avg_school_rating_2mi",
    "count_schools_2mi",
    "count_parks_2km",
    "total_park_acres_2km",
    "census_tract_geoid",
    "census_block_group_geoid",
    "subdivision_name",
    "llm_description_score",
    "llm_photo_score",
]

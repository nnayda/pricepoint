"""Geospatial feature engineering.

Transforms precomputed geospatial lookups into model-ready features:
distances to nearest schools/parks/hospitals, school ratings, noise/risk zones,
neighborhood history metrics, and LLM quality scores.
"""

from __future__ import annotations

import logging
import time

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_GEO_LOOKUP_SQL = """
SELECT
    gl.property_id,
    gl.avg_school_rating,
    gl.avg_school_drive,
    gl.dist_nearest_school_m,
    gl.dist_nearest_elementary_m,
    gl.dist_nearest_middle_m,
    gl.dist_nearest_high_m,
    gl.dist_nearest_park_m,
    gl.dist_nearest_greenway_m,
    gl.dist_nearest_hospital_m,
    gl.in_noise_zone::int AS in_noise_zone,
    gl.in_critical_risk_zone::int AS in_critical_risk_zone,
    gl.county_subdivision_geoid
FROM property_geo_lookups gl
JOIN redfin_listings rl ON rl.id = gl.property_id
WHERE rl.location IS NOT NULL
{filter_clause}
"""

_HISTORY_METRICS_SQL = """
SELECT DISTINCT ON (gl.property_id)
    gl.property_id,
    hm.avg_days_on_market_1m,
    hm.avg_days_on_market_3m,
    hm.avg_days_on_market_1y,
    hm.median_sale_price_1m,
    hm.median_sale_price_3m,
    hm.median_sale_price_1y
FROM property_geo_lookups gl
JOIN property_history_metrics hm
    ON gl.county_subdivision_geoid = hm.township_geoid
JOIN redfin_listings rl ON rl.id = gl.property_id
WHERE rl.location IS NOT NULL
{filter_clause}
ORDER BY gl.property_id, hm.metric_month DESC
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
    return "AND rl.id = ANY(:property_ids)"


def _build_filter_clause_props(property_ids: list[int] | None) -> str:
    """Return SQL filter clause for the props CTE (uses 'id' not 'rl.id')."""
    if property_ids is None:
        return ""
    return "AND id = ANY(:property_ids)"


def _build_params(property_ids: list[int] | None) -> dict[str, object]:
    """Build parameter dict for SQL queries."""
    params: dict[str, object] = {}
    if property_ids is not None:
        params["property_ids"] = property_ids
    return params


def build_geospatial_features(
    db: Session,
    *,
    property_ids: list[int] | None = None,
) -> pd.DataFrame:
    """Compute geospatial features for the given properties.

    Queries precomputed geo lookups, history metrics, and LLM scores.

    Returns a DataFrame indexed by property_id with 19 feature columns.
    """
    if property_ids is not None and len(property_ids) == 0:
        return _empty_frame()

    filter_clause = _build_filter_clause(property_ids)
    filter_clause_props = _build_filter_clause_props(property_ids)
    params = _build_params(property_ids)

    # Geo lookup features
    t0 = time.monotonic()
    geo_df = _exec_query(db, _GEO_LOOKUP_SQL.format(filter_clause=filter_clause), params)
    logger.info("Geo lookup: %d rows in %.1fs", len(geo_df), time.monotonic() - t0)

    # History metrics
    t0 = time.monotonic()
    history_df = _exec_query(db, _HISTORY_METRICS_SQL.format(filter_clause=filter_clause), params)
    logger.info("History metrics: %d rows in %.1fs", len(history_df), time.monotonic() - t0)

    # LLM scores
    t0 = time.monotonic()
    llm_df = _exec_query(db, _LLM_SCORES_SQL.format(filter_clause=filter_clause_props), params)
    logger.info("LLM scores: %d rows in %.1fs", len(llm_df), time.monotonic() - t0)

    if geo_df.empty:
        return _empty_frame()

    # Drop county_subdivision_geoid (used only for joining, not a feature)
    if "county_subdivision_geoid" in geo_df.columns:
        geo_df = geo_df.drop(columns=["county_subdivision_geoid"])

    # Merge all DataFrames on property_id
    result = geo_df
    for other in (history_df, llm_df):
        if not other.empty:
            result = result.merge(other, on="property_id", how="left")

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
    # Geo lookup features (11)
    "avg_school_rating",
    "avg_school_drive",
    "dist_nearest_school_m",
    "dist_nearest_elementary_m",
    "dist_nearest_middle_m",
    "dist_nearest_high_m",
    "dist_nearest_park_m",
    "dist_nearest_greenway_m",
    "dist_nearest_hospital_m",
    "in_noise_zone",
    "in_critical_risk_zone",
    # History metrics (6)
    "avg_days_on_market_1m",
    "avg_days_on_market_3m",
    "avg_days_on_market_1y",
    "median_sale_price_1m",
    "median_sale_price_3m",
    "median_sale_price_1y",
    # LLM scores (2)
    "llm_description_score",
    "llm_photo_score",
]

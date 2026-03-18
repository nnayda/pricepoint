"""Comparable sales feature engineering.

Computes comp-derived features for the XGBoost model by finding spatially
similar sold properties and aggregating their price signals.  Temporal
leakage is prevented by only using comps that sold *before* the subject.
"""

from __future__ import annotations

import logging
import time

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_COMP_FEATURES_SQL = """
WITH subjects AS (
    SELECT id, location, sold_date, sqft, price_per_sqft, num_beds, num_baths
    FROM redfin_listings
    WHERE location IS NOT NULL
      AND sqft IS NOT NULL
      AND num_beds IS NOT NULL
    {filter_clause}
)
SELECT
    s.id AS property_id,
    COUNT(comp.id) AS comp_count,
    PERCENTILE_CONT(0.5) WITHIN GROUP (
        ORDER BY comp.sold_price / NULLIF(comp.sqft, 0)
    ) AS comp_median_ppsf,
    AVG(
        comp.sold_price
        + (s.sqft - comp.sqft) * (comp.sold_price / NULLIF(comp.sqft, 0))
    ) AS comp_mean_adjusted_price,
    (
        SELECT c2.sold_price
        FROM redfin_listings c2
        WHERE c2.id != s.id
          AND c2.listing_status = 'SOLD'
          AND c2.sold_price IS NOT NULL
          AND c2.sqft IS NOT NULL
          AND c2.num_beds IS NOT NULL
          AND (s.sold_date IS NULL OR c2.sold_date < s.sold_date)
          AND ST_DWithin(
              c2.location::geography, s.location::geography, 3218
          )
          AND c2.num_beds BETWEEN s.num_beds - 1 AND s.num_beds + 1
          AND c2.sqft BETWEEN s.sqft * 0.8 AND s.sqft * 1.2
        ORDER BY ST_Distance(
            c2.location::geography, s.location::geography
        )
        LIMIT 1
    ) AS comp_nearest_price,
    s.price_per_sqft AS subject_ppsf,
    CASE
        WHEN COUNT(comp.id) >= 4 THEN
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY comp.sold_price)
            - PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY comp.sold_price)
        WHEN COUNT(comp.id) >= 2 THEN
            STDDEV(comp.sold_price)
        ELSE NULL
    END AS comp_price_spread,
    AVG(
        EXTRACT(EPOCH FROM (s.sold_date - comp.sold_date)) / 86400.0
    ) AS comp_avg_days_ago,
    MIN(
        ST_Distance(comp.location::geography, s.location::geography)
    ) AS comp_nearest_distance_m
FROM subjects s
LEFT JOIN LATERAL (
    SELECT c.id, c.sold_price, c.sqft, c.sold_date, c.location
    FROM redfin_listings c
    WHERE c.id != s.id
      AND c.listing_status = 'SOLD'
      AND c.sold_price IS NOT NULL
      AND c.sqft IS NOT NULL
      AND c.num_beds IS NOT NULL
      AND (s.sold_date IS NULL OR c.sold_date < s.sold_date)
      AND ST_DWithin(c.location::geography, s.location::geography, 3218)
      AND c.num_beds BETWEEN s.num_beds - 1 AND s.num_beds + 1
      AND c.sqft BETWEEN s.sqft * 0.8 AND s.sqft * 1.2
    ORDER BY ST_Distance(c.location::geography, s.location::geography)
    LIMIT 10
) comp ON TRUE
GROUP BY s.id, s.location, s.sold_date, s.sqft, s.num_beds, s.price_per_sqft
"""

FEATURE_COLUMNS = [
    "comp_median_ppsf",
    "comp_mean_adjusted_price",
    "comp_nearest_price",
    "comp_ppsf_ratio",
    "comp_count",
    "comp_price_spread",
    "comp_avg_days_ago",
    "comp_nearest_distance_m",
]

_CHUNK_SIZE = 500


def _build_filter_clause(property_ids: list[int] | None) -> str:
    """Return SQL filter clause for property IDs."""
    if property_ids is None:
        return ""
    return "AND id = ANY(:property_ids)"


def _build_params(property_ids: list[int] | None) -> dict[str, object]:
    """Build parameter dict for SQL queries."""
    params: dict[str, object] = {}
    if property_ids is not None:
        params["property_ids"] = property_ids
    return params


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


def _compute_derived(df: pd.DataFrame) -> pd.DataFrame:
    """Compute Python-side derived features after the SQL aggregation."""
    if df.empty:
        return df

    # comp_ppsf_ratio = subject_ppsf / comp_median_ppsf (NULL if either missing)
    df["comp_ppsf_ratio"] = df["subject_ppsf"] / df["comp_median_ppsf"]

    # Set comp_count to 0 (not NULL) when LEFT JOIN produced no comps
    df["comp_count"] = pd.to_numeric(df["comp_count"], errors="coerce").fillna(0).astype(int)

    # Drop the helper column
    df = df.drop(columns=["subject_ppsf"], errors="ignore")

    return df


def build_comparable_features(
    db: Session,
    *,
    property_ids: list[int] | None = None,
) -> pd.DataFrame:
    """Compute comparable-sales features for the given properties.

    Uses a spatial LATERAL JOIN to find the top 10 comps per property,
    then aggregates price signals, spread, freshness, and proximity.

    Returns a DataFrame indexed by property_id with 8 feature columns.
    """
    if property_ids is not None and len(property_ids) == 0:
        return _empty_frame()

    t0 = time.monotonic()

    if property_ids is not None and len(property_ids) > _CHUNK_SIZE:
        # Chunk large batches to avoid query planner issues
        chunks: list[pd.DataFrame] = []
        for i in range(0, len(property_ids), _CHUNK_SIZE):
            chunk_ids = property_ids[i : i + _CHUNK_SIZE]
            chunk_df = _run_query(db, chunk_ids)
            if not chunk_df.empty:
                chunks.append(chunk_df)
            logger.info(
                "Comp features chunk %d-%d: %d rows",
                i,
                min(i + _CHUNK_SIZE, len(property_ids)),
                len(chunk_df),
            )
        result = pd.concat(chunks) if chunks else _empty_frame()
    else:
        result = _run_query(db, property_ids)

    logger.info(
        "Comparable features: %d rows in %.1fs",
        len(result),
        time.monotonic() - t0,
    )
    return result


def _run_query(
    db: Session,
    property_ids: list[int] | None,
) -> pd.DataFrame:
    """Execute the comp features query and post-process."""
    filter_clause = _build_filter_clause(property_ids)
    params = _build_params(property_ids)

    sql = _COMP_FEATURES_SQL.format(filter_clause=filter_clause)
    df = _exec_query(db, sql, params)

    if df.empty:
        return _empty_frame()

    df = _compute_derived(df)
    df = df.set_index("property_id")
    return df.reindex(columns=FEATURE_COLUMNS)


def _empty_frame() -> pd.DataFrame:
    """Return an empty DataFrame with the expected feature columns."""
    return pd.DataFrame(columns=FEATURE_COLUMNS)

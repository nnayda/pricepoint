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
    # Cast to float — PostgreSQL returns NUMERIC aggregates as decimal.Decimal
    df["subject_ppsf"] = pd.to_numeric(df["subject_ppsf"], errors="coerce")
    df["comp_median_ppsf"] = pd.to_numeric(df["comp_median_ppsf"], errors="coerce")
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


_TRAINING_COMP_CHUNK_SIZE = 2000

# Bulk SQL: processes a chunk of sale events from the _comp_events temp table.
# Replaces the per-row correlated subquery for comp_nearest_price with
# ARRAY_AGG over the LATERAL result (comps are already distance-ordered).
_TRAINING_COMP_BULK_SQL = text("""
SELECT
    e.sale_event_id,
    COUNT(comp.id) AS comp_count,
    PERCENTILE_CONT(0.5) WITHIN GROUP (
        ORDER BY comp.sold_price / NULLIF(comp.sqft, 0)
    ) AS comp_median_ppsf,
    AVG(
        comp.sold_price
        + (e.sqft - comp.sqft) * (comp.sold_price / NULLIF(comp.sqft, 0))
    ) AS comp_mean_adjusted_price,
    (ARRAY_AGG(comp.sold_price ORDER BY comp.dist_m)
        FILTER (WHERE comp.id IS NOT NULL)
    )[1] AS comp_nearest_price,
    e.sold_price / NULLIF(e.sqft, 0) AS subject_ppsf,
    CASE
        WHEN COUNT(comp.id) >= 4 THEN
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY comp.sold_price)
            - PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY comp.sold_price)
        WHEN COUNT(comp.id) >= 2 THEN
            STDDEV(comp.sold_price)
        ELSE NULL
    END AS comp_price_spread,
    AVG(
        EXTRACT(EPOCH FROM (e.sale_date - comp.sold_date)) / 86400.0
    ) AS comp_avg_days_ago,
    MIN(comp.dist_m) AS comp_nearest_distance_m
FROM _comp_events e
JOIN redfin_listings l ON l.id = e.property_id AND l.location IS NOT NULL
LEFT JOIN LATERAL (
    SELECT c.id, c.sold_price, c.sqft, c.sold_date,
           ST_Distance(c.location::geography, l.location::geography) AS dist_m
    FROM redfin_listings c
    WHERE c.id != e.property_id
      AND c.listing_status = 'SOLD'
      AND c.sold_price IS NOT NULL
      AND c.sqft IS NOT NULL
      AND c.num_beds IS NOT NULL
      AND c.sold_date < e.sale_date
      AND ST_DWithin(c.location::geography, l.location::geography, 3218)
      AND c.num_beds BETWEEN e.num_beds - 1 AND e.num_beds + 1
      AND c.sqft BETWEEN e.sqft * 0.8 AND e.sqft * 1.2
    ORDER BY dist_m
    LIMIT 10
) comp ON TRUE
WHERE e.chunk_id = :chunk_id
GROUP BY e.sale_event_id, e.property_id, e.sale_date, e.sqft,
         e.num_beds, e.sold_price, l.location
""")


def build_training_comparable_features(
    db: Session,
    sale_events: pd.DataFrame,
) -> pd.DataFrame:
    """Compute comparable-sales features for each historical sale event.

    Uses a temp table and chunked bulk queries instead of per-row queries
    to eliminate ~48K DB round-trips.

    Parameters
    ----------
    db:
        SQLAlchemy session.
    sale_events:
        DataFrame with columns ``sale_event_id``, ``property_id``,
        ``sale_date``, ``sqft``, ``num_beds``, ``num_baths``, ``sold_price``.

    Returns
    -------
    pd.DataFrame
        Indexed by ``sale_event_id`` with 8 comp feature columns.
    """
    if sale_events.empty:
        return pd.DataFrame(columns=["sale_event_id"] + FEATURE_COLUMNS).set_index("sale_event_id")

    logger.info("Building training comp features for %d sale events...", len(sale_events))
    t0 = time.monotonic()

    # Separate events with/without required attributes
    has_attrs = sale_events["sqft"].notna() & sale_events["num_beds"].notna()
    valid_events = sale_events[has_attrs].copy()
    invalid_event_ids = sale_events.loc[~has_attrs, "sale_event_id"].tolist()

    result_chunks: list[pd.DataFrame] = []

    if not valid_events.empty:
        # Assign chunk IDs for batched processing
        valid_events["chunk_id"] = [
            i // _TRAINING_COMP_CHUNK_SIZE for i in range(len(valid_events))
        ]
        num_chunks = int(valid_events["chunk_id"].max()) + 1

        # Create temp table
        db.execute(text("DROP TABLE IF EXISTS _comp_events"))
        db.execute(
            text("""
            CREATE TEMP TABLE _comp_events (
                sale_event_id TEXT NOT NULL,
                property_id INTEGER NOT NULL,
                sale_date DATE NOT NULL,
                sqft DOUBLE PRECISION NOT NULL,
                num_beds INTEGER NOT NULL,
                sold_price DOUBLE PRECISION,
                chunk_id INTEGER NOT NULL
            )
        """)
        )

        # Prepare and bulk insert
        _cols = [
            "sale_event_id",
            "property_id",
            "sale_date",
            "sqft",
            "num_beds",
            "sold_price",
            "chunk_id",
        ]
        insert_df = valid_events[_cols].copy()
        insert_df["sale_event_id"] = insert_df["sale_event_id"].astype(str)
        insert_df["property_id"] = insert_df["property_id"].astype(int)
        insert_df["num_beds"] = insert_df["num_beds"].astype(int)
        insert_df["chunk_id"] = insert_df["chunk_id"].astype(int)
        if pd.api.types.is_datetime64_any_dtype(insert_df["sale_date"]):
            insert_df["sale_date"] = insert_df["sale_date"].dt.date
        # Replace NaN with None for DB compatibility
        insert_df = insert_df.where(pd.notna(insert_df), None)

        db.execute(
            text(
                "INSERT INTO _comp_events"
                " (sale_event_id, property_id, sale_date,"
                " sqft, num_beds, sold_price, chunk_id)"
                " VALUES (:sale_event_id, :property_id, :sale_date,"
                " :sqft, :num_beds, :sold_price, :chunk_id)"
            ),
            insert_df.to_dict("records"),
        )
        # Index for chunk filtering
        db.execute(text("CREATE INDEX ON _comp_events (chunk_id)"))

        logger.info(
            "  Inserted %d events into temp table (%d chunks of %d)",
            len(valid_events),
            num_chunks,
            _TRAINING_COMP_CHUNK_SIZE,
        )

        # Process each chunk
        for chunk_id in range(num_chunks):
            result = db.execute(_TRAINING_COMP_BULK_SQL, {"chunk_id": chunk_id})
            rows = result.fetchall()
            if rows:
                columns = list(result.keys())
                result_chunks.append(pd.DataFrame(rows, columns=columns))
            elapsed = time.monotonic() - t0
            done = min((chunk_id + 1) * _TRAINING_COMP_CHUNK_SIZE, len(valid_events))
            logger.info(
                "  Training comp features: %d/%d events, chunk %d/%d (%.1fs elapsed)",
                done,
                len(valid_events),
                chunk_id + 1,
                num_chunks,
                elapsed,
            )

        db.execute(text("DROP TABLE IF EXISTS _comp_events"))

    # Combine SQL results
    if result_chunks:
        df = pd.concat(result_chunks, ignore_index=True)
        df = _compute_derived(df)
    else:
        df = _empty_frame()
        df["sale_event_id"] = pd.Series(dtype=str)

    # Add null rows for events that lacked sqft/num_beds
    if invalid_event_ids:
        null_rows = {"sale_event_id": invalid_event_ids, "comp_count": [0] * len(invalid_event_ids)}
        for col in FEATURE_COLUMNS:
            if col != "comp_count":
                null_rows[col] = [None] * len(invalid_event_ids)
        df = pd.concat([df, pd.DataFrame(null_rows)], ignore_index=True)

    df = df.set_index("sale_event_id")
    df = df.reindex(columns=FEATURE_COLUMNS)

    logger.info(
        "Training comp features: %d rows in %.1fs",
        len(df),
        time.monotonic() - t0,
    )
    return df

"""Geospatial feature engineering.

Transforms raw geospatial data into model-ready features:
distance to nearest school, crime density within radius, nearby amenity counts, etc.
"""

from __future__ import annotations

import logging
import math

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

BATCH_SIZE = 100

# 2 miles in meters
TWO_MILES_M = 3218.0

_DISTANCE_SQL = """
WITH props AS (
    SELECT id AS property_id, location
    FROM redfin_listings
    WHERE location IS NOT NULL
    {filter_clause}
),
-- KNN distance features via CROSS JOIN LATERAL
dist_school AS (
    SELECT p.property_id,
           s.dist AS dist_nearest_school_m
    FROM props p
    CROSS JOIN LATERAL (
        SELECT ST_Distance(p.location::geography, s.location::geography) AS dist
        FROM schools s
        WHERE s.location IS NOT NULL
        ORDER BY p.location <-> s.location
        LIMIT 1
    ) s
),
dist_elementary AS (
    SELECT p.property_id,
           s.dist AS dist_nearest_elementary_m
    FROM props p
    CROSS JOIN LATERAL (
        SELECT ST_Distance(p.location::geography, s.location::geography) AS dist
        FROM schools s
        WHERE s.location IS NOT NULL AND s.school_type = 'Elementary'
        ORDER BY p.location <-> s.location
        LIMIT 1
    ) s
),
dist_middle AS (
    SELECT p.property_id,
           s.dist AS dist_nearest_middle_m
    FROM props p
    CROSS JOIN LATERAL (
        SELECT ST_Distance(p.location::geography, s.location::geography) AS dist
        FROM schools s
        WHERE s.location IS NOT NULL AND s.school_type = 'Middle'
        ORDER BY p.location <-> s.location
        LIMIT 1
    ) s
),
dist_high AS (
    SELECT p.property_id,
           s.dist AS dist_nearest_high_m
    FROM props p
    CROSS JOIN LATERAL (
        SELECT ST_Distance(p.location::geography, s.location::geography) AS dist
        FROM schools s
        WHERE s.location IS NOT NULL AND s.school_type = 'High'
        ORDER BY p.location <-> s.location
        LIMIT 1
    ) s
),
all_parks AS (
    SELECT ST_Centroid(geom) AS location, acres FROM wake_parks WHERE geom IS NOT NULL
    UNION ALL
    SELECT ST_Centroid(geom) AS location, map_acres AS acres
    FROM raleigh_parks WHERE geom IS NOT NULL
    UNION ALL
    SELECT geom AS location, park_area AS acres FROM cary_parks WHERE geom IS NOT NULL
),
dist_park AS (
    SELECT p.property_id,
           pk.dist AS dist_nearest_park_m
    FROM props p
    CROSS JOIN LATERAL (
        SELECT ST_Distance(p.location::geography, pk.location::geography) AS dist
        FROM all_parks pk
        ORDER BY p.location <-> pk.location
        LIMIT 1
    ) pk
),
all_greenways AS (
    SELECT geom FROM wake_greenways WHERE geom IS NOT NULL
    UNION ALL
    SELECT geom FROM raleigh_greenways WHERE geom IS NOT NULL
    UNION ALL
    SELECT geom FROM cary_greenways WHERE geom IS NOT NULL
),
dist_greenway AS (
    SELECT p.property_id,
           g.dist AS dist_nearest_greenway_m
    FROM props p
    CROSS JOIN LATERAL (
        SELECT ST_Distance(p.location::geography, g.geom::geography) AS dist
        FROM all_greenways g
        ORDER BY p.location <-> g.geom
        LIMIT 1
    ) g
),
dist_hospital AS (
    SELECT p.property_id,
           h.dist AS dist_nearest_hospital_m
    FROM props p
    CROSS JOIN LATERAL (
        SELECT ST_Distance(p.location::geography, h.geom::geography) AS dist
        FROM wake_hospitals h
        WHERE h.geom IS NOT NULL
        ORDER BY p.location <-> h.geom
        LIMIT 1
    ) h
),
dist_library AS (
    SELECT p.property_id,
           l.dist AS dist_nearest_library_m
    FROM props p
    CROSS JOIN LATERAL (
        SELECT ST_Distance(p.location::geography, l.geom::geography) AS dist
        FROM wake_libraries l
        WHERE l.geom IS NOT NULL
        ORDER BY p.location <-> l.geom
        LIMIT 1
    ) l
),
dist_highway AS (
    SELECT p.property_id,
           hw.dist AS dist_nearest_highway_m
    FROM props p
    CROSS JOIN LATERAL (
        SELECT ST_Distance(p.location::geography, hw.geom::geography) AS dist
        FROM wake_highways hw
        WHERE hw.geom IS NOT NULL
        ORDER BY p.location <-> hw.geom
        LIMIT 1
    ) hw
),
dist_railroad AS (
    SELECT p.property_id,
           rr.dist AS dist_nearest_railroad_m
    FROM props p
    CROSS JOIN LATERAL (
        SELECT ST_Distance(p.location::geography, rr.geom::geography) AS dist
        FROM wake_railroads rr
        WHERE rr.geom IS NOT NULL
        ORDER BY p.location <-> rr.geom
        LIMIT 1
    ) rr
)
SELECT
    p.property_id,
    ds.dist_nearest_school_m,
    de.dist_nearest_elementary_m,
    dm.dist_nearest_middle_m,
    dh.dist_nearest_high_m,
    dp.dist_nearest_park_m,
    dg.dist_nearest_greenway_m,
    dho.dist_nearest_hospital_m,
    dl.dist_nearest_library_m,
    dhw.dist_nearest_highway_m,
    dr.dist_nearest_railroad_m
FROM props p
LEFT JOIN dist_school ds ON ds.property_id = p.property_id
LEFT JOIN dist_elementary de ON de.property_id = p.property_id
LEFT JOIN dist_middle dm ON dm.property_id = p.property_id
LEFT JOIN dist_high dh ON dh.property_id = p.property_id
LEFT JOIN dist_park dp ON dp.property_id = p.property_id
LEFT JOIN dist_greenway dg ON dg.property_id = p.property_id
LEFT JOIN dist_hospital dho ON dho.property_id = p.property_id
LEFT JOIN dist_library dl ON dl.property_id = p.property_id
LEFT JOIN dist_highway dhw ON dhw.property_id = p.property_id
LEFT JOIN dist_railroad dr ON dr.property_id = p.property_id
"""

_AGGREGATE_SQL = """
WITH props AS (
    SELECT id AS property_id, location
    FROM redfin_listings
    WHERE location IS NOT NULL
    {filter_clause}
),
school_agg AS (
    SELECT
        p.property_id,
        AVG(s.rating) AS avg_school_rating_2mi,
        COUNT(*) AS count_schools_2mi
    FROM props p
    JOIN schools s ON s.location IS NOT NULL
        AND ST_DWithin(p.location::geography, s.location::geography, :two_miles_m)
    GROUP BY p.property_id
),
all_crimes AS (
    SELECT location, date_from AS occurred_at FROM staging_cary_police_incidents
        WHERE location IS NOT NULL
    UNION ALL
    SELECT location, reported_date AS occurred_at FROM staging_raleigh_police_incidents
        WHERE location IS NOT NULL
    UNION ALL
    SELECT location, CASE
        WHEN date_occu IS NOT NULL AND date_occu != '' THEN date_occu::timestamp
        ELSE NULL
    END AS occurred_at FROM staging_morrisville_police_incidents
        WHERE location IS NOT NULL
),
crime_agg AS (
    SELECT
        p.property_id,
        COUNT(*) FILTER (WHERE ST_DWithin(p.location::geography, c.location::geography, 500))
            AS crime_count_500m_1yr,
        COUNT(*) FILTER (WHERE ST_DWithin(p.location::geography, c.location::geography, 1000))
            AS crime_count_1km_1yr,
        COUNT(*) FILTER (WHERE ST_DWithin(p.location::geography, c.location::geography, 2000))
            AS crime_count_2km_1yr
    FROM props p
    CROSS JOIN all_crimes c
    WHERE c.occurred_at >= (NOW() - INTERVAL '1 year')
        AND ST_DWithin(p.location::geography, c.location::geography, 2000)
    GROUP BY p.property_id
),
park_centroids AS (
    SELECT ST_Centroid(geom) AS location, acres FROM wake_parks WHERE geom IS NOT NULL
    UNION ALL
    SELECT ST_Centroid(geom) AS location, map_acres AS acres
    FROM raleigh_parks WHERE geom IS NOT NULL
    UNION ALL
    SELECT geom AS location, park_area AS acres FROM cary_parks WHERE geom IS NOT NULL
),
park_agg AS (
    SELECT
        p.property_id,
        COUNT(*) AS count_parks_2km,
        COALESCE(SUM(pk.acres), 0) AS total_park_acres_2km
    FROM props p
    JOIN park_centroids pk ON ST_DWithin(p.location::geography, pk.location::geography, 2000)
    GROUP BY p.property_id
)
SELECT
    p.property_id,
    sa.avg_school_rating_2mi,
    COALESCE(sa.count_schools_2mi, 0) AS count_schools_2mi,
    COALESCE(ca.crime_count_500m_1yr, 0) AS crime_count_500m_1yr,
    COALESCE(ca.crime_count_1km_1yr, 0) AS crime_count_1km_1yr,
    COALESCE(ca.crime_count_2km_1yr, 0) AS crime_count_2km_1yr,
    COALESCE(pa.count_parks_2km, 0) AS count_parks_2km,
    COALESCE(pa.total_park_acres_2km, 0) AS total_park_acres_2km
FROM props p
LEFT JOIN school_agg sa ON sa.property_id = p.property_id
LEFT JOIN crime_agg ca ON ca.property_id = p.property_id
LEFT JOIN park_agg pa ON pa.property_id = p.property_id
"""

_CONTAINMENT_SQL = """
WITH props AS (
    SELECT id AS property_id, location
    FROM redfin_listings
    WHERE location IS NOT NULL
    {filter_clause}
)
SELECT
    p.property_id,
    tt.geoid AS census_tract_geoid,
    bg.geoid AS census_block_group_geoid,
    ws.name AS subdivision_name,
    CASE WHEN ue.ue_exists THEN true ELSE false END AS has_utility_easement_100m
FROM props p
LEFT JOIN LATERAL (
    SELECT geoid FROM tiger_tracts t
    WHERE ST_Contains(t.geom, p.location)
    LIMIT 1
) tt ON true
LEFT JOIN LATERAL (
    SELECT geoid FROM tiger_block_groups b
    WHERE ST_Contains(b.geom, p.location)
    LIMIT 1
) bg ON true
LEFT JOIN LATERAL (
    SELECT name FROM wake_subdivisions s
    WHERE ST_Contains(s.geom, p.location)
    LIMIT 1
) ws ON true
LEFT JOIN LATERAL (
    SELECT true AS ue_exists FROM wake_utility_easements u
    WHERE ST_DWithin(p.location::geography, u.geom::geography, 100)
    LIMIT 1
) ue ON true
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


def build_geospatial_features(
    db: Session,
    *,
    property_ids: list[int] | None = None,
) -> pd.DataFrame:
    """Compute geospatial features for the given properties.

    Queries PostGIS for distance, count/aggregate, containment, and LLM score
    features. Processes in batches of 100 properties when property_ids is
    provided.

    Returns a DataFrame indexed by property_id with 24 feature columns.
    """
    if property_ids is not None and len(property_ids) == 0:
        return _empty_frame()

    # If we have a large list of IDs, process in batches
    if property_ids is not None and len(property_ids) > BATCH_SIZE:
        frames: list[pd.DataFrame] = []
        for start in range(0, len(property_ids), BATCH_SIZE):
            batch = property_ids[start : start + BATCH_SIZE]
            frames.append(_query_batch(db, batch))
        return pd.concat(frames)
    else:
        return _query_batch(db, property_ids)


def _query_batch(
    db: Session,
    property_ids: list[int] | None,
) -> pd.DataFrame:
    """Execute all four query groups for a single batch and merge results."""
    filter_clause = _build_filter_clause(property_ids)

    # Distance features
    dist_df = _exec_query(
        db,
        _DISTANCE_SQL.format(filter_clause=filter_clause),
        _build_params(property_ids),
    )

    # Aggregate features (school ratings, crime counts, park counts)
    agg_df = _exec_query(
        db,
        _AGGREGATE_SQL.format(filter_clause=filter_clause),
        _build_params(property_ids, {"two_miles_m": TWO_MILES_M}),
    )

    # Containment features (census tract, block group, subdivision, easement)
    contain_df = _exec_query(
        db,
        _CONTAINMENT_SQL.format(filter_clause=filter_clause),
        _build_params(property_ids),
    )

    # LLM scores
    llm_df = _exec_query(
        db,
        _LLM_SCORES_SQL.format(filter_clause=filter_clause),
        _build_params(property_ids),
    )

    # Merge all DataFrames on property_id
    result = dist_df
    for other in (agg_df, contain_df, llm_df):
        if not other.empty:
            result = result.merge(other, on="property_id", how="left")

    if result.empty:
        return _empty_frame()

    # Compute derived feature: crime density per km^2 within 1km radius
    result["crime_density_1km"] = result["crime_count_1km_1yr"] / (math.pi * 1.0**2)

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
    "dist_nearest_library_m",
    "dist_nearest_highway_m",
    "dist_nearest_railroad_m",
    "avg_school_rating_2mi",
    "count_schools_2mi",
    "crime_count_500m_1yr",
    "crime_count_1km_1yr",
    "crime_count_2km_1yr",
    "crime_density_1km",
    "count_parks_2km",
    "total_park_acres_2km",
    "census_tract_geoid",
    "census_block_group_geoid",
    "subdivision_name",
    "has_utility_easement_100m",
    "llm_description_score",
    "llm_photo_score",
]

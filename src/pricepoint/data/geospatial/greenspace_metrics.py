"""Precompute greenspace metrics at TIGER geographic levels.

Computes park/trail counts, area ratios, population-normalised metrics,
and z-scores relative to peer regions for block_group, tract,
county_subdivision, and county.
"""

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from pricepoint.db.models import GreenspaceRegionMetric

logger = logging.getLogger(__name__)

# Map geo_level → (TIGER table name, geoid column, namelsad column, aland column)
GEO_LEVEL_CONFIG: dict[str, dict[str, str]] = {
    "block_group": {
        "table": "block_groups",
        "geoid": "geoid",
        "name": "namelsad",
        "aland": "aland",
        "geom": "geom",
    },
    "tract": {
        "table": "tracts",
        "geoid": "geoid",
        "name": "namelsad",
        "aland": "aland",
        "geom": "geom",
    },
    "county_subdivision": {
        "table": "townships",
        "geoid": "geoid",
        "name": "namelsad",
        "aland": "aland",
        "geom": "geom",
    },
    "county": {
        "table": "counties",
        "geoid": "geoid",
        "name": "namelsad",
        "aland": "aland",
        "geom": "geom",
    },
}

# Parent prefix length for z-score grouping
ZSCORE_PARENT_PREFIX: dict[str, int] = {
    "block_group": 5,  # county prefix
    "tract": 5,
    "county_subdivision": 5,
    "county": 2,  # state prefix
}


def compute_base_metrics(
    session: Session,
    geo_level: str,
) -> int:
    """Compute raw greenspace metrics for a geographic level.

    Joins TIGER regions with greenspaces/trails via ST_Intersects, computes
    clipped areas/lengths, and upserts rows into greenspace_region_metrics.
    Processes all boundaries present in the database.

    Returns the number of rows inserted.
    """
    cfg = GEO_LEVEL_CONFIG[geo_level]
    tiger_table = cfg["table"]
    geoid_col = cfg["geoid"]
    name_col = cfg["name"]
    aland_col = cfg["aland"]
    geom_col = cfg["geom"]

    sql = text(f"""
        WITH parks AS (
            SELECT
                t.{geoid_col} AS geoid,
                COUNT(DISTINCT g.id) AS park_count,
                COALESCE(SUM(
                    ST_Area(ST_Intersection(t.{geom_col}, g.geom)::geography)
                ), 0) AS greenspace_area_sqm,
                COALESCE(SUM(
                    ST_Area(ST_Intersection(t.{geom_col}, g.geom)::geography) / 4046.8564224
                ), 0) AS total_park_acres
            FROM {tiger_table} t
            LEFT JOIN greenspaces g ON ST_Intersects(t.{geom_col}, g.geom)
            GROUP BY t.{geoid_col}
        ),
        trail_metrics AS (
            SELECT
                t.{geoid_col} AS geoid,
                COUNT(DISTINCT tr.id) AS trail_count,
                COALESCE(SUM(
                    ST_Length(ST_Intersection(t.{geom_col}, tr.geom)::geography) / 1609.344
                ), 0) AS total_trail_miles
            FROM {tiger_table} t
            LEFT JOIN trails tr ON ST_Intersects(t.{geom_col}, tr.geom)
            GROUP BY t.{geoid_col}
        )
        SELECT
            t.{geoid_col} AS geoid,
            t.{name_col} AS name,
            COALESCE(p.park_count, 0) AS park_count,
            COALESCE(tm.trail_count, 0) AS trail_count,
            COALESCE(p.total_park_acres, 0) AS total_park_acres,
            COALESCE(tm.total_trail_miles, 0) AS total_trail_miles,
            COALESCE(p.greenspace_area_sqm, 0) AS greenspace_area_sqm,
            COALESCE(t.{aland_col}, 0) AS region_land_area_sqm,
            CASE
                WHEN COALESCE(t.{aland_col}, 0) > 0
                THEN COALESCE(p.greenspace_area_sqm, 0)::float / t.{aland_col}
                ELSE NULL
            END AS greenspace_ratio
        FROM {tiger_table} t
        LEFT JOIN parks p ON p.geoid = t.{geoid_col}
        LEFT JOIN trail_metrics tm ON tm.geoid = t.{geoid_col}
    """)

    rows = session.execute(sql).fetchall()
    logger.info("Computed %d %s rows from TIGER/greenspace join", len(rows), geo_level)

    # Delete existing rows for this geo_level, then bulk insert
    session.query(GreenspaceRegionMetric).filter(
        GreenspaceRegionMetric.geo_level == geo_level
    ).delete()

    new_rows = []
    for r in rows:
        new_rows.append(
            GreenspaceRegionMetric(
                geo_level=geo_level,
                geoid=r.geoid,
                name=r.name,
                park_count=r.park_count,
                trail_count=r.trail_count,
                total_park_acres=round(r.total_park_acres, 2),
                total_trail_miles=round(r.total_trail_miles, 2),
                greenspace_area_sqm=round(r.greenspace_area_sqm, 2),
                region_land_area_sqm=r.region_land_area_sqm,
                greenspace_ratio=round(r.greenspace_ratio, 6) if r.greenspace_ratio else None,
            )
        )
    session.bulk_save_objects(new_rows)
    session.flush()
    return len(new_rows)


def enrich_population(session: Session, geo_level: str) -> int:
    """Join ACS demographics to set population and per-capita metrics.

    Uses the latest acs_year available for the matching geography_level.
    Returns the number of rows updated.
    """
    # Map our geo_level names to ACS geography_level names
    acs_level = geo_level  # they match for block_group, tract, county_subdivision, county

    sql = text("""
        UPDATE greenspace_region_metrics grm
        SET
            population = acs.total_population,
            parks_per_1k_residents = CASE
                WHEN COALESCE(acs.total_population, 0) > 0
                THEN grm.park_count * 1000.0 / acs.total_population
                ELSE NULL
            END,
            greenspace_acres_per_1k_residents = CASE
                WHEN COALESCE(acs.total_population, 0) > 0
                THEN grm.total_park_acres * 1000.0 / acs.total_population
                ELSE NULL
            END
        FROM acs_demographics acs
        WHERE grm.geo_level = :geo_level
          AND acs.geography_level = :acs_level
          AND acs.geoid = grm.geoid
          AND acs.acs_year = (
              SELECT MAX(a2.acs_year)
              FROM acs_demographics a2
              WHERE a2.geography_level = :acs_level
          )
    """)

    result = session.execute(sql, {"geo_level": geo_level, "acs_level": acs_level})
    count = result.rowcount  # type: ignore[attr-defined]
    session.flush()
    logger.info("Enriched %d %s rows with ACS population data", count, geo_level)
    return count


def compute_zscores(session: Session, geo_level: str) -> int:
    """Compute z-scores for all metric columns using window functions.

    Groups by parent geography prefix (county for sub-county levels,
    state for county level).

    Returns the number of rows updated.
    """
    prefix_len = ZSCORE_PARENT_PREFIX[geo_level]

    # Build z-score expressions for each metric
    zscore_cols = [
        ("greenspace_ratio", "greenspace_ratio_zscore"),
        ("park_count", "park_count_zscore"),
        ("trail_count", "trail_count_zscore"),
        ("total_park_acres", "total_park_acres_zscore"),
        ("total_trail_miles", "total_trail_miles_zscore"),
        ("parks_per_1k_residents", "parks_per_1k_zscore"),
        ("greenspace_acres_per_1k_residents", "greenspace_acres_per_1k_zscore"),
    ]

    set_clauses = []
    for _src, dest in zscore_cols:
        set_clauses.append(f"{dest} = z.{dest}")

    select_clauses = []
    for src, dest in zscore_cols:
        select_clauses.append(f"""
            CASE
                WHEN STDDEV_POP({src}) OVER (PARTITION BY LEFT(geoid, {prefix_len})) > 0
                THEN ({src} - AVG({src}) OVER (PARTITION BY LEFT(geoid, {prefix_len})))
                     / STDDEV_POP({src}) OVER (PARTITION BY LEFT(geoid, {prefix_len}))
                ELSE 0
            END AS {dest}""")

    sql = text(f"""
        UPDATE greenspace_region_metrics grm
        SET {", ".join(set_clauses)}
        FROM (
            SELECT
                id,
                {", ".join(select_clauses)}
            FROM greenspace_region_metrics
            WHERE geo_level = :geo_level
        ) z
        WHERE grm.id = z.id
    """)

    result = session.execute(sql, {"geo_level": geo_level})
    count = result.rowcount  # type: ignore[attr-defined]
    session.flush()
    logger.info("Computed z-scores for %d %s rows", count, geo_level)
    return count


def verify_metrics(session: Session) -> None:
    """Verify that all geo levels have rows and z-scores populated.

    Raises AssertionError if any level is missing data.
    """
    for geo_level in GEO_LEVEL_CONFIG:
        count = (
            session.query(GreenspaceRegionMetric)
            .filter(GreenspaceRegionMetric.geo_level == geo_level)
            .count()
        )
        assert count > 0, f"No greenspace_region_metrics rows for geo_level={geo_level}"

        zscore_count = (
            session.query(GreenspaceRegionMetric)
            .filter(
                GreenspaceRegionMetric.geo_level == geo_level,
                GreenspaceRegionMetric.greenspace_ratio_zscore.isnot(None),
            )
            .count()
        )
        assert zscore_count > 0, f"No z-scores populated for geo_level={geo_level}"

    logger.info("Greenspace region metrics verification passed")

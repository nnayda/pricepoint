"""Build the property_geo_lookups gold table.

Precomputes geographic containment (census tract, block group, county
subdivision, noise zone, risk zone, school district) and distance metrics
(nearest school, park, greenway, hospital) plus school averages for every
property with a location.  Replaces repeated ST_Contains and KNN queries at
API / ML feature-engineering time with indexed lookups.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from pricepoint.db.models import PropertyGeoLookup, RedfinListing

logger = logging.getLogger(__name__)

_INSERT_COLUMNS = """\
    property_id,
    census_tract_geoid,
    census_block_group_geoid,
    county_subdivision_geoid,
    county_geoid,
    subdivision_id,
    subdivision_name,
    in_noise_zone,
    noise_max_db,
    noise_source_layers,
    in_risk_zone,
    risk_max_severity,
    risk_types,
    school_district_geoid,
    dist_nearest_school_m,
    dist_nearest_elementary_m,
    dist_nearest_middle_m,
    dist_nearest_high_m,
    dist_nearest_park_m,
    dist_nearest_greenway_m,
    dist_nearest_hospital_m,
    avg_school_rating,
    avg_school_drive,
    in_critical_risk_zone"""

_SELECT_COLUMNS = """\
    p.id,
    tt.geoid,
    bg.geoid,
    cs.geoid,
    co.geoid,
    sd.id,
    sd.name,
    COALESCE(nz.in_noise, false),
    nz.max_db,
    nz.source_layers,
    COALESCE(rz.in_risk, false),
    rz.max_severity,
    rz.risk_types,
    scd.geoid,
    ds_any.dist_m,
    ds_elem.dist_m,
    ds_mid.dist_m,
    ds_high.dist_m,
    dp.dist_m,
    dg.dist_m,
    dh.dist_m,
    sa.avg_rating,
    sa.avg_drive,
    CASE WHEN rz.max_severity = 'critical' THEN true ELSE false END"""

_LATERALS = """\
LEFT JOIN LATERAL (
    SELECT t.geoid FROM tracts t
    WHERE ST_Contains(t.geom, p.location)
    LIMIT 1
) tt ON true
LEFT JOIN LATERAL (
    SELECT b.geoid FROM block_groups b
    WHERE ST_Contains(b.geom, p.location)
    LIMIT 1
) bg ON true
LEFT JOIN LATERAL (
    SELECT cs.geoid FROM townships cs
    WHERE ST_Contains(cs.geom, p.location)
    LIMIT 1
) cs ON true
LEFT JOIN LATERAL (
    SELECT co.geoid FROM counties co
    WHERE ST_Contains(co.geom, p.location)
    LIMIT 1
) co ON true
LEFT JOIN LATERAL (
    SELECT s.id, s.name FROM subdivisions s
    WHERE ST_Contains(s.geom, p.location)
    LIMIT 1
) sd ON true
LEFT JOIN LATERAL (
    SELECT
        true AS in_noise,
        MAX(n.noise_max_db) AS max_db,
        jsonb_agg(DISTINCT n.source_layer) AS source_layers
    FROM noises n
    WHERE ST_Intersects(n.geom, p.location)
    HAVING COUNT(*) > 0
) nz ON true
LEFT JOIN LATERAL (
    SELECT
        true AS in_risk,
        CASE WHEN bool_or(rb.severity = 'critical')
             THEN 'critical' ELSE 'caution'
        END AS max_severity,
        jsonb_agg(DISTINCT rb.infrastructure_type) AS risk_types
    FROM risk_boundaries rb
    WHERE ST_Contains(rb.geom, p.location)
    HAVING COUNT(*) > 0
) rz ON true
LEFT JOIN LATERAL (
    SELECT d.geoid FROM school_districts d
    WHERE ST_Contains(d.geom, p.location)
    LIMIT 1
) scd ON true
LEFT JOIN LATERAL (
    SELECT ST_Distance(p.location::geography, s.location::geography) AS dist_m
    FROM schools s
    WHERE s.location IS NOT NULL
    ORDER BY p.location <-> s.location
    LIMIT 1
) ds_any ON true
LEFT JOIN LATERAL (
    SELECT ST_Distance(p.location::geography, s.location::geography) AS dist_m
    FROM schools s
    WHERE s.location IS NOT NULL AND s.school_type = 'Elementary'
    ORDER BY p.location <-> s.location
    LIMIT 1
) ds_elem ON true
LEFT JOIN LATERAL (
    SELECT ST_Distance(p.location::geography, s.location::geography) AS dist_m
    FROM schools s
    WHERE s.location IS NOT NULL AND s.school_type = 'Middle'
    ORDER BY p.location <-> s.location
    LIMIT 1
) ds_mid ON true
LEFT JOIN LATERAL (
    SELECT ST_Distance(p.location::geography, s.location::geography) AS dist_m
    FROM schools s
    WHERE s.location IS NOT NULL AND s.school_type = 'High'
    ORDER BY p.location <-> s.location
    LIMIT 1
) ds_high ON true
LEFT JOIN LATERAL (
    SELECT ST_Distance(p.location::geography, pk.geom::geography) AS dist_m
    FROM greenspaces pk
    WHERE ST_DWithin(p.location, pk.geom, 0.2)
    ORDER BY p.location <-> pk.geom
    LIMIT 1
) dp ON true
LEFT JOIN LATERAL (
    SELECT ST_Distance(p.location::geography, g.geom::geography) AS dist_m
    FROM trails g
    WHERE ST_DWithin(p.location, g.geom, 0.2)
    ORDER BY p.location <-> g.geom
    LIMIT 1
) dg ON true
LEFT JOIN LATERAL (
    SELECT ST_Distance(p.location::geography, h.geom::geography) AS dist_m
    FROM hospitals h
    WHERE ST_DWithin(p.location, h.geom, 0.5)
    ORDER BY p.location <-> h.geom
    LIMIT 1
) dh ON true
LEFT JOIN LATERAL (
    SELECT
        AVG(s.rating) AS avg_rating,
        AVG(ps.drive_minutes) AS avg_drive
    FROM property_schools ps
    JOIN schools s ON s.id = ps.school_id
    WHERE ps.property_id = p.id AND ps.assigned = true
    HAVING COUNT(*) > 0
) sa ON true"""

_FULL_BUILD_SQL = text(f"""
INSERT INTO property_geo_lookups (
{_INSERT_COLUMNS}
)
SELECT
{_SELECT_COLUMNS}
FROM redfin_listings p
{_LATERALS}
WHERE p.location IS NOT NULL
""")

_INCREMENTAL_SQL = text(f"""
INSERT INTO property_geo_lookups (
{_INSERT_COLUMNS}
)
SELECT
{_SELECT_COLUMNS}
FROM redfin_listings p
{_LATERALS}
WHERE p.location IS NOT NULL
  AND p.id = ANY(:property_ids)
""")


def build_property_geo_lookups(session: Session) -> int:
    """Full rebuild: TRUNCATE + INSERT all property geo lookups.

    Returns the number of rows inserted.
    """
    logger.info("Starting full build of property_geo_lookups")
    session.execute(text("TRUNCATE TABLE property_geo_lookups"))
    result = session.execute(_FULL_BUILD_SQL)
    count = result.rowcount  # type: ignore[attr-defined]
    session.commit()
    logger.info("Built %d property geo lookups", count)
    return count  # type: ignore[return-value]


def build_incremental(session: Session, property_ids: list[int]) -> int:
    """Incremental update: DELETE + INSERT for specific property IDs.

    Returns the number of rows inserted.
    """
    if not property_ids:
        return 0

    logger.info("Incremental geo lookup build for %d properties", len(property_ids))

    # Delete existing rows for these properties
    session.execute(
        text("DELETE FROM property_geo_lookups WHERE property_id = ANY(:property_ids)"),
        {"property_ids": property_ids},
    )

    result = session.execute(_INCREMENTAL_SQL, {"property_ids": property_ids})
    count = result.rowcount  # type: ignore[attr-defined]
    session.commit()
    logger.info("Inserted %d incremental geo lookups", count)
    return count


def verify_geo_lookups(session: Session) -> dict[str, int]:
    """Verify coverage of property_geo_lookups vs redfin_listings.

    Returns dict with counts for total properties, lookup rows, and coverage
    of each boundary type.
    """
    total_props = session.scalar(
        select(func.count(RedfinListing.id)).where(RedfinListing.location.isnot(None))
    )
    total_lookups = session.scalar(select(func.count(PropertyGeoLookup.id)))

    tract_count = session.scalar(
        select(func.count(PropertyGeoLookup.id)).where(
            PropertyGeoLookup.census_tract_geoid.isnot(None)
        )
    )
    bg_count = session.scalar(
        select(func.count(PropertyGeoLookup.id)).where(
            PropertyGeoLookup.census_block_group_geoid.isnot(None)
        )
    )
    noise_count = session.scalar(
        select(func.count(PropertyGeoLookup.id)).where(PropertyGeoLookup.in_noise_zone.is_(True))
    )
    risk_count = session.scalar(
        select(func.count(PropertyGeoLookup.id)).where(PropertyGeoLookup.in_risk_zone.is_(True))
    )
    school_dist_count = session.scalar(
        select(func.count(PropertyGeoLookup.id)).where(
            PropertyGeoLookup.dist_nearest_school_m.isnot(None)
        )
    )
    park_dist_count = session.scalar(
        select(func.count(PropertyGeoLookup.id)).where(
            PropertyGeoLookup.dist_nearest_park_m.isnot(None)
        )
    )
    critical_count = session.scalar(
        select(func.count(PropertyGeoLookup.id)).where(
            PropertyGeoLookup.in_critical_risk_zone.is_(True)
        )
    )

    stats = {
        "total_properties": total_props or 0,
        "total_lookups": total_lookups or 0,
        "with_tract": tract_count or 0,
        "with_block_group": bg_count or 0,
        "in_noise_zone": noise_count or 0,
        "in_risk_zone": risk_count or 0,
        "with_school_dist": school_dist_count or 0,
        "with_park_dist": park_dist_count or 0,
        "in_critical_risk_zone": critical_count or 0,
    }

    missing = stats["total_properties"] - stats["total_lookups"]
    if missing > 0:
        logger.warning("Coverage gap: %d properties with location lack geo lookups", missing)
    else:
        logger.info(
            "Full coverage: %d lookups for %d properties",
            stats["total_lookups"],
            stats["total_properties"],
        )

    return stats

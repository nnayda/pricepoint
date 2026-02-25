"""Collect Overture Maps Places into PostGIS.

Downloads commercial POIs from the Overture Maps GeoParquet dataset on S3
using DuckDB, filters by confidence threshold, and bulk-loads into PostGIS
using truncate-and-reload.
"""

import logging

import duckdb
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import delete, func, select

from pricepoint.config.settings import get_settings
from pricepoint.db import SessionLocal
from pricepoint.db.models import Place

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000


def _map_overture_row(row: tuple) -> Place:
    """Map a DuckDB result row to a Place model instance.

    Row columns (by index):
        0: id, 1: name, 2: category, 3: alternate_categories,
        4: confidence, 5: operating_status,
        6: address, 7: city, 8: state, 9: postcode, 10: country,
        11: brand_name, 12: brand_wikidata,
        13: website, 14: phone, 15: email, 16: social,
        17: source_dataset, 18: source_record_id,
        19: longitude, 20: latitude
    """
    lon = row[19]
    lat = row[20]
    geom = None
    if lon is not None and lat is not None:
        try:
            geom = from_shape(Point(float(lon), float(lat)), srid=4326)
        except (TypeError, ValueError):
            geom = None

    return Place(
        source_id=row[0],
        name=row[1],
        category=row[2],
        alternate_categories=row[3],
        confidence=row[4],
        operating_status=row[5],
        address=row[6],
        city=row[7],
        state=row[8],
        postcode=row[9],
        country=row[10],
        brand_name=row[11],
        brand_wikidata=row[12],
        website=row[13],
        phone=row[14],
        email=row[15],
        social=row[16],
        source_dataset=row[17],
        source_record_id=row[18],
        geom=geom,
    )


def _build_query(s3_path: str, min_confidence: float) -> str:
    """Build the DuckDB SQL query for Overture Places GeoParquet."""
    return f"""
        SELECT
            id,
            names.primary AS name,
            categories.primary AS category,
            categories.alternate AS alternate_categories,
            confidence,
            operating_status,
            addresses[1].freeform AS address,
            addresses[1].locality AS city,
            addresses[1].region AS state,
            addresses[1].postcode AS postcode,
            addresses[1].country AS country,
            brand.names.primary[1] AS brand_name,
            brand.wikidata AS brand_wikidata,
            websites[1] AS website,
            phones[1] AS phone,
            emails[1] AS email,
            socials[1] AS social,
            sources[1].dataset AS source_dataset,
            sources[1].record_id AS source_record_id,
            ST_X(geometry) AS longitude,
            ST_Y(geometry) AS latitude
        FROM read_parquet('{s3_path}', hive_partitioning=true)
        WHERE confidence >= {min_confidence}
    """


def fetch_places() -> None:
    """Fetch Overture Places from S3 GeoParquet and load into PostGIS."""
    settings = get_settings()
    s3_path = settings.overture_places_s3_path
    min_confidence = settings.overture_places_min_confidence

    logger.info(
        "Starting places load from %s (min_confidence=%.2f)",
        s3_path,
        min_confidence,
    )

    con = duckdb.connect()
    try:
        con.execute("INSTALL spatial; LOAD spatial;")
        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute("SET s3_region='us-west-2';")

        query = _build_query(s3_path, min_confidence)
        result = con.execute(query)

        session = SessionLocal()
        try:
            session.execute(delete(Place))
            session.commit()

            total = 0
            while True:
                rows = result.fetchmany(BATCH_SIZE)
                if not rows:
                    break

                records = [_map_overture_row(r) for r in rows]
                session.add_all(records)
                session.commit()

                total += len(records)
                logger.info("Loaded %d places records (total: %d)", len(records), total)

            logger.info("Places load complete: %d records", total)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    finally:
        con.close()


def verify_places() -> None:
    """Verify that place records were loaded."""
    session = SessionLocal()
    try:
        count = session.execute(select(func.count()).select_from(Place)).scalar()
        if not count:
            raise RuntimeError("No records found in places after load")
        logger.info("Verified %d records in places", count)
    finally:
        session.close()

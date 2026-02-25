"""Collect Overture Maps Places into PostGIS.

Downloads commercial POIs from the Overture Maps GeoParquet dataset on S3
using DuckDB, filters by country and confidence threshold, and loads into
PostGIS using a staging + upsert swap pattern.
"""

import logging
from datetime import UTC, datetime

import duckdb
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import delete, func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from pricepoint.config.settings import get_settings
from pricepoint.db import SessionLocal
from pricepoint.db.models import Place, StagingPlace

logger = logging.getLogger(__name__)

BATCH_SIZE = 5000

# Columns upserted from staging into production (everything except id/source_id).
_UPDATABLE_COLUMNS = [
    "name",
    "category",
    "alternate_categories",
    "confidence",
    "operating_status",
    "address",
    "city",
    "state",
    "postcode",
    "country",
    "brand_name",
    "brand_wikidata",
    "website",
    "phone",
    "email",
    "social",
    "source_dataset",
    "source_record_id",
    "geom",
]


def _clean_str(value: str | None) -> str | None:
    """Strip NUL (0x00) characters that PostgreSQL rejects in text fields."""
    if value is None:
        return None
    return value.replace("\x00", "")


def _clean_str_list(value: list[str] | None) -> list[str] | None:
    """Strip NUL characters from each element of a string list."""
    if value is None:
        return None
    return [v.replace("\x00", "") for v in value]


def _row_to_dict(row: tuple) -> dict:
    """Convert a DuckDB result row to a dict for Core insert.

    Applies NUL-byte cleaning.  Row column order matches _build_query SELECT.

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

    return {
        "source_id": _clean_str(row[0]),
        "name": _clean_str(row[1]),
        "category": _clean_str(row[2]),
        "alternate_categories": _clean_str_list(row[3]),
        "confidence": row[4],
        "operating_status": _clean_str(row[5]),
        "address": _clean_str(row[6]),
        "city": _clean_str(row[7]),
        "state": _clean_str(row[8]),
        "postcode": _clean_str(row[9]),
        "country": _clean_str(row[10]),
        "brand_name": _clean_str(row[11]),
        "brand_wikidata": _clean_str(row[12]),
        "website": _clean_str(row[13]),
        "phone": _clean_str(row[14]),
        "email": _clean_str(row[15]),
        "social": _clean_str(row[16]),
        "source_dataset": _clean_str(row[17]),
        "source_record_id": _clean_str(row[18]),
        "geom": geom,
    }


def _build_query(s3_path: str, min_confidence: float, country: str) -> str:
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
            AND addresses[1].country = '{country}'
    """


def _load_staging(con: duckdb.DuckDBPyConnection, query: str) -> int:
    """Stream DuckDB results into the staging_places table.

    Returns the total number of rows loaded.
    """
    result = con.execute(query)
    session = SessionLocal()
    try:
        session.execute(delete(StagingPlace))
        session.commit()

        total = 0
        while True:
            rows = result.fetchmany(BATCH_SIZE)
            if not rows:
                break

            records = [_row_to_dict(r) for r in rows]
            session.execute(insert(StagingPlace), records)
            session.commit()

            total += len(records)
            logger.info("Staged %d places records (total: %d)", len(records), total)

        logger.info("Staging complete: %d records", total)
        return total
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _promote_to_production(run_started: datetime) -> tuple[int, int]:
    """Upsert staging rows into production and remove stale rows.

    Returns (upserted, stale_deleted) counts.
    """
    session = SessionLocal()
    try:
        # Read staging rows in batches and upsert into production
        staging_count = session.execute(select(func.count()).select_from(StagingPlace)).scalar()

        upserted = 0
        offset = 0
        while offset < (staging_count or 0):
            staging_rows = (
                session.execute(
                    select(StagingPlace).order_by(StagingPlace.id).offset(offset).limit(BATCH_SIZE)
                )
                .scalars()
                .all()
            )
            if not staging_rows:
                break

            values = [
                {
                    "source_id": r.source_id,
                    "name": r.name,
                    "category": r.category,
                    "alternate_categories": r.alternate_categories,
                    "confidence": r.confidence,
                    "operating_status": r.operating_status,
                    "address": r.address,
                    "city": r.city,
                    "state": r.state,
                    "postcode": r.postcode,
                    "country": r.country,
                    "brand_name": r.brand_name,
                    "brand_wikidata": r.brand_wikidata,
                    "website": r.website,
                    "phone": r.phone,
                    "email": r.email,
                    "social": r.social,
                    "source_dataset": r.source_dataset,
                    "source_record_id": r.source_record_id,
                    "geom": r.geom,
                    "loaded_at": run_started,
                }
                for r in staging_rows
            ]

            stmt = pg_insert(Place).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["source_id"],
                set_={col: stmt.excluded[col] for col in _UPDATABLE_COLUMNS}
                | {"loaded_at": stmt.excluded.loaded_at},
            )
            session.execute(stmt)
            session.commit()

            upserted += len(values)
            offset += BATCH_SIZE
            logger.info("Upserted %d places into production (total: %d)", len(values), upserted)

        # Remove stale rows not seen in this run
        stale_result = session.execute(delete(Place).where(Place.loaded_at < run_started))
        stale_deleted: int = stale_result.rowcount  # type: ignore[attr-defined]
        session.commit()

        logger.info(
            "Production promotion complete: %d upserted, %d stale deleted",
            upserted,
            stale_deleted,
        )
        return upserted, stale_deleted
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def fetch_places() -> None:
    """Fetch Overture Places from S3 GeoParquet and load into PostGIS.

    Uses a staging + upsert swap pattern:
    1. Stream S3 data into staging_places (safe to truncate, not serving queries)
    2. Validate staging row count
    3. Upsert from staging into production places (preserves PKs for FK safety)
    4. Delete stale production rows not seen in this run
    """
    settings = get_settings()
    s3_path = settings.overture_places_s3_path
    min_confidence = settings.overture_places_min_confidence
    country = settings.overture_places_country
    run_started = datetime.now(tz=UTC)

    logger.info(
        "Starting places load from %s (min_confidence=%.2f, country=%s)",
        s3_path,
        min_confidence,
        country,
    )

    con = duckdb.connect()
    try:
        con.execute("INSTALL spatial; LOAD spatial;")
        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute("SET s3_region='us-west-2';")

        query = _build_query(s3_path, min_confidence, country)

        # Step 1: Load into staging
        staging_count = _load_staging(con, query)

        # Step 2: Validate
        if not staging_count:
            raise RuntimeError("No records loaded into staging — aborting")

        logger.info("Staging validated: %d records, promoting to production", staging_count)

        # Step 3 & 4: Upsert into production + clean stale rows
        upserted, stale_deleted = _promote_to_production(run_started)

        logger.info(
            "Places load complete: %d staged, %d upserted, %d stale deleted",
            staging_count,
            upserted,
            stale_deleted,
        )
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

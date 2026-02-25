"""Collect airport data from OurAirports CSV.

Downloads the worldwide airports CSV, filters to US airports, and loads
them into PostGIS using direct upsert keyed on ``ident``.
"""

from __future__ import annotations

import contextlib
import csv
import io
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from pricepoint.config.settings import get_settings
from pricepoint.db import SessionLocal
from pricepoint.db.models import Airport

logger = logging.getLogger(__name__)

_UPDATABLE_COLUMNS = [
    "airport_type",
    "name",
    "elevation_ft",
    "iso_region",
    "municipality",
    "scheduled_service",
    "iata_code",
    "home_link",
    "wikipedia_link",
    "geom",
    "loaded_at",
]

_BATCH_SIZE = 500


def parse_airport_row(row: dict[str, str]) -> dict[str, Any] | None:
    """Parse a CSV row into a dict suitable for Airport upsert.

    Returns ``None`` if the row should be skipped (non-US or missing coords).
    """
    if row.get("iso_country") != "US":
        return None

    lat_str = row.get("latitude_deg", "").strip()
    lon_str = row.get("longitude_deg", "").strip()
    if not lat_str or not lon_str:
        return None

    try:
        lat = float(lat_str)
        lon = float(lon_str)
    except (ValueError, TypeError):
        return None

    elev_str = row.get("elevation_ft", "").strip()
    elevation: int | None = None
    if elev_str:
        with contextlib.suppress(ValueError, TypeError):
            elevation = int(float(elev_str))

    scheduled_raw = row.get("scheduled_service", "").strip().lower()
    scheduled = scheduled_raw == "yes"

    iata = row.get("iata_code", "").strip() or None
    home = row.get("home_link", "").strip() or None
    wiki = row.get("wikipedia_link", "").strip() or None

    return {
        "ident": row.get("ident", "").strip(),
        "airport_type": row.get("type", "").strip() or None,
        "name": row.get("name", "").strip() or None,
        "elevation_ft": elevation,
        "iso_region": row.get("iso_region", "").strip() or None,
        "municipality": row.get("municipality", "").strip() or None,
        "scheduled_service": scheduled,
        "iata_code": iata,
        "home_link": home,
        "wikipedia_link": wiki,
        "lat": lat,
        "lon": lon,
    }


def fetch_airports() -> int:
    """Download OurAirports CSV and upsert US airports into PostGIS.

    Returns the total number of records upserted.
    """
    settings = get_settings()
    url = settings.ourairports_csv_url

    logger.info("Downloading airports CSV from %s", url)
    resp = httpx.get(url, timeout=120, follow_redirects=True)
    resp.raise_for_status()

    reader = csv.DictReader(io.StringIO(resp.text))
    run_started = datetime.now(UTC)

    session = SessionLocal()
    try:
        total = 0
        batch: list[dict[str, Any]] = []

        for row in reader:
            parsed = parse_airport_row(row)
            if parsed is None:
                continue
            if not parsed["ident"]:
                continue

            geom = from_shape(Point(parsed["lon"], parsed["lat"]), srid=4326)

            batch.append(
                {
                    "ident": parsed["ident"],
                    "airport_type": parsed["airport_type"],
                    "name": parsed["name"],
                    "elevation_ft": parsed["elevation_ft"],
                    "iso_region": parsed["iso_region"],
                    "municipality": parsed["municipality"],
                    "scheduled_service": parsed["scheduled_service"],
                    "iata_code": parsed["iata_code"],
                    "home_link": parsed["home_link"],
                    "wikipedia_link": parsed["wikipedia_link"],
                    "geom": geom,
                    "loaded_at": run_started,
                }
            )

            if len(batch) >= _BATCH_SIZE:
                _upsert_batch(session, batch)
                total += len(batch)
                batch = []

        if batch:
            _upsert_batch(session, batch)
            total += len(batch)

        # Remove stale rows not seen in this run
        if total > 0:
            stale_count = session.execute(
                delete(Airport).where(Airport.loaded_at < run_started)
            ).rowcount  # type: ignore[union-attr, attr-defined]
            session.commit()
            if stale_count:
                logger.info("Removed %d stale airport records", stale_count)

        logger.info("Airports total loaded: %d records", total)
        return total

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _upsert_batch(session: Any, batch: list[dict[str, Any]]) -> None:
    """Execute a PostgreSQL upsert for a batch of airport records."""
    stmt = pg_insert(Airport).values(batch)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_airports_ident",
        set_={col: stmt.excluded[col] for col in _UPDATABLE_COLUMNS},
    )
    session.execute(stmt)
    session.commit()


def verify_airports() -> int:
    """Verify that records were loaded into the airports table.

    Returns the record count. Raises RuntimeError if the table is empty.
    """
    session = SessionLocal()
    try:
        count = session.execute(select(func.count()).select_from(Airport)).scalar() or 0
        if not count:
            raise RuntimeError("No records found in airports after load")
        logger.info("Verified %d airport records", count)
        return count
    finally:
        session.close()

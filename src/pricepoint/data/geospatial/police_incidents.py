"""Collect police incident data with geographic coordinates.

Sources: municipal open-data portals (e.g., Opendatasoft).
"""

import csv
import io
import logging

from geoalchemy2.shape import from_shape
from odsclient import get_whole_dataset
from shapely.geometry import Point
from sqlalchemy import delete

from pricepoint.config.settings import get_settings
from pricepoint.db import SessionLocal
from pricepoint.db.models import StagingCaryPoliceIncident

logger = logging.getLogger(__name__)


def fetch_police_incidents(*, city: str, start_date: str, end_date: str) -> None:
    """Download police incident records for the given city and date range.

    Stores results in the PostGIS ``police_incidents`` table.
    """
    raise NotImplementedError


def _csv_val(value: str) -> str | None:
    """Return None for empty CSV strings, otherwise the value as-is."""
    return value if value else None


def _csv_float(value: str) -> float | None:
    """Parse a CSV string as float, returning None for empty or invalid values."""
    if not value:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_geometry(lon: object, lat: object) -> object | None:
    """Create a WKB geometry from lon/lat values, returning None on failure."""
    if lon is None or lat is None:
        return None
    try:
        return from_shape(Point(float(lon), float(lat)), srid=4326)
    except (TypeError, ValueError):
        logger.warning("Invalid coordinates: lon=%s, lat=%s", lon, lat)
        return None


def _map_record(record: dict) -> StagingCaryPoliceIncident:
    """Map a single CSV row dict to a staging model instance."""
    lon = _csv_float(record.get("lon", ""))
    lat = _csv_float(record.get("lat", ""))

    return StagingCaryPoliceIncident(
        api_id=_csv_val(record.get("id", "")),
        incident_number=_csv_val(record.get("incident_number", "")),
        crime_category=_csv_val(record.get("crime_category", "")),
        crime_type=_csv_val(record.get("crime_type", "")),
        ucr=_csv_val(record.get("ucr", "")),
        map_reference=_csv_val(record.get("map_reference", "")),
        date_from=_csv_val(record.get("date_from", "")),
        from_time=_csv_val(record.get("from_time", "")),
        date_to=_csv_val(record.get("date_to", "")),
        to_time=_csv_val(record.get("to_time", "")),
        crimeday=_csv_val(record.get("crimeday", "")),
        geocode=_csv_val(record.get("geocode", "")),
        location_category=_csv_val(record.get("location_category", "")),
        district=_csv_val(record.get("district", "")),
        beat_number=_csv_val(record.get("beat_number", "")),
        neighborhd_id=_csv_val(record.get("neighborhd_id", "")),
        apartment_complex=_csv_val(record.get("apartment_complex", "")),
        residential_subdivision=_csv_val(record.get("residential_subdivision", "")),
        subdivisn_id=_csv_val(record.get("subdivisn_id", "")),
        activity_date=_csv_val(record.get("activity_date", "")),
        phxrecordstatus=_csv_val(record.get("phxrecordstatus", "")),
        phxcommunity=_csv_val(record.get("phxcommunity", "")),
        phxstatus=_csv_val(record.get("phxstatus", "")),
        record=_csv_val(record.get("record", "")),
        offensecategory=_csv_val(record.get("offensecategory", "")),
        violentproperty=_csv_val(record.get("violentproperty", "")),
        timeframe=_csv_val(record.get("timeframe", "")),
        domestic=_csv_val(record.get("domestic", "")),
        total_incidents=_csv_val(record.get("total_incidents", "")),
        year=_csv_val(record.get("year", "")),
        older_than_five_years_from_now=_csv_val(record.get("older_than_five_years_from_now", "")),
        chrgcnt=_csv_val(record.get("chrgcnt", "")),
        lon=lon,
        lat=lat,
        location=_build_geometry(lon, lat),
    )


def fetch_cary_police_incidents(*, full_refresh: bool = True) -> None:
    """Fetch all police incident records from the Town of Cary Open Data Portal.

    Downloads the full ``cpd-incidents`` dataset via ``odsclient`` and loads
    records into the ``staging_cary_police_incidents`` table.

    Args:
        full_refresh: If True (default), truncate the staging table before loading.
    """
    settings = get_settings()

    session = SessionLocal()
    try:
        if full_refresh:
            session.execute(delete(StagingCaryPoliceIncident))
            session.commit()

        csv_text = get_whole_dataset(
            "cpd-incidents",
            platform_id=settings.cary_opendata_platform_id,
        )

        reader = csv.DictReader(io.StringIO(csv_text), delimiter=";")
        records = [_map_record(row) for row in reader]

        if records:
            session.add_all(records)
            session.commit()

        logger.info("Cary police incidents load complete: %d records", len(records))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

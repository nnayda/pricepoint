"""Collect police incident data with geographic coordinates.

Sources: municipal open-data portals (e.g., Socrata SODA API).
"""

import logging

import httpx
from geoalchemy2.shape import from_shape
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
    """Map a single API result dict to a staging model instance."""
    return StagingCaryPoliceIncident(
        api_id=record.get("id"),
        incident_number=record.get("incident_number"),
        crime_category=record.get("crime_category"),
        crime_type=record.get("crime_type"),
        ucr=record.get("ucr"),
        map_reference=record.get("map_reference"),
        date_from=record.get("date_from"),
        from_time=record.get("from_time"),
        date_to=record.get("date_to"),
        to_time=record.get("to_time"),
        crimeday=record.get("crimeday"),
        geocode=record.get("geocode"),
        location_category=record.get("location_category"),
        district=record.get("district"),
        beat_number=str(record["beat_number"]) if record.get("beat_number") is not None else None,
        neighborhd_id=record.get("neighborhd_id"),
        apartment_complex=record.get("apartment_complex"),
        residential_subdivision=record.get("residential_subdivision"),
        subdivisn_id=record.get("subdivisn_id"),
        activity_date=record.get("activity_date"),
        phxrecordstatus=record.get("phxrecordstatus"),
        phxcommunity=record.get("phxcommunity"),
        phxstatus=record.get("phxstatus"),
        record=str(record["record"]) if record.get("record") is not None else None,
        offensecategory=record.get("offensecategory"),
        violentproperty=record.get("violentproperty"),
        timeframe=record.get("timeframe"),
        domestic=record.get("domestic"),
        total_incidents=(
            str(record["total_incidents"]) if record.get("total_incidents") is not None else None
        ),
        year=record.get("year"),
        older_than_five_years_from_now=record.get("older_than_five_years_from_now"),
        chrgcnt=str(record["chrgcnt"]) if record.get("chrgcnt") is not None else None,
        lon=float(record["lon"]) if record.get("lon") is not None else None,
        lat=float(record["lat"]) if record.get("lat") is not None else None,
        location=_build_geometry(record.get("lon"), record.get("lat")),
    )


def fetch_cary_police_incidents(*, full_refresh: bool = True) -> None:
    """Fetch all police incident records from the Town of Cary Open Data Portal.

    Downloads records from the Opendatasoft API v2.1 and loads them into the
    ``staging_cary_police_incidents`` table. Uses offset-based pagination.

    Args:
        full_refresh: If True (default), truncate the staging table before loading.
    """
    settings = get_settings()
    url = f"{settings.cary_opendata_base_url}/catalog/datasets/cpd-incidents/records"
    page_size = settings.cary_police_page_size

    session = SessionLocal()
    try:
        if full_refresh:
            session.execute(delete(StagingCaryPoliceIncident))
            session.commit()

        offset = 0
        total_count: int | None = None

        with httpx.Client(timeout=30.0) as client:
            while True:
                response = client.get(url, params={"limit": page_size, "offset": offset})
                response.raise_for_status()
                data = response.json()

                if total_count is None:
                    total_count = data["total_count"]
                    logger.info("Total records to fetch: %d", total_count)

                results = data.get("results", [])
                if not results:
                    break

                records = [_map_record(r) for r in results]
                session.add_all(records)
                session.commit()

                offset += len(results)
                logger.info("Fetched %d / %d records", offset, total_count)

                if offset >= total_count:
                    break

        logger.info("Cary police incidents load complete: %d records", offset)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

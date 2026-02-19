"""Collect police incident data with geographic coordinates.

Sources: municipal open-data portals (Opendatasoft, ArcGIS Feature Services).
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime

import httpx
from geoalchemy2.shape import from_shape
from odsclient import ODSClient
from shapely.geometry import Point
from sqlalchemy import delete, select

from pricepoint.config.settings import get_settings
from pricepoint.db import SessionLocal
from pricepoint.db.models import (
    StagingCaryPoliceIncident,
    StagingMorrisvillePoliceIncident,
    StagingRaleighPoliceIncident,
)

logger = logging.getLogger(__name__)


def fetch_police_incidents(*, full_refresh: bool = True) -> dict[str, str]:
    """Orchestrate police incident collection from all supported cities.

    Calls the city-specific collectors for Cary, Raleigh, and Morrisville,
    collecting results and returning summary status for each city.

    Args:
        full_refresh: If True (default), each collector truncates its staging
            table before loading.

    Returns:
        A dict mapping city name to status string ("ok" or an error message).
    """
    collectors: dict[str, Callable[..., None]] = {
        "cary": fetch_cary_police_incidents,
        "raleigh": fetch_raleigh_police_incidents,
        "morrisville": fetch_morrisville_police_incidents,
    }

    results: dict[str, str] = {}
    for city, collector_fn in collectors.items():
        try:
            collector_fn(full_refresh=full_refresh)
            results[city] = "ok"
            logger.info("Police incidents collection succeeded for %s", city)
        except Exception:
            logger.exception("Police incidents collection failed for %s", city)
            results[city] = "error"

    return results


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


def _build_geometry(lon: float | None, lat: float | None) -> object | None:
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
    CARY_BASE_URL = "https://data.townofcary.org/"
    CARY_DATASET_ID = "cpd-incidents"

    session = SessionLocal()
    try:
        if full_refresh:
            session.execute(delete(StagingCaryPoliceIncident))
            session.commit()

        # Use ODSClient with base URL instead of platform_id
        client = ODSClient(base_url=CARY_BASE_URL)
        df = client.get_whole_dataframe(dataset_id=CARY_DATASET_ID)

        if df.empty:
            logger.warning("Cary police incidents: downloaded dataset is empty")
            return

        # Normalize column names: lowercase and replace spaces with underscores
        df.columns = df.columns.str.lower().str.replace(" ", "_")

        # Rename columns to match the expected format
        column_mapping = {
            "id": "id",
            "incident_number": "incident_number",
            "crime_category": "crime_category",
            "crime_type": "crime_type",
            "ucr": "ucr",
            "map_reference": "map_reference",
            "begin_date_of_occurrence": "date_from",
            "begin_time_of_occurrence": "from_time",
            "end_date_of_occurrence": "date_to",
            "end_time_of_occurrence": "to_time",
            "crime_day": "crimeday",
            "geo_code": "geocode",
            "location_category": "location_category",
            "district": "district",
            "beat_number": "beat_number",
            "neighborhood_id": "neighborhd_id",
            "apartment_complex": "apartment_complex",
            "residential_subdivision": "residential_subdivision",
            "subdivision_id": "subdivisn_id",
            "phx_activity_date": "activity_date",
            "phx_record_status": "phxrecordstatus",
            "phx_community": "phxcommunity",
            "phx_status": "phxstatus",
            "record": "record",
            "offense_category": "offensecategory",
            "violent_property": "violentproperty",
            "timeframe": "timeframe",
            "domestic": "domestic",
            "total_incidents": "total_incidents",
            "year": "year",
            "older_than_five_years_from_now": "older_than_five_years_from_now",
            "charge_count": "chrgcnt",
            "longitude": "lon",
            "latitude": "lat",
        }
        df = df.rename(columns=column_mapping)

        # Convert dataframe to records - iterate through rows
        records = []
        for _, row in df.iterrows():
            # Convert row to dict and map to model
            row_dict = row.to_dict()
            # Convert NaN to empty string for CSV compatibility
            row_dict = {
                k: (v if not (isinstance(v, float) and str(v) == "nan") else "")
                for k, v in row_dict.items()
            }
            records.append(_map_record(row_dict))

        if records:
            session.add_all(records)
            session.commit()

        logger.info("Cary police incidents load complete: %d records", len(records))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# -- Raleigh ArcGIS helpers ----------------------------------------------------

_ARCGIS_PAGE_SIZE = 5000


def _parse_arcgis_timestamp(value: int | str | None) -> datetime | None:
    """Convert an ArcGIS epoch-millisecond timestamp to a Python datetime."""
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


def _query_arcgis_features(
    base_url: str,
    service_name: str,
    *,
    where: str = "1=1",
    offset: int = 0,
    count: int = _ARCGIS_PAGE_SIZE,
) -> list[dict]:
    """Send a paginated query to an ArcGIS REST Feature Service.

    Returns the ``features`` list from the JSON response.
    """
    url = f"{base_url}/{service_name}/FeatureServer/0/query"
    params: dict[str, str | int] = {
        "where": where,
        "outFields": "*",
        "returnGeometry": "false",
        "resultOffset": offset,
        "resultRecordCount": count,
        "f": "json",
    }
    response = httpx.get(url, params=params, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data.get("features", [])


def _map_raleigh_record(feature: dict) -> StagingRaleighPoliceIncident:
    """Map an ArcGIS JSON feature to a staging model instance."""
    attrs = feature.get("attributes", {})
    lat = attrs.get("latitude")
    lon = attrs.get("longitude")

    return StagingRaleighPoliceIncident(
        objectid=str(attrs["OBJECTID"]) if attrs.get("OBJECTID") is not None else None,
        global_id=attrs.get("GlobalID"),
        case_number=attrs.get("case_number"),
        crime_category=attrs.get("crime_category"),
        crime_code=attrs.get("crime_code"),
        crime_description=attrs.get("crime_description"),
        crime_type=attrs.get("crime_type"),
        reported_block_address=attrs.get("reported_block_address"),
        city_of_incident=attrs.get("city_of_incident"),
        city=attrs.get("city"),
        district=attrs.get("district"),
        reported_date=_parse_arcgis_timestamp(attrs.get("reported_date")),
        reported_year=attrs.get("reported_year"),
        reported_month=attrs.get("reported_month"),
        reported_day=attrs.get("reported_day"),
        reported_hour=attrs.get("reported_hour"),
        reported_dayofwk=attrs.get("reported_dayofwk"),
        latitude=lat,
        longitude=lon,
        agency=attrs.get("agency"),
        updated_date=_parse_arcgis_timestamp(attrs.get("updated_date")),
        location=_build_geometry(lon, lat),
    )


def fetch_raleigh_police_incidents(*, full_refresh: bool = True) -> None:
    """Fetch police incident records from the Raleigh NIBRS historical endpoint.

    Paginates through the full ``Police_Incidents`` Feature Service and loads
    records into the ``staging_raleigh_police_incidents`` table.

    Args:
        full_refresh: If True (default), truncate the staging table before loading.
    """
    settings = get_settings()

    session = SessionLocal()
    try:
        if full_refresh:
            session.execute(delete(StagingRaleighPoliceIncident))
            session.commit()

        offset = 0
        total = 0
        while True:
            features = _query_arcgis_features(
                settings.raleigh_arcgis_base_url,
                "Police_Incidents",
                offset=offset,
                count=_ARCGIS_PAGE_SIZE,
            )
            if not features:
                break

            records = [_map_raleigh_record(f) for f in features]
            session.add_all(records)
            session.commit()

            total += len(records)
            offset += len(features)

            if len(features) < _ARCGIS_PAGE_SIZE:
                break

        logger.info("Raleigh police incidents load complete: %d records", total)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def fetch_daily_raleigh_police_incidents() -> None:
    """Fetch yesterday's incidents from the Raleigh Daily_Police_Incidents endpoint.

    Deduplicates against existing ``case_number`` values in the staging table
    and inserts only new records.
    """
    settings = get_settings()

    session = SessionLocal()
    try:
        features = _query_arcgis_features(
            settings.raleigh_arcgis_base_url,
            "Daily_Police_Incidents",
        )

        if not features:
            logger.info("Raleigh daily police incidents: no new records")
            return

        existing = set(
            session.execute(select(StagingRaleighPoliceIncident.case_number)).scalars().all()
        )

        new_records = [
            _map_raleigh_record(f)
            for f in features
            if f.get("attributes", {}).get("case_number") not in existing
        ]

        if new_records:
            session.add_all(new_records)
            session.commit()

        logger.info(
            "Raleigh daily police incidents: %d new of %d total",
            len(new_records),
            len(features),
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# -- Morrisville Opendatasoft helpers ------------------------------------------


def _parse_area_coords(area: str) -> tuple[float | None, float | None]:
    """Parse an Opendatasoft ``area`` value ("lat, lon") into (lat, lon).

    Returns ``(None, None)`` on any failure.
    """
    if not area:
        return None, None
    try:
        parts = area.split(",")
        return float(parts[0].strip()), float(parts[1].strip())
    except (IndexError, ValueError):
        return None, None


def _map_morrisville_record(record: dict) -> StagingMorrisvillePoliceIncident:
    """Map a single CSV row dict to a Morrisville staging model instance."""
    lat, lon = _parse_area_coords(record.get("area", ""))

    return StagingMorrisvillePoliceIncident(
        inci_id=_csv_val(record.get("inci_id", "")),
        offense=_csv_val(record.get("offense", "")),
        date_rept=_csv_val(record.get("date_rept", "")),
        date_occu=_csv_val(record.get("date_occu", "")),
        dow1=_csv_val(record.get("dow1", "")),
        monthstamp=_csv_val(record.get("monthstamp", "")),
        yearstamp=_csv_val(record.get("yearstamp", "")),
        street=_csv_val(record.get("street", "")),
        city=_csv_val(record.get("city", "")),
        state=_csv_val(record.get("state", "")),
        zip=_csv_val(record.get("zip", "")),
        neighborhd=_csv_val(record.get("neighborhd", "")),
        subdivisn=_csv_val(record.get("subdivisn", "")),
        tract=_csv_val(record.get("tract", "")),
        zone=_csv_val(record.get("zone", "")),
        district=_csv_val(record.get("district", "")),
        asst_offcr=_csv_val(record.get("asst_offcr", "")),
        lat=lat,
        lon=lon,
        location=_build_geometry(lon, lat),
    )


def fetch_morrisville_police_incidents(*, full_refresh: bool = True) -> None:
    """Fetch all police incident records from the Town of Morrisville Open Data Portal.

    Downloads the full ``pd_incident_report`` dataset via ``odsclient`` and loads
    records into the ``staging_morrisville_police_incidents`` table.

    Args:
        full_refresh: If True (default), truncate the staging table before loading.
    """
    MORRISVILLE_BASE_URL = "https://opendata.townofmorrisville.org/"
    MORRISVILLE_DATASET_ID = "pd_incident_report"

    session = SessionLocal()
    try:
        if full_refresh:
            session.execute(delete(StagingMorrisvillePoliceIncident))
            session.commit()

        # Use ODSClient with base URL instead of platform_id
        client = ODSClient(base_url=MORRISVILLE_BASE_URL)
        df = client.get_whole_dataframe(dataset_id=MORRISVILLE_DATASET_ID)

        if df.empty:
            logger.warning("Morrisville police incidents: downloaded dataset is empty")
            return

        # Normalize column names: lowercase and replace spaces with underscores
        df.columns = df.columns.str.lower().str.replace(" ", "_")

        # Rename columns to match expected format
        column_mapping = {
            "inci_id": "inci_id",
            "offense": "offense",
            "date_rept": "date_rept",
            "date_occu": "date_occu",
            "dow1": "dow1",
            "monthstamp": "monthstamp",
            "yearstamp": "yearstamp",
            "street": "street",
            "city": "city",
            "state": "state",
            "zip": "zip",
            "neighborhd": "neighborhd",
            "subdivisn": "subdivisn",
            "tract": "tract",
            "zone": "zone",
            "district": "district",
            "asst_offcr": "asst_offcr",
            "geo_point_2d": "area",  # This contains "lat, lon" format
        }

        # Only rename columns that exist
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        # Convert dataframe to records - iterate through rows
        records = []
        for _, row in df.iterrows():
            # Convert row to dict and map to model
            row_dict = row.to_dict()
            # Convert NaN to empty string
            row_dict = {
                k: (v if not (isinstance(v, float) and str(v) == "nan") else "")
                for k, v in row_dict.items()
            }
            records.append(_map_morrisville_record(row_dict))

        if records:
            session.add_all(records)
            session.commit()

        logger.info(
            "Morrisville police incidents load complete: %d records",
            len(records),
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

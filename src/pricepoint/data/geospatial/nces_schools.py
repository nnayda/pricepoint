"""Collect NCES school directory data from the EDGE ArcGIS REST API.

Downloads public school data for a configured state and loads it into the
nces_schools table. Uses pagination to handle large result sets.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import delete

from pricepoint.config.settings import get_settings
from pricepoint.db import SessionLocal
from pricepoint.db.models import NcesSchool

logger = logging.getLogger(__name__)

# Fields to request from the NCES EDGE API
_CORE_FIELDS = [
    "NCESSCH",
    "SCH_NAME",
    "LSTREET1",
    "LCITY",
    "LSTATE",
    "LZIP",
    "LATCOD",
    "LONCOD",
    "SCHOOL_TYPE_TEXT",
    "SCHOOL_LEVEL",
    "GSLO",
    "GSHI",
    "STATUS",
]

_EXTRA_FIELDS = [
    "PHONE",
    "TOTAL",
    "MEMBER",
    "CHARTER_TEXT",
    "VIRTUAL",
    "FTE",
    "STUTERATIO",
    "FRELCH",
    "REDLCH",
    "TOTFRL",
    "LEA_NAME",
    "LEAID",
    "ULOCALE",
]

_ALL_FIELDS = _CORE_FIELDS + _EXTRA_FIELDS
_PAGE_SIZE = 1000


def _fetch_nces_page(base_url: str, state_fips: str, offset: int) -> list[dict[str, Any]]:
    """Query NCES EDGE ArcGIS REST API with pagination.

    Returns a list of feature attribute dicts for one page.
    """
    params = {
        "where": f"OPSTFIPS='{state_fips}' AND STATUS='1'",
        "outFields": ",".join(_ALL_FIELDS),
        "resultOffset": str(offset),
        "resultRecordCount": str(_PAGE_SIZE),
        "f": "json",
    }
    resp = httpx.get(
        f"{base_url}/query",
        params=params,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("features", [])


def _parse_nces_record(feature: dict[str, Any]) -> dict[str, Any]:
    """Extract core fields and pack extras from an ArcGIS feature."""
    attrs = feature.get("attributes", {})

    # Core fields
    lat = attrs.get("LATCOD")
    lon = attrs.get("LONCOD")

    extras: dict[str, Any] = {}
    for field in _EXTRA_FIELDS:
        val = attrs.get(field)
        if val is not None:
            extras[field] = val

    nces_id_raw = attrs.get("NCESSCH")
    nces_id = str(nces_id_raw) if nces_id_raw is not None else ""

    return {
        "nces_id": nces_id,
        "name": attrs.get("SCH_NAME", ""),
        "street": attrs.get("LSTREET1"),
        "city": attrs.get("LCITY"),
        "state": attrs.get("LSTATE"),
        "zip_code": attrs.get("LZIP"),
        "school_type": attrs.get("SCHOOL_TYPE_TEXT"),
        "school_level": attrs.get("SCHOOL_LEVEL"),
        "grades_low": attrs.get("GSLO"),
        "grades_high": attrs.get("GSHI"),
        "lat": float(lat) if lat is not None else None,
        "lon": float(lon) if lon is not None else None,
        "extras": extras if extras else None,
    }


def fetch_nces_schools() -> int:
    """Download all NCES schools for the configured state and upsert into DB.

    Deletes existing records first, then bulk inserts.
    Returns the total record count.
    """
    settings = get_settings()
    base_url = settings.nces_edge_base_url
    state_fips = settings.tiger_state_fips

    session = SessionLocal()
    try:
        session.execute(delete(NcesSchool))
        session.commit()

        offset = 0
        total = 0

        while True:
            features = _fetch_nces_page(base_url, state_fips, offset)
            if not features:
                break

            records = []
            for feature in features:
                parsed = _parse_nces_record(feature)
                if not parsed["nces_id"]:
                    continue

                location = None
                if parsed["lat"] is not None and parsed["lon"] is not None:
                    location = from_shape(Point(parsed["lon"], parsed["lat"]), srid=4326)

                records.append(
                    NcesSchool(
                        nces_id=parsed["nces_id"],
                        name=parsed["name"],
                        street=parsed["street"],
                        city=parsed["city"],
                        state=parsed["state"],
                        zip_code=parsed["zip_code"],
                        school_type=parsed["school_type"],
                        school_level=parsed["school_level"],
                        grades_low=parsed["grades_low"],
                        grades_high=parsed["grades_high"],
                        location=location,
                        extras=parsed["extras"],
                    )
                )

            if records:
                session.add_all(records)
                session.commit()

            total += len(records)
            logger.info("NCES schools page at offset %d: %d records", offset, len(records))

            if len(features) < _PAGE_SIZE:
                break
            offset += _PAGE_SIZE

        logger.info("NCES schools total loaded: %d records", total)
        return total

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

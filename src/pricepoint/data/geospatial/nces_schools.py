"""Collect NCES school directory data from the EDGE ArcGIS REST API.

Downloads public school data for the entire US (all states and territories)
and loads it into the nces_schools table. Uses pagination to handle large
result sets.

Uses direct upsert (pg_insert ... ON CONFLICT DO UPDATE) keyed on nces_id
to avoid any window where the table is empty.
"""

from __future__ import annotations

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

# Columns to update on conflict (everything except nces_id and id)
_UPDATABLE_COLUMNS = [
    "name",
    "street",
    "city",
    "state",
    "zip_code",
    "school_type",
    "school_level",
    "grades_low",
    "grades_high",
    "location",
    "extras",
    "loaded_at",
]

# FIPS state code -> USPS abbreviation (used by NCES STABR field)
_FIPS_TO_ABBR: dict[str, str] = {
    "01": "AL",
    "02": "AK",
    "04": "AZ",
    "05": "AR",
    "06": "CA",
    "08": "CO",
    "09": "CT",
    "10": "DE",
    "11": "DC",
    "12": "FL",
    "13": "GA",
    "15": "HI",
    "16": "ID",
    "17": "IL",
    "18": "IN",
    "19": "IA",
    "20": "KS",
    "21": "KY",
    "22": "LA",
    "23": "ME",
    "24": "MD",
    "25": "MA",
    "26": "MI",
    "27": "MN",
    "28": "MS",
    "29": "MO",
    "30": "MT",
    "31": "NE",
    "32": "NV",
    "33": "NH",
    "34": "NJ",
    "35": "NM",
    "36": "NY",
    "37": "NC",
    "38": "ND",
    "39": "OH",
    "40": "OK",
    "41": "OR",
    "42": "PA",
    "44": "RI",
    "45": "SC",
    "46": "SD",
    "47": "TN",
    "48": "TX",
    "49": "UT",
    "50": "VT",
    "51": "VA",
    "53": "WA",
    "54": "WV",
    "55": "WI",
    "56": "WY",
    "60": "AS",
    "66": "GU",
    "69": "MP",
    "72": "PR",
    "78": "VI",
}


def _fips_to_state_abbr(fips: str) -> str:
    """Convert a FIPS state code to a USPS state abbreviation."""
    abbr = _FIPS_TO_ABBR.get(fips)
    if abbr is None:
        raise ValueError(f"Unknown state FIPS code: {fips!r}")
    return abbr


def _fetch_nces_page(
    base_url: str, offset: int, *, state_abbr: str | None = None
) -> list[dict[str, Any]]:
    """Query NCES EDGE ArcGIS REST API with pagination.

    If *state_abbr* is provided, only schools in that state are returned.
    Otherwise all active US schools are fetched.

    Returns a list of feature attribute dicts for one page.
    """
    where = f"STABR='{state_abbr}' AND STATUS='1'" if state_abbr else "STATUS='1'"
    params = {
        "where": where,
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
    """Download all NCES schools for the entire US and upsert into DB.

    Uses pg_insert ... ON CONFLICT DO UPDATE keyed on nces_id so that the
    table is never emptied.  After all pages are upserted, stale rows
    (loaded_at < run start) are cleaned up.

    Returns the total record count.
    """
    settings = get_settings()
    base_url = settings.nces_edge_base_url

    run_started = datetime.now(UTC)

    session = SessionLocal()
    try:
        offset = 0
        total = 0

        while True:
            features = _fetch_nces_page(base_url, offset)
            if not features:
                break

            values: list[dict[str, Any]] = []
            for feature in features:
                parsed = _parse_nces_record(feature)
                if not parsed["nces_id"]:
                    continue

                location = None
                if parsed["lat"] is not None and parsed["lon"] is not None:
                    location = from_shape(Point(parsed["lon"], parsed["lat"]), srid=4326)

                values.append(
                    {
                        "nces_id": parsed["nces_id"],
                        "name": parsed["name"],
                        "street": parsed["street"],
                        "city": parsed["city"],
                        "state": parsed["state"],
                        "zip_code": parsed["zip_code"],
                        "school_type": parsed["school_type"],
                        "school_level": parsed["school_level"],
                        "grades_low": parsed["grades_low"],
                        "grades_high": parsed["grades_high"],
                        "location": location,
                        "extras": parsed["extras"],
                        "loaded_at": run_started,
                    }
                )

            if values:
                stmt = pg_insert(NcesSchool).values(values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["nces_id"],
                    set_={col: stmt.excluded[col] for col in _UPDATABLE_COLUMNS},
                )
                session.execute(stmt)
                session.commit()

            total += len(values)
            logger.info("NCES schools page at offset %d: %d records", offset, len(values))

            if len(features) < _PAGE_SIZE:
                break
            offset += _PAGE_SIZE

        # Remove stale rows not seen in this run
        if total > 0:
            stale_count = session.execute(
                delete(NcesSchool).where(NcesSchool.loaded_at < run_started)
            ).rowcount  # type: ignore[attr-defined]
            session.commit()
            if stale_count:
                logger.info("Removed %d stale NCES school records", stale_count)

        logger.info("NCES schools total loaded: %d records", total)
        return total

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def verify_nces_schools() -> int:
    """Verify that records were loaded into the nces_schools table.

    Returns the record count. Raises RuntimeError if the table is empty.
    """
    session = SessionLocal()
    try:
        count = session.execute(select(func.count()).select_from(NcesSchool)).scalar() or 0
        if not count:
            raise RuntimeError("No records found in nces_schools after load")
        logger.info("Verified %d NCES school records", count)
        return count
    finally:
        session.close()

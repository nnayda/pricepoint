"""Collect HIFLD North American Rail Network lines from ArcGIS FeatureServer.

Downloads railroad line geometries for the configured state and loads them
into the railroads table. Uses pagination and upsert on fraarcid.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from geoalchemy2.shape import from_shape
from shapely.geometry import MultiLineString, shape
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from pricepoint.config.settings import get_settings
from pricepoint.db import SessionLocal
from pricepoint.db.models import Railroad

logger = logging.getLogger(__name__)

_PAGE_SIZE = 1000

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
}

_UPDATABLE_COLUMNS = [
    "rrowner1",
    "rrowner2",
    "rrowner3",
    "stateab",
    "cntyfips",
    "subdivision",
    "branch",
    "passngr",
    "tracks",
    "miles",
    "net",
    "geom",
    "loaded_at",
]


def _fips_to_state_abbr(fips: str) -> str:
    """Convert a FIPS state code to a USPS state abbreviation."""
    abbr = _FIPS_TO_ABBR.get(fips)
    if abbr is None:
        raise ValueError(f"Unknown state FIPS code: {fips!r}")
    return abbr


def _fetch_page(base_url: str, state_abbr: str, offset: int) -> list[dict[str, Any]]:
    """Query HIFLD ArcGIS FeatureServer with pagination, returning GeoJSON features."""
    params = {
        "where": f"STATEAB='{state_abbr}'",
        "outFields": "*",
        "resultOffset": str(offset),
        "resultRecordCount": str(_PAGE_SIZE),
        "f": "geojson",
    }
    resp = httpx.get(f"{base_url}/query", params=params, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data.get("features", [])


def _parse_feature(feature: dict[str, Any]) -> dict[str, Any] | None:
    """Parse a GeoJSON feature into a dict suitable for Railroad insert."""
    props = feature.get("properties", {})
    geom_json = feature.get("geometry")

    fraarcid = props.get("FRAARCID")
    if fraarcid is None:
        return None

    geom = None
    if geom_json:
        geom_shape = shape(geom_json)
        if geom_shape.geom_type == "LineString":
            geom_shape = MultiLineString([geom_shape])
        if geom_shape.geom_type == "MultiLineString":
            geom = from_shape(geom_shape, srid=4326)

    tracks_raw = props.get("TRACKS")
    tracks = int(tracks_raw) if tracks_raw is not None else None

    miles_raw = props.get("MILES")
    miles = float(miles_raw) if miles_raw is not None else None

    return {
        "fraarcid": int(fraarcid),
        "rrowner1": props.get("RROWNER1"),
        "rrowner2": props.get("RROWNER2"),
        "rrowner3": props.get("RROWNER3"),
        "stateab": props.get("STATEAB"),
        "cntyfips": props.get("CNTYFIPS"),
        "subdivision": props.get("SUBDIVISIO") or props.get("SUBDIVISION"),
        "branch": props.get("BRANCH"),
        "passngr": props.get("PASSNGR"),
        "tracks": tracks,
        "miles": miles,
        "net": props.get("NET"),
        "geom": geom,
    }


def fetch_railroads() -> int:
    """Download railroad lines for the configured state and upsert into DB.

    Returns the total record count.
    """
    settings = get_settings()
    base_url = settings.hifld_railroads_base_url
    state_abbr = _fips_to_state_abbr(settings.tiger_state_fips)

    run_started = datetime.now(UTC)

    session = SessionLocal()
    try:
        offset = 0
        total = 0

        while True:
            features = _fetch_page(base_url, state_abbr, offset)
            if not features:
                break

            values: list[dict[str, Any]] = []
            for feature in features:
                parsed = _parse_feature(feature)
                if parsed is None:
                    continue
                parsed["loaded_at"] = run_started
                values.append(parsed)

            if values:
                stmt = pg_insert(Railroad).values(values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["fraarcid"],
                    set_={col: stmt.excluded[col] for col in _UPDATABLE_COLUMNS},
                )
                session.execute(stmt)
                session.commit()

            total += len(values)
            logger.info("Railroads page at offset %d: %d records", offset, len(values))

            if len(features) < _PAGE_SIZE:
                break
            offset += _PAGE_SIZE

        # Remove stale rows not seen in this run
        if total > 0:
            stale_count = session.execute(
                delete(Railroad).where(Railroad.loaded_at < run_started)
            ).rowcount
            session.commit()
            if stale_count:
                logger.info("Removed %d stale railroad records", stale_count)

        logger.info("Railroads total loaded: %d records", total)
        return total

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def verify_railroads() -> int:
    """Verify that records were loaded into the railroads table.

    Returns the record count. Raises RuntimeError if the table is empty.
    """
    session = SessionLocal()
    try:
        count = session.execute(select(func.count()).select_from(Railroad)).scalar() or 0
        if not count:
            raise RuntimeError("No records found in railroads after load")
        logger.info("Verified %d railroad records", count)
        return count
    finally:
        session.close()

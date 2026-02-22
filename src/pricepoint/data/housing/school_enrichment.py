"""Enrich schools with addresses and travel times.

Matches Redfin school names to NCES records via fuzzy matching,
falls back to Nominatim geocoding, and computes drive/walk times via OSRM.
"""

from __future__ import annotations

import logging
import time
from difflib import SequenceMatcher
from typing import Any

import httpx
from geoalchemy2.types import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from pricepoint.config.settings import get_settings
from pricepoint.db.models import NcesSchool

logger = logging.getLogger(__name__)

# Suffixes to strip when normalizing school names
_STRIP_SUFFIXES = [
    "elementary school",
    "middle school",
    "high school",
    "school",
    "elem",
    "elementary",
    "middle",
    "magnet",
    "academy",
    "preparatory",
    "prep",
]

# Meters per mile for ST_DWithin conversion
_METERS_PER_MILE = 1609.344


# ---------------------------------------------------------------------------
# Name normalization
# ---------------------------------------------------------------------------


def _normalize_school_name(name: str) -> str:
    """Lowercase and strip common school-type suffixes for comparison."""
    normalized = name.strip().lower()
    for suffix in _STRIP_SUFFIXES:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)].strip()
            break
    return normalized


# ---------------------------------------------------------------------------
# NCES fuzzy matching
# ---------------------------------------------------------------------------


def match_nces_school(
    session: Session,
    school_name: str,
    property_lat: float,
    property_lon: float,
    radius_miles: float = 10.0,
) -> NcesSchool | None:
    """Find best NCES match using name similarity + spatial proximity.

    Queries NcesSchool within radius_miles of the property, then picks the
    best match by SequenceMatcher ratio above a threshold of 0.4.
    """
    radius_m = radius_miles * _METERS_PER_MILE
    property_point = func.ST_SetSRID(func.ST_MakePoint(property_lon, property_lat), 4326)

    candidates = (
        session.execute(
            select(NcesSchool).where(
                NcesSchool.location.isnot(None),
                func.ST_DWithin(
                    cast(NcesSchool.location, Geography),
                    cast(property_point, Geography),
                    radius_m,
                ),
            )
        )
        .scalars()
        .all()
    )

    if not candidates:
        return None

    normalized_target = _normalize_school_name(school_name)
    best_match: NcesSchool | None = None
    best_score = 0.0

    for candidate in candidates:
        normalized_candidate = _normalize_school_name(candidate.name)
        score = SequenceMatcher(None, normalized_target, normalized_candidate).ratio()
        if score > best_score:
            best_score = score
            best_match = candidate

    if best_score >= 0.4:
        return best_match
    return None


# ---------------------------------------------------------------------------
# Nominatim fallback
# ---------------------------------------------------------------------------


def geocode_school_nominatim(
    school_name: str,
    near_lat: float,
    near_lon: float,
) -> dict[str, Any] | None:
    """Search Nominatim for a school near given coords.

    Returns {"address": str, "lat": float, "lon": float} or None.
    """
    time.sleep(1)  # Respect Nominatim rate limit
    try:
        # Bias results with a viewbox around the property (~10 mile box)
        delta = 0.15  # ~10 miles in degrees
        viewbox = f"{near_lon - delta},{near_lat + delta},{near_lon + delta},{near_lat - delta}"
        resp = httpx.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": school_name,
                "format": "json",
                "limit": 1,
                "viewbox": viewbox,
                "bounded": 0,
            },
            headers={"User-Agent": "PricePoint/1.0"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data:
            return {
                "address": data[0].get("display_name", ""),
                "lat": float(data[0]["lat"]),
                "lon": float(data[0]["lon"]),
            }
    except Exception:
        logger.warning("Nominatim geocoding failed for %s", school_name, exc_info=True)
    return None


# ---------------------------------------------------------------------------
# OSRM travel times
# ---------------------------------------------------------------------------


def get_osrm_route(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    profile: str = "car",
) -> dict[str, Any] | None:
    """Call OSRM route API for a single origin-destination pair.

    Returns {"duration_minutes": float, "distance_miles": float} or None.
    """
    settings = get_settings()
    if settings.osrm_rate_limit_seconds > 0:
        time.sleep(settings.osrm_rate_limit_seconds)

    try:
        url = (
            f"{settings.osrm_base_url}/route/v1/{profile}/"
            f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
        )
        resp = httpx.get(url, params={"overview": "false"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == "Ok" and data.get("routes"):
            route = data["routes"][0]
            return {
                "duration_minutes": round(route["duration"] / 60, 1),
                "distance_miles": round(route["distance"] / _METERS_PER_MILE, 1),
            }
    except Exception:
        logger.warning(
            "OSRM %s route failed for (%s,%s)->(%s,%s)",
            profile,
            origin_lat,
            origin_lon,
            dest_lat,
            dest_lon,
            exc_info=True,
        )
    return None


def get_travel_times(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
) -> dict[str, int | None]:
    """Get both driving and walking times via OSRM.

    Returns {"drive_minutes": int | None, "walk_minutes": int | None}.
    """
    result: dict[str, int | None] = {"drive_minutes": None, "walk_minutes": None}

    car = get_osrm_route(origin_lat, origin_lon, dest_lat, dest_lon, profile="car")
    if car:
        result["drive_minutes"] = int(round(car["duration_minutes"]))

    foot = get_osrm_route(origin_lat, origin_lon, dest_lat, dest_lon, profile="foot")
    if foot:
        result["walk_minutes"] = int(round(foot["duration_minutes"]))

    return result


# ---------------------------------------------------------------------------
# OSRM Table API — batch travel times
# ---------------------------------------------------------------------------


def get_travel_times_batch(
    origin_lat: float,
    origin_lon: float,
    destinations: list[tuple[float, float]],
    profile: str = "car",
) -> list[dict[str, float | None]]:
    """1-to-N travel times/distances in a single OSRM Table API call.

    Args:
        origin_lat: Origin latitude.
        origin_lon: Origin longitude.
        destinations: List of (lat, lon) tuples for each destination.
        profile: OSRM routing profile ("car" or "foot").

    Returns:
        List of {"duration_minutes": float | None, "distance_miles": float | None}
        in the same order as *destinations*. On total failure, returns a list of
        None-valued dicts.
    """
    settings = get_settings()
    empty: list[dict[str, float | None]] = [
        {"duration_minutes": None, "distance_miles": None} for _ in destinations
    ]

    if not destinations:
        return []

    if settings.osrm_rate_limit_seconds > 0:
        time.sleep(settings.osrm_rate_limit_seconds)

    coords = f"{origin_lon},{origin_lat}" + "".join(f";{lon},{lat}" for lat, lon in destinations)
    url = f"{settings.osrm_base_url}/table/v1/{profile}/{coords}"

    try:
        resp = httpx.get(
            url,
            params={"sources": "0", "annotations": "duration,distance"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != "Ok":
            logger.warning("OSRM table %s returned code=%s", profile, data.get("code"))
            return empty

        durations = data.get("durations", [[]])[0]
        distances = data.get("distances", [[]])[0]

        results: list[dict[str, float | None]] = []
        for i in range(len(destinations)):
            dur = durations[i + 1] if i + 1 < len(durations) else None
            dist = distances[i + 1] if i + 1 < len(distances) else None
            results.append(
                {
                    "duration_minutes": round(dur / 60, 1) if dur is not None else None,
                    "distance_miles": round(dist / _METERS_PER_MILE, 1)
                    if dist is not None
                    else None,
                }
            )
        return results

    except Exception:
        logger.warning(
            "OSRM table %s call failed for origin (%s,%s) with %d destinations",
            profile,
            origin_lat,
            origin_lon,
            len(destinations),
            exc_info=True,
        )
        return empty

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
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pricepoint.config.settings import get_settings
from pricepoint.db.models import NcesSchool, PropertySchool, School

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
                    func.ST_Geography(NcesSchool.location),
                    func.ST_Geography(property_point),
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
# Orchestrator
# ---------------------------------------------------------------------------


def enrich_school(
    session: Session,
    school: School,
    property_lat: float,
    property_lon: float,
) -> bool:
    """Enrich a single school with address and compute travel times.

    1. If school.address is already set, skip address lookup
    2. Try NCES match -> set address, nces_id, location (if missing)
    3. If no NCES match, try Nominatim -> set address, location
    4. If both fail, set needs_review = True
    5. If school has location, compute drive/walk times via OSRM
    6. Return True if any enrichment was made
    """
    changed = False

    # Address lookup
    if not school.address:
        nces = match_nces_school(session, school.name, property_lat, property_lon)
        if nces:
            parts = [p for p in [nces.street, nces.city, nces.state, nces.zip_code] if p]
            school.address = ", ".join(parts) if parts else None
            school.nces_id = nces.nces_id
            if school.location is None and nces.location is not None:
                school.location = nces.location
            changed = True
        else:
            nom = geocode_school_nominatim(school.name, property_lat, property_lon)
            if nom:
                school.address = nom["address"]
                if school.location is None:
                    school.location = from_shape(Point(nom["lon"], nom["lat"]), srid=4326)
                changed = True
            else:
                school.needs_review = True
                changed = True

    # Travel times
    if school.location is not None:
        school_point = to_shape(school.location)
        school_lat, school_lon = school_point.y, school_point.x
        times = get_travel_times(property_lat, property_lon, school_lat, school_lon)

        # Update PropertySchool linkages with travel times
        links = (
            session.execute(select(PropertySchool).where(PropertySchool.school_id == school.id))
            .scalars()
            .all()
        )
        for link in links:
            if times["drive_minutes"] is not None:
                link.drive_minutes = times["drive_minutes"]
                changed = True
            if times["walk_minutes"] is not None:
                link.walk_minutes = times["walk_minutes"]
                changed = True

    if changed:
        session.flush()

    return changed


def enrich_property_schools(
    session: Session,
    property_id: int,
    property_lat: float,
    property_lon: float,
) -> int:
    """Enrich all schools linked to a property. Returns count enriched."""
    links = (
        session.execute(select(PropertySchool).where(PropertySchool.property_id == property_id))
        .scalars()
        .all()
    )

    enriched = 0
    for link in links:
        school = session.get(School, link.school_id)
        if school and enrich_school(session, school, property_lat, property_lon):
            enriched += 1

    return enriched

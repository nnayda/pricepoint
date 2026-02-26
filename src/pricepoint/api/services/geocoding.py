"""Geocoding service — provider-agnostic wrapper for Nominatim and Photon."""

from __future__ import annotations

import logging
import re
import time
from typing import Any

import httpx

from pricepoint.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

_USER_AGENT = "PricePoint/1.0"


# ---------------------------------------------------------------------------
# Response parsers
# ---------------------------------------------------------------------------


def _parse_nominatim(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract fields from a Nominatim JSON response array."""
    results: list[dict[str, Any]] = []
    for item in items:
        display_name = _build_nominatim_display_name(item)
        results.append(
            {
                "display_name": display_name,
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
                "place_id": item.get("place_id"),
                "osm_type": item.get("osm_type", ""),
                "osm_id": item.get("osm_id", 0),
                "boundingbox": [float(b) for b in item["boundingbox"]]
                if "boundingbox" in item
                else [],
            }
        )
    return results


def _build_nominatim_display_name(item: dict[str, Any]) -> str:
    """Build display name from Nominatim addressdetails when available.

    Nominatim's raw ``display_name`` sometimes omits the house number for
    street-level matches.  When ``address`` details are present we assemble
    the name ourselves so the house number is always included.
    """
    addr = item.get("address")
    if not addr:
        return item["display_name"]

    house_number = addr.get("house_number")
    road = addr.get("road")

    parts: list[str] = []
    if house_number and road:
        parts.append(f"{house_number} {road}")
    elif road:
        parts.append(road)
    elif house_number:
        parts.append(house_number)

    for key in ("city", "town", "village", "county", "state", "postcode", "country"):
        val = addr.get(key)
        if val:
            parts.append(str(val))

    return ", ".join(parts) if parts else item["display_name"]


_LEADING_HOUSE_NUMBER_RE = re.compile(r"^\s*(\d+[\w-]*)\s+")


def _extract_house_number(query: str) -> str | None:
    """Extract a leading house number from the user's search query."""
    m = _LEADING_HOUSE_NUMBER_RE.match(query)
    return m.group(1) if m else None


def _parse_photon(data: dict[str, Any], query: str = "") -> list[dict[str, Any]]:
    """Parse a Photon GeoJSON response into the standard result format.

    Photon returns GeoJSON FeatureCollection with [lon, lat] coordinates.
    Filters to US results only (``countrycode == "US"``).

    When *query* is provided and contains a leading house number, that number
    is injected into street-level results that Photon returned without a
    ``housenumber`` property.
    """
    query_house_number = _extract_house_number(query) if query else None

    results: list[dict[str, Any]] = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        # Filter to US only
        if props.get("countrycode", "").upper() != "US":
            continue

        coords = feature.get("geometry", {}).get("coordinates", [])
        if len(coords) < 2:
            continue

        lon, lat = float(coords[0]), float(coords[1])

        # Assemble display_name from address properties.
        # Combine housenumber + street into a single address line so
        # downstream parsing can extract the house number from parts[0].
        name = props.get("name")
        street = props.get("street")
        housenumber = props.get("housenumber")

        # Inject the house number from the query into street-level results
        # that Photon returned without one.
        if not housenumber and query_house_number and props.get("type") == "street":
            housenumber = query_house_number

        parts: list[str] = []
        if housenumber and street:
            parts.append(f"{housenumber} {street}")
            # Only include name if it differs from the street
            if name and name != street:
                parts.insert(0, str(name))
        elif street:
            if name and name != street:
                parts.append(str(name))
            parts.append(str(street))
        elif housenumber and name:
            parts.append(f"{housenumber} {name}")
        elif name:
            parts.append(str(name))

        for key in ("city", "state", "postcode", "country"):
            val = props.get(key)
            if val:
                parts.append(str(val))
        display_name = ", ".join(parts) if parts else props.get("name", "")

        results.append(
            {
                "display_name": display_name,
                "lat": lat,
                "lon": lon,
                "place_id": None,
                "osm_type": props.get("osm_type", ""),
                "osm_id": props.get("osm_id", 0),
                "boundingbox": [],
            }
        )
    return results


# ---------------------------------------------------------------------------
# Parameter builders
# ---------------------------------------------------------------------------


def _build_nominatim_params(
    query: str,
    limit: int,
    bias_lat: float | None,
    bias_lon: float | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "q": query,
        "format": "json",
        "addressdetails": 1,
        "limit": limit,
        "countrycodes": "us",
    }
    if bias_lat is not None and bias_lon is not None:
        delta = 0.15  # ~10 miles
        params["viewbox"] = (
            f"{bias_lon - delta},{bias_lat + delta},{bias_lon + delta},{bias_lat - delta}"
        )
        params["bounded"] = 0
    return params


def _build_photon_params(
    query: str,
    limit: int,
    bias_lat: float | None,
    bias_lon: float | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "q": query,
        "limit": limit,
        "lang": "en",
    }
    if bias_lat is not None and bias_lon is not None:
        params["lat"] = bias_lat
        params["lon"] = bias_lon
    return params


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def geocode_async(
    query: str,
    limit: int = 5,
    *,
    bias_lat: float | None = None,
    bias_lon: float | None = None,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Geocode asynchronously (for FastAPI routes).

    Returns a list of dicts with keys:
    ``display_name``, ``lat``, ``lon``, ``place_id``, ``osm_type``,
    ``osm_id``, ``boundingbox``.
    """
    cfg = settings or get_settings()
    provider = cfg.geocode_provider.lower()

    if provider == "photon":
        params = _build_photon_params(query, limit, bias_lat, bias_lon)
    else:
        params = _build_nominatim_params(query, limit, bias_lat, bias_lon)

    try:
        async with httpx.AsyncClient(timeout=cfg.geocode_timeout) as client:
            resp = await client.get(
                cfg.geocode_url,
                params=params,
                headers={"User-Agent": _USER_AGENT},
            )
            resp.raise_for_status()
    except httpx.TimeoutException:
        logger.warning("Geocode request timed out for q=%r", query)
        return []
    except httpx.HTTPStatusError:
        logger.warning("Geocode provider returned error for q=%r", query, exc_info=True)
        return []
    except httpx.HTTPError:
        logger.warning("Geocode request failed for q=%r", query, exc_info=True)
        return []

    raw = resp.json()

    if provider == "photon":
        return _parse_photon(raw, query)
    return _parse_nominatim(raw)


def geocode_sync(
    query: str,
    limit: int = 5,
    *,
    bias_lat: float | None = None,
    bias_lon: float | None = None,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Geocode synchronously (for Airflow / data pipelines).

    Applies ``geocode_rate_limit_seconds`` sleep when > 0.
    """
    cfg = settings or get_settings()
    provider = cfg.geocode_provider.lower()

    if cfg.geocode_rate_limit_seconds > 0:
        time.sleep(cfg.geocode_rate_limit_seconds)

    if provider == "photon":
        params = _build_photon_params(query, limit, bias_lat, bias_lon)
    else:
        params = _build_nominatim_params(query, limit, bias_lat, bias_lon)

    try:
        resp = httpx.get(
            cfg.geocode_url,
            params=params,
            headers={"User-Agent": _USER_AGENT},
            timeout=cfg.geocode_timeout,
        )
        resp.raise_for_status()
    except httpx.HTTPError:
        logger.warning("Geocode request failed for q=%r", query, exc_info=True)
        return []

    raw = resp.json()

    if provider == "photon":
        return _parse_photon(raw, query)
    return _parse_nominatim(raw)

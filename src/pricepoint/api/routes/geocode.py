"""Geocode endpoint — proxy to Nominatim with Valkey caching."""

import json
import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis

from pricepoint.api.dependencies import get_valkey
from pricepoint.api.schemas.geocode import GeocodeResponse, GeocodeResult

logger = logging.getLogger(__name__)

router = APIRouter(tags=["geocode"])

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_TIMEOUT = 5.0
CACHE_TTL = 86400  # 24 hours
MAX_LIMIT = 10


@router.get("/geocode", response_model=GeocodeResponse)
async def geocode(
    q: Annotated[str, Query(min_length=2)],
    limit: Annotated[int, Query(ge=1)] = 5,
    valkey: Annotated[Redis | None, Depends(get_valkey)] = None,
) -> GeocodeResponse:
    """Look up addresses via Nominatim, with optional Valkey caching."""
    limit = min(limit, MAX_LIMIT)
    normalized_q = q.strip().lower()
    cache_key = f"geocode:{normalized_q}:{limit}"

    # Try cache first
    if valkey is not None:
        try:
            cached = await valkey.get(cache_key)
            if cached is not None:
                results = [GeocodeResult(**r) for r in json.loads(cached)]
                return GeocodeResponse(results=results, cached=True)
        except Exception:
            logger.warning("Valkey read failed for key %s", cache_key, exc_info=True)

    # Call Nominatim
    try:
        async with httpx.AsyncClient(timeout=NOMINATIM_TIMEOUT) as client:
            resp = await client.get(
                NOMINATIM_URL,
                params={
                    "q": q,
                    "format": "json",
                    "limit": limit,
                    "countrycodes": "us",
                },
                headers={"User-Agent": "PricePoint/0.1.0"},
            )
            resp.raise_for_status()
    except httpx.TimeoutException:
        logger.warning("Nominatim request timed out for q=%r", q)
        return GeocodeResponse(results=[], cached=False)
    except httpx.HTTPStatusError:
        logger.warning("Nominatim returned error for q=%r", q, exc_info=True)
        return GeocodeResponse(results=[], cached=False)
    except httpx.HTTPError:
        logger.warning("Nominatim request failed for q=%r", q, exc_info=True)
        return GeocodeResponse(results=[], cached=False)

    raw = resp.json()
    results = [
        GeocodeResult(
            display_name=item["display_name"],
            lat=float(item["lat"]),
            lon=float(item["lon"]),
            place_id=item["place_id"],
            osm_type=item["osm_type"],
            osm_id=item["osm_id"],
            boundingbox=[float(b) for b in item["boundingbox"]],
        )
        for item in raw
    ]

    # Write to cache
    if valkey is not None and results:
        try:
            await valkey.set(
                cache_key,
                json.dumps([r.model_dump() for r in results]),
                ex=CACHE_TTL,
            )
        except Exception:
            logger.warning("Valkey write failed for key %s", cache_key, exc_info=True)

    return GeocodeResponse(results=results, cached=False)

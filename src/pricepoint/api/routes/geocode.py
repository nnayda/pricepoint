"""Geocode endpoint — proxy to geocoding provider with Valkey caching."""

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis

from pricepoint.api.dependencies import get_valkey
from pricepoint.api.schemas.geocode import GeocodeResponse, GeocodeResult
from pricepoint.api.services.geocoding import geocode_async
from pricepoint.config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["geocode"])

MAX_LIMIT = 10


@router.get("/geocode", response_model=GeocodeResponse)
async def geocode(
    q: Annotated[str, Query(min_length=2)],
    limit: Annotated[int, Query(ge=1)] = 5,
    valkey: Annotated[Redis | None, Depends(get_valkey)] = None,
) -> GeocodeResponse:
    """Look up addresses via geocoding provider, with optional Valkey caching."""
    limit = min(limit, MAX_LIMIT)
    normalized_q = q.strip().lower()
    cache_key = f"geocode:{normalized_q}:{limit}"
    cache_ttl = get_settings().cache_ttl_geocode

    # Try cache first
    if valkey is not None:
        try:
            cached = await valkey.get(cache_key)
            if cached is not None:
                results = [GeocodeResult(**r) for r in json.loads(cached)]
                return GeocodeResponse(results=results, cached=True)
        except Exception:
            logger.warning("Valkey read failed for key %s", cache_key, exc_info=True)

    # Call geocoding provider
    raw_results = await geocode_async(q, limit=limit)
    results = [GeocodeResult(**r) for r in raw_results]

    # Write to cache
    if valkey is not None and results:
        try:
            await valkey.set(
                cache_key,
                json.dumps([r.model_dump() for r in results]),
                ex=cache_ttl,
            )
        except Exception:
            logger.warning("Valkey write failed for key %s", cache_key, exc_info=True)

    return GeocodeResponse(results=results, cached=False)

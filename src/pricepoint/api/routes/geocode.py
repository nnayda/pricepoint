"""Geocode endpoint — proxy to geocoding provider with Valkey caching.

Lookup order: Valkey cache → local DB (redfin_listings) → external geocoder.
"""

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from geoalchemy2.functions import ST_X, ST_Y
from redis.asyncio import Redis
from sqlalchemy import func
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db, get_valkey
from pricepoint.api.schemas.geocode import GeocodeResponse, GeocodeResult
from pricepoint.api.services.geocoding import geocode_async
from pricepoint.config.settings import get_settings
from pricepoint.db.models import RedfinListing

logger = logging.getLogger(__name__)

router = APIRouter(tags=["geocode"])

MAX_LIMIT = 10


def _search_db_properties(db: Session, query: str, limit: int) -> list[GeocodeResult]:
    """Search RedfinListing table for addresses matching *query*."""
    full_address = func.concat(
        RedfinListing.street_address,
        ", ",
        RedfinListing.city,
        ", ",
        RedfinListing.state,
        " ",
        RedfinListing.zip_code,
    )
    rows = (
        db.query(
            full_address.label("display_name"),
            ST_Y(RedfinListing.location).label("lat"),
            ST_X(RedfinListing.location).label("lon"),
            RedfinListing.id,
        )
        .filter(
            RedfinListing.location.isnot(None),
            full_address.ilike(f"%{query}%"),
        )
        .limit(limit)
        .all()
    )
    return [
        GeocodeResult(
            display_name=row.display_name,
            lat=row.lat,
            lon=row.lon,
            place_id=None,
            osm_type="property",
            osm_id=row.id,
            boundingbox=[],
        )
        for row in rows
    ]


@router.get("/geocode", response_model=GeocodeResponse)
async def geocode(
    q: Annotated[str, Query(min_length=2)],
    limit: Annotated[int, Query(ge=1)] = 5,
    valkey: Annotated[Redis | None, Depends(get_valkey)] = None,
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
) -> GeocodeResponse:
    """Look up addresses via geocoding provider, with optional Valkey caching."""
    limit = min(limit, MAX_LIMIT)
    normalized_q = q.strip().lower()
    cache_key = f"geocode:{normalized_q}:{limit}"
    cache_ttl = get_settings().cache_ttl_geocode

    # 1. Try cache first
    if valkey is not None:
        try:
            cached = await valkey.get(cache_key)
            if cached is not None:
                results = [GeocodeResult(**r) for r in json.loads(cached)]
                return GeocodeResponse(results=results, cached=True)
        except Exception:
            logger.warning("Valkey read failed for key %s", cache_key, exc_info=True)

    # 2. Search local DB (redfin_listings)
    try:
        db_results = _search_db_properties(db, normalized_q, limit)
    except Exception:
        logger.warning("DB property search failed for query %r", q, exc_info=True)
        db_results = []

    if db_results:
        # Cache DB results the same way we cache external results
        if valkey is not None:
            try:
                await valkey.set(
                    cache_key,
                    json.dumps([r.model_dump() for r in db_results]),
                    ex=cache_ttl,
                )
            except Exception:
                logger.warning("Valkey write failed for key %s", cache_key, exc_info=True)
        return GeocodeResponse(results=db_results, cached=False)

    # 3. Fall back to external geocoding provider
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

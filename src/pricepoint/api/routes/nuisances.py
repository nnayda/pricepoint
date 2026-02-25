"""Nuisances endpoint — returns transportation noise polygons from PostGIS."""

import hashlib
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_MakePoint, ST_SetSRID
from redis.asyncio import Redis
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db, get_valkey
from pricepoint.api.schemas.nuisances import (
    NoiseFeature,
    NoiseProperties,
    NoiseResponse,
)
from pricepoint.db.models import TransportationNoise

logger = logging.getLogger(__name__)

router = APIRouter(tags=["nuisances"])

METERS_PER_MILE = 1609.344
CACHE_TTL = 604800  # 7 days


def _cache_key(lat: float, lon: float, radius_miles: float) -> str:
    """Build a deterministic cache key for the noise query."""
    raw = f"nuisances:noise:{lat:.6f}:{lon:.6f}:{radius_miles:.2f}"
    digest = hashlib.md5(raw.encode()).hexdigest()  # noqa: S324
    return f"nuisances:noise:{digest}"


@router.get("/nuisances/noise", response_model=NoiseResponse)
async def get_noise(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    radius_miles: Annotated[float, Query(gt=0, le=10)] = 2.0,
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
    valkey: Annotated[Redis | None, Depends(get_valkey)] = None,
) -> NoiseResponse:
    """Return transportation noise polygons near the given location."""
    # Check cache
    c_key = _cache_key(lat, lon, radius_miles)
    if valkey is not None:
        try:
            cached = await valkey.get(c_key)
            if cached is not None:
                data = json.loads(cached)
                return NoiseResponse(**data)
        except Exception:
            logger.warning("Valkey read failed for key %s", c_key, exc_info=True)

    radius_meters = radius_miles * METERS_PER_MILE

    # Build geography point
    property_point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

    # Query noise polygons within radius using ST_DWithin on geography casts
    geog_type = Geography(srid=4326)
    stmt = (
        select(
            func.ST_AsGeoJSON(TransportationNoise.geom).label("geojson"),
            TransportationNoise.noise_band,
            TransportationNoise.noise_min_db,
            TransportationNoise.noise_max_db,
            TransportationNoise.source_layer,
            TransportationNoise.area_sq_m,
        )
        .where(
            TransportationNoise.geom.isnot(None),
            func.ST_DWithin(
                cast(TransportationNoise.geom, geog_type),
                cast(property_point, geog_type),
                radius_meters,
            ),
        )
        .order_by(TransportationNoise.noise_min_db)
    )

    rows = db.execute(stmt).all()

    features: list[NoiseFeature] = []
    for row in rows:
        features.append(
            NoiseFeature(
                geometry=json.loads(row.geojson),
                properties=NoiseProperties(
                    noise_band=row.noise_band,
                    noise_min_db=row.noise_min_db,
                    noise_max_db=row.noise_max_db,
                    source_layer=row.source_layer,
                    area_sq_m=row.area_sq_m,
                ),
            )
        )

    response = NoiseResponse(features=features)

    # Write to cache
    if valkey is not None:
        try:
            await valkey.set(
                c_key,
                json.dumps(response.model_dump()),
                ex=CACHE_TTL,
            )
        except Exception:
            logger.warning("Valkey write failed for key %s", c_key, exc_info=True)

    return response

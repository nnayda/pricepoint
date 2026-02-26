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
    InfrastructureFeature,
    InfrastructureGeometriesResponse,
    NoiseFeature,
    NoiseProperties,
    NoiseResponse,
    NuisanceSource,
    NuisanceSourcesResponse,
)
from pricepoint.db.models import Airport, Railroad, Road, TransportationNoise

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


@router.get("/nuisances/sources", response_model=NuisanceSourcesResponse)
async def get_nuisance_sources(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
) -> NuisanceSourcesResponse:
    """Return identified nuisance sources near the given location.

    Finds noise polygons containing the property, identifies the loudest
    polygon per source layer, then queries the nearest matching infrastructure
    (airport, road, or railroad) for detail.
    """
    property_point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
    geog_type = Geography(srid=4326)

    # Find noise polygons that contain the property point
    stmt = (
        select(
            TransportationNoise.source_layer,
            func.max(TransportationNoise.noise_min_db).label("max_db"),
            func.min(TransportationNoise.noise_band).label("noise_band"),
        )
        .where(
            TransportationNoise.geom.isnot(None),
            func.ST_Intersects(TransportationNoise.geom, property_point),
        )
        .group_by(TransportationNoise.source_layer)
    )
    noise_rows = db.execute(stmt).all()

    sources: list[NuisanceSource] = []

    for row in noise_rows:
        source_layer: str = row.source_layer
        max_db: int = row.max_db
        noise_band: str = row.noise_band
        severity = "Concern" if max_db >= 55 else "Caution"

        # Determine nearest infrastructure source based on layer type
        if source_layer == "aviation":
            _add_aviation_source(
                db, property_point, geog_type, source_layer, severity, max_db, noise_band, sources
            )
        elif source_layer == "road":
            _add_road_source(
                db, property_point, geog_type, source_layer, severity, max_db, noise_band, sources
            )
        elif source_layer == "rail":
            _add_rail_source(
                db, property_point, geog_type, source_layer, severity, max_db, noise_band, sources
            )

    return NuisanceSourcesResponse(sources=sources)


def _add_aviation_source(
    db: Session,
    point: object,
    geog_type: Geography,
    source_layer: str,
    severity: str,
    max_db: int,
    noise_band: str,
    sources: list[NuisanceSource],
) -> None:
    """Find nearest airport and add as a nuisance source."""
    dist_col = func.ST_Distance(
        cast(Airport.geom, geog_type),
        cast(point, geog_type),
    ).label("dist_m")

    airport_row = db.execute(
        select(
            Airport.name,
            Airport.iata_code,
            func.ST_Y(Airport.geom).label("lat"),
            func.ST_X(Airport.geom).label("lon"),
            dist_col,
        )
        .where(Airport.geom.isnot(None))
        .order_by(dist_col)
        .limit(1)
    ).first()

    if airport_row:
        name = airport_row.name
        if airport_row.iata_code:
            name = f"{name} ({airport_row.iata_code})"
        sources.append(
            NuisanceSource(
                id=f"aviation-{airport_row.iata_code or 'nearest'}",
                name=name,
                source_type=source_layer,
                severity=severity,
                distance_miles=round(airport_row.dist_m / METERS_PER_MILE, 1),
                lat=airport_row.lat,
                lon=airport_row.lon,
                detail=f"Airport noise zone ({noise_band})",
                noise_min_db=max_db,
                noise_band=noise_band,
            )
        )


def _add_road_source(
    db: Session,
    point: object,
    geog_type: Geography,
    source_layer: str,
    severity: str,
    max_db: int,
    noise_band: str,
    sources: list[NuisanceSource],
) -> None:
    """Find nearest road and add as a nuisance source."""
    dist_col = func.ST_Distance(
        cast(Road.geom, geog_type),
        cast(point, geog_type),
    ).label("dist_m")

    closest_pt = func.ST_ClosestPoint(Road.geom, point)

    road_row = db.execute(
        select(
            Road.fullname,
            func.ST_Y(closest_pt).label("lat"),
            func.ST_X(closest_pt).label("lon"),
            dist_col,
        )
        .where(Road.geom.isnot(None))
        .order_by(dist_col)
        .limit(1)
    ).first()

    if road_row:
        road_name = road_row.fullname or "Unnamed Road"
        sources.append(
            NuisanceSource(
                id=f"road-{road_name.lower().replace(' ', '-')}",
                name=road_name,
                source_type=source_layer,
                severity=severity,
                distance_miles=round(road_row.dist_m / METERS_PER_MILE, 1),
                lat=road_row.lat,
                lon=road_row.lon,
                detail=f"Road traffic noise zone ({noise_band})",
                noise_min_db=max_db,
                noise_band=noise_band,
            )
        )


def _add_rail_source(
    db: Session,
    point: object,
    geog_type: Geography,
    source_layer: str,
    severity: str,
    max_db: int,
    noise_band: str,
    sources: list[NuisanceSource],
) -> None:
    """Find nearest railroad and add as a nuisance source."""
    dist_col = func.ST_Distance(
        cast(Railroad.geom, geog_type),
        cast(point, geog_type),
    ).label("dist_m")

    closest_pt = func.ST_ClosestPoint(Railroad.geom, point)

    rail_row = db.execute(
        select(
            Railroad.rrowner1,
            Railroad.subdivision,
            func.ST_Y(closest_pt).label("lat"),
            func.ST_X(closest_pt).label("lon"),
            dist_col,
        )
        .where(Railroad.geom.isnot(None))
        .order_by(dist_col)
        .limit(1)
    ).first()

    if rail_row:
        name = rail_row.rrowner1 or "Railroad"
        if rail_row.subdivision:
            name = f"{name} — {rail_row.subdivision}"
        sources.append(
            NuisanceSource(
                id=f"rail-{(rail_row.rrowner1 or 'nearest').lower().replace(' ', '-')}",
                name=name,
                source_type=source_layer,
                severity=severity,
                distance_miles=round(rail_row.dist_m / METERS_PER_MILE, 1),
                lat=rail_row.lat,
                lon=rail_row.lon,
                detail=f"Railroad noise zone ({noise_band})",
                noise_min_db=max_db,
                noise_band=noise_band,
            )
        )


@router.get("/nuisances/geometries", response_model=InfrastructureGeometriesResponse)
async def get_nuisance_geometries(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    radius_miles: Annotated[float, Query(gt=0, le=10)] = 2.0,
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
) -> InfrastructureGeometriesResponse:
    """Return infrastructure geometries (roads, airports, railroads) near the given location.

    Returns a GeoJSON FeatureCollection with features tagged by layer.
    """
    property_point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
    geog_type = Geography(srid=4326)
    radius_meters = radius_miles * METERS_PER_MILE

    features: list[InfrastructureFeature] = []

    # Roads
    road_rows = db.execute(
        select(
            func.ST_AsGeoJSON(Road.geom).label("geojson"),
            Road.fullname,
        )
        .where(
            Road.geom.isnot(None),
            func.ST_DWithin(
                cast(Road.geom, geog_type),
                cast(property_point, geog_type),
                radius_meters,
            ),
        )
    ).all()

    for row in road_rows:
        features.append(
            InfrastructureFeature(
                geometry=json.loads(row.geojson),
                properties={"layer": "road", "fullname": row.fullname or ""},
            )
        )

    # Airports
    airport_rows = db.execute(
        select(
            func.ST_AsGeoJSON(Airport.geom).label("geojson"),
            Airport.name,
            Airport.iata_code,
        )
        .where(
            Airport.geom.isnot(None),
            func.ST_DWithin(
                cast(Airport.geom, geog_type),
                cast(property_point, geog_type),
                radius_meters,
            ),
        )
    ).all()

    for row in airport_rows:
        features.append(
            InfrastructureFeature(
                geometry=json.loads(row.geojson),
                properties={
                    "layer": "airport",
                    "name": row.name or "",
                    "iata_code": row.iata_code or "",
                },
            )
        )

    # Railroads
    rail_rows = db.execute(
        select(
            func.ST_AsGeoJSON(Railroad.geom).label("geojson"),
            Railroad.rrowner1,
            Railroad.subdivision,
        )
        .where(
            Railroad.geom.isnot(None),
            func.ST_DWithin(
                cast(Railroad.geom, geog_type),
                cast(property_point, geog_type),
                radius_meters,
            ),
        )
    ).all()

    for row in rail_rows:
        features.append(
            InfrastructureFeature(
                geometry=json.loads(row.geojson),
                properties={
                    "layer": "railroad",
                    "rrowner1": row.rrowner1 or "",
                    "subdivision": row.subdivision or "",
                },
            )
        )

    return InfrastructureGeometriesResponse(features=features)

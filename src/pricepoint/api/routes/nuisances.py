"""Nuisances endpoint — returns nuisance source cards from PostGIS.

Noise polygon geometry and infrastructure geometry are served via Martin
vector tiles (see docker/martin/config.yaml).  This module only provides
the card-level severity data for the sidebar.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_DWithin, ST_MakePoint, ST_SetSRID
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db
from pricepoint.api.schemas.nuisances import (
    NuisanceSource,
    NuisanceSourcesResponse,
)
from pricepoint.db.models import (
    Airport,
    PropertyGeoLookup,
    Railroad,
    RedfinListing,
    Road,
    TransportationNoise,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["nuisances"])

METERS_PER_MILE = 1609.344


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

    # Fast-path: if precomputed lookup says not in noise zone, skip queries
    lookup = db.execute(
        select(PropertyGeoLookup.in_noise_zone)
        .join(RedfinListing, RedfinListing.id == PropertyGeoLookup.property_id)
        .where(
            RedfinListing.location.isnot(None),
            ST_DWithin(RedfinListing.location, property_point, 0.001),
        )
        .limit(1)
    ).scalar_one_or_none()

    if lookup is not None and not lookup:
        return NuisanceSourcesResponse(sources=[])

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



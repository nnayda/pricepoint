"""Utilities endpoint — returns infrastructure features from PostGIS spatial queries."""

import hashlib
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_X, ST_Y, ST_MakePoint, ST_SetSRID
from redis.asyncio import Redis
from sqlalchemy import String, cast, func, literal, select, union_all
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db, get_valkey
from pricepoint.api.schemas.utilities import (
    UtilitiesMetrics,
    UtilitiesResponse,
    UtilityFeature,
)
from pricepoint.db.models import (
    CellTower,
    NatGasPipeline,
    PetroleumPipeline,
    PowerPlant,
    TransmissionLine,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["utilities"])

METERS_PER_MILE = 1609.344
CACHE_TTL = 604800  # 7 days


def _st_dwithin_geography(geom_col, point, radius_meters: float):  # noqa: ANN001, ANN201
    """ST_DWithin using geography cast for meter-based distance."""
    return func.ST_DWithin(
        cast(geom_col, Geography()),
        cast(point, Geography()),
        radius_meters,
    )


def _build_features_query(property_point, radius_meters: float):  # noqa: ANN001, ANN201
    """Build a UNION ALL query across infrastructure tables.

    Returns id, name, feature_type, centroid lat/lon, and distance in miles.
    """
    # Cell towers
    cell_tower_q = select(
        cast(CellTower.id, String).label("feature_id"),
        func.coalesce(CellTower.licensee, "Cell Tower").label("name"),
        literal("cell_tower").label("feature_type"),
        ST_Y(CellTower.geom).label("lat"),
        ST_X(CellTower.geom).label("lon"),
        (
            func.ST_Distance(
                cast(property_point, Geography()),
                cast(CellTower.geom, Geography()),
            )
            / METERS_PER_MILE
        ).label("distance_miles"),
    ).where(
        CellTower.geom.isnot(None),
        _st_dwithin_geography(CellTower.geom, property_point, radius_meters),
    )

    # Transmission lines
    transmission_q = select(
        cast(TransmissionLine.id, String).label("feature_id"),
        func.coalesce(TransmissionLine.owner, "Transmission Line").label("name"),
        literal("transmission_line").label("feature_type"),
        ST_Y(func.ST_Centroid(TransmissionLine.geom)).label("lat"),
        ST_X(func.ST_Centroid(TransmissionLine.geom)).label("lon"),
        (
            func.ST_Distance(
                cast(property_point, Geography()),
                cast(TransmissionLine.geom, Geography()),
            )
            / METERS_PER_MILE
        ).label("distance_miles"),
    ).where(
        TransmissionLine.geom.isnot(None),
        _st_dwithin_geography(TransmissionLine.geom, property_point, radius_meters),
    )

    # Power plants
    power_plant_q = select(
        cast(PowerPlant.id, String).label("feature_id"),
        func.coalesce(PowerPlant.name, "Power Plant").label("name"),
        literal("power_plant").label("feature_type"),
        ST_Y(PowerPlant.geom).label("lat"),
        ST_X(PowerPlant.geom).label("lon"),
        (
            func.ST_Distance(
                cast(property_point, Geography()),
                cast(PowerPlant.geom, Geography()),
            )
            / METERS_PER_MILE
        ).label("distance_miles"),
    ).where(
        PowerPlant.geom.isnot(None),
        _st_dwithin_geography(PowerPlant.geom, property_point, radius_meters),
    )

    # Natural gas pipelines
    nat_gas_q = select(
        cast(NatGasPipeline.id, String).label("feature_id"),
        func.coalesce(NatGasPipeline.operator, "Natural Gas Pipeline").label("name"),
        literal("nat_gas_pipeline").label("feature_type"),
        ST_Y(func.ST_Centroid(NatGasPipeline.geom)).label("lat"),
        ST_X(func.ST_Centroid(NatGasPipeline.geom)).label("lon"),
        (
            func.ST_Distance(
                cast(property_point, Geography()),
                cast(NatGasPipeline.geom, Geography()),
            )
            / METERS_PER_MILE
        ).label("distance_miles"),
    ).where(
        NatGasPipeline.geom.isnot(None),
        _st_dwithin_geography(NatGasPipeline.geom, property_point, radius_meters),
    )

    # Petroleum pipelines
    petroleum_q = select(
        cast(PetroleumPipeline.id, String).label("feature_id"),
        func.coalesce(PetroleumPipeline.operator, "Petroleum Pipeline").label("name"),
        literal("petroleum_pipeline").label("feature_type"),
        ST_Y(func.ST_Centroid(PetroleumPipeline.geom)).label("lat"),
        ST_X(func.ST_Centroid(PetroleumPipeline.geom)).label("lon"),
        (
            func.ST_Distance(
                cast(property_point, Geography()),
                cast(PetroleumPipeline.geom, Geography()),
            )
            / METERS_PER_MILE
        ).label("distance_miles"),
    ).where(
        PetroleumPipeline.geom.isnot(None),
        _st_dwithin_geography(PetroleumPipeline.geom, property_point, radius_meters),
    )

    return union_all(
        cell_tower_q,
        transmission_q,
        power_plant_q,
        nat_gas_q,
        petroleum_q,
    ).cte("all_utilities")


def _compute_nuisance_score(
    nearest_transmission_line: float = 3.0,
    nearest_power_plant: float = 3.0,
    nearest_cell_tower: float = 3.0,
    nearest_pipeline: float = 3.0,
) -> float:
    """Compute nuisance score (0-10) as weighted proximity combination.

    Weights: transmission_line=3, power_plant=3, cell_tower=2, pipeline=1.
    Per-type contribution: weight * max(0, 1 - distance_miles / 3).
    Final score scaled to 0-10.
    """
    max_raw = 3 + 3 + 2 + 1  # 9.0 when all distances are 0

    transmission_contrib = 3 * max(0.0, 1.0 - nearest_transmission_line / 3.0)
    power_plant_contrib = 3 * max(0.0, 1.0 - nearest_power_plant / 3.0)
    cell_tower_contrib = 2 * max(0.0, 1.0 - nearest_cell_tower / 3.0)
    pipeline_contrib = 1 * max(0.0, 1.0 - nearest_pipeline / 3.0)

    raw = transmission_contrib + power_plant_contrib + cell_tower_contrib + pipeline_contrib
    return round((raw / max_raw) * 10.0, 1)


def _cache_key(lat: float, lon: float, radius_miles: float) -> str:
    """Build a deterministic cache key for the utilities query."""
    raw = f"utilities:{lat:.6f}:{lon:.6f}:{radius_miles:.2f}"
    digest = hashlib.md5(raw.encode()).hexdigest()  # noqa: S324
    return f"utilities:{digest}"


@router.get("/utilities", response_model=UtilitiesResponse)
async def get_utilities(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    radius_miles: Annotated[float, Query(gt=0, le=10)] = 3.0,
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
    valkey: Annotated[Redis | None, Depends(get_valkey)] = None,
) -> UtilitiesResponse:
    """Return utility infrastructure features near the given location."""
    # Check cache
    c_key = _cache_key(lat, lon, radius_miles)
    if valkey is not None:
        try:
            cached = await valkey.get(c_key)
            if cached is not None:
                data = json.loads(cached)
                return UtilitiesResponse(**data)
        except Exception:
            logger.warning("Valkey read failed for key %s", c_key, exc_info=True)

    radius_meters = radius_miles * METERS_PER_MILE
    property_point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

    cte = _build_features_query(property_point, radius_meters)

    rows = db.execute(
        select(
            cte.c.feature_id,
            cte.c.name,
            cte.c.feature_type,
            cte.c.lat,
            cte.c.lon,
            cte.c.distance_miles,
        ).order_by(cte.c.distance_miles)
    ).all()

    # Build feature list
    features: list[UtilityFeature] = []
    nearest: dict[str, float] = {}

    for row in rows:
        ftype = row.feature_type
        dist = round(row.distance_miles, 2) if row.distance_miles is not None else 0.0

        features.append(
            UtilityFeature(
                id=f"UT-{ftype[0].upper()}-{row.feature_id}",
                name=row.name or ftype.replace("_", " ").title(),
                feature_type=ftype,
                lat=row.lat,
                lon=row.lon,
                distance_miles=dist,
            )
        )

        # Track nearest distance per type
        if ftype not in nearest or dist < nearest[ftype]:
            nearest[ftype] = dist

    # Compute nearest distances (default to radius_miles if type not found)
    nearest_cell_tower = nearest.get("cell_tower", radius_miles)
    nearest_transmission_line = nearest.get("transmission_line", radius_miles)
    nearest_power_plant = nearest.get("power_plant", radius_miles)
    nearest_pipeline = min(
        nearest.get("nat_gas_pipeline", radius_miles),
        nearest.get("petroleum_pipeline", radius_miles),
    )

    nuisance = _compute_nuisance_score(
        nearest_transmission_line,
        nearest_power_plant,
        nearest_cell_tower,
        nearest_pipeline,
    )

    metrics = UtilitiesMetrics(
        nearest_cell_tower_miles=round(nearest_cell_tower, 2),
        nearest_transmission_line_miles=round(nearest_transmission_line, 2),
        nearest_power_plant_miles=round(nearest_power_plant, 2),
        nearest_pipeline_miles=round(nearest_pipeline, 2),
        nuisance_score=nuisance,
    )

    response = UtilitiesResponse(features=features, metrics=metrics)

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

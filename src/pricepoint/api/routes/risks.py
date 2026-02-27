"""Risks endpoint — returns infrastructure risk features.

Boundary polygon geometry and infrastructure line geometry are now served
via Martin vector tiles (see docker/martin/config.yaml).  This module
provides risk severity assessments for the sidebar card list.
"""

import hashlib
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from geoalchemy2.functions import ST_X, ST_Y, ST_DWithin, ST_MakePoint, ST_SetSRID
from geoalchemy2.types import Geography
from redis.asyncio import Redis
from sqlalchemy import String, cast, func, literal, select, union_all
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db, get_valkey
from pricepoint.api.schemas.risks import RiskFeature, RisksResponse
from pricepoint.db.models import (
    CellTower,
    NatGasPipeline,
    PetroleumPipeline,
    PowerPlant,
    PropertyGeoLookup,
    RedfinListing,
    RiskBoundary,
    TransmissionLine,
)

# Pre-built set for line-geometry models
_LINE_MODELS = {TransmissionLine, NatGasPipeline, PetroleumPipeline}

logger = logging.getLogger(__name__)

router = APIRouter(tags=["risks"])

METERS_PER_MILE = 1609.344
CACHE_TTL = 604800  # 7 days

TYPE_LABELS: dict[str, str] = {
    "cell_tower": "Cell Tower",
    "transmission_line": "Transmission Line",
    "power_plant": "Power Plant",
    "nat_gas_pipeline": "Natural Gas Pipeline",
    "petroleum_pipeline": "Petroleum Pipeline",
}

SEVERITY_PHRASES: dict[str, str] = {
    "critical": "within critical risk zone",
    "caution": "within caution risk zone",
}

SEVERITY_MAP: dict[str, str] = {
    "critical": "Concern",
    "caution": "Caution",
}

# For ORDER BY: Concern first, Caution second, Safe last
SEVERITY_SORT = {"Concern": 0, "Caution": 1, "Safe": 2}


def _st_dwithin_geography(geom_col, point, radius_meters: float):  # noqa: ANN001, ANN201
    """ST_DWithin using geography cast for meter-based distance."""
    return func.ST_DWithin(
        cast(geom_col, Geography),
        cast(point, Geography),
        radius_meters,
    )


def _build_infra_query(  # noqa: ANN201
    property_point,  # noqa: ANN001
    radius_meters: float,
):
    """Build UNION ALL across 5 infrastructure tables (no JOIN to risk_boundaries)."""
    queries = []

    infra_tables = [
        (CellTower, "cell_tower", CellTower.geom, func.coalesce(CellTower.licensee, "Cell Tower")),
        (
            TransmissionLine,
            "transmission_line",
            TransmissionLine.geom,
            func.coalesce(TransmissionLine.owner, "Transmission Line"),
        ),
        (PowerPlant, "power_plant", PowerPlant.geom, func.coalesce(PowerPlant.name, "Power Plant")),
        (
            NatGasPipeline,
            "nat_gas_pipeline",
            NatGasPipeline.geom,
            func.coalesce(NatGasPipeline.operator, "Natural Gas Pipeline"),
        ),
        (
            PetroleumPipeline,
            "petroleum_pipeline",
            PetroleumPipeline.geom,
            func.coalesce(PetroleumPipeline.operator, "Petroleum Pipeline"),
        ),
    ]

    for model, type_label, geom_col, name_expr in infra_tables:
        is_line = model in _LINE_MODELS
        lat_expr = ST_Y(func.ST_Centroid(geom_col)) if is_line else ST_Y(geom_col)
        lon_expr = ST_X(func.ST_Centroid(geom_col)) if is_line else ST_X(geom_col)

        q = select(
            cast(model.id, String).label("infra_id"),  # type: ignore[union-attr]
            name_expr.label("name"),
            literal(type_label).label("infrastructure_type"),
            lat_expr.label("lat"),
            lon_expr.label("lon"),
            (
                func.ST_Distance(
                    cast(property_point, Geography),
                    cast(geom_col, Geography),
                )
                / METERS_PER_MILE
            ).label("distance_miles"),
        ).where(
            geom_col.isnot(None),
            _st_dwithin_geography(geom_col, property_point, radius_meters),
        )
        queries.append(q)

    return union_all(*queries).cte("all_risks")


def _build_boundaries_query(  # noqa: ANN201
    property_point,  # noqa: ANN001
    radius_meters: float,
):
    """Select risk boundary polygons within the radius, with containment check.

    Boundary polygon geometry is served via Martin vector tiles; this query
    only checks containment to determine severity labels.
    """
    return select(
        RiskBoundary.infrastructure_type,
        RiskBoundary.infrastructure_id,
        RiskBoundary.severity,
        func.ST_Contains(RiskBoundary.geom, property_point).label("contains_property"),
    ).where(
        _st_dwithin_geography(RiskBoundary.geom, property_point, radius_meters),
    )


def _severity_label(rb_severity: str | None) -> str:
    if rb_severity is None:
        return "Safe"
    return SEVERITY_MAP.get(rb_severity, "Safe")


def _detail_text(infra_type: str, rb_severity: str | None) -> str:
    label = TYPE_LABELS.get(infra_type, infra_type.replace("_", " ").title())
    if rb_severity and rb_severity in SEVERITY_PHRASES:
        return f"{label} — {SEVERITY_PHRASES[rb_severity]}"
    return f"{label} — outside risk zones"


def _cache_key(lat: float, lon: float, radius_miles: float) -> str:
    raw = f"risks:{lat:.6f}:{lon:.6f}:{radius_miles:.2f}"
    digest = hashlib.md5(raw.encode()).hexdigest()  # noqa: S324
    return f"risks:{digest}"


@router.get("/risks", response_model=RisksResponse)
async def get_risks(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    radius_miles: Annotated[float, Query(gt=0, le=10)] = 3.0,
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
    valkey: Annotated[Redis | None, Depends(get_valkey)] = None,
) -> RisksResponse:
    """Return infrastructure risk features and boundary polygons near the given location."""
    # Check cache
    c_key = _cache_key(lat, lon, radius_miles)
    if valkey is not None:
        try:
            cached = await valkey.get(c_key)
            if cached is not None:
                data = json.loads(cached)
                return RisksResponse(**data)
        except Exception:
            logger.warning("Valkey read failed for key %s", c_key, exc_info=True)

    radius_meters = radius_miles * METERS_PER_MILE
    property_point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

    # Query 1: infrastructure features (no JOIN to risk_boundaries)
    cte = _build_infra_query(property_point, radius_meters)

    rows = db.execute(
        select(
            cte.c.infra_id,
            cte.c.name,
            cte.c.infrastructure_type,
            cte.c.lat,
            cte.c.lon,
            cte.c.distance_miles,
        ).order_by(
            cte.c.distance_miles,
        )
    ).all()

    # Fast-path: if precomputed lookup says not in risk zone, skip boundary query
    risk_lookup = db.execute(
        select(PropertyGeoLookup.in_risk_zone)
        .join(RedfinListing, RedfinListing.id == PropertyGeoLookup.property_id)
        .where(
            RedfinListing.location.isnot(None),
            ST_DWithin(RedfinListing.location, property_point, 0.001),
        )
        .limit(1)
    ).scalar_one_or_none()

    severity_lookup: dict[tuple[str, str], str] = {}
    if risk_lookup is None or risk_lookup:
        # Query 2: risk boundary polygons (with containment check)
        boundary_rows = db.execute(_build_boundaries_query(property_point, radius_meters)).all()

        # Build severity lookup from boundaries that contain the property point
        for brow in boundary_rows:
            if brow.contains_property:
                key = (brow.infrastructure_type, str(brow.infrastructure_id))
                if key not in severity_lookup or brow.severity == "critical":
                    severity_lookup[key] = brow.severity

    features: list[RiskFeature] = []
    for row in rows:
        rb_severity = severity_lookup.get(
            (row.infrastructure_type, row.infra_id),
        )
        severity = _severity_label(rb_severity)
        dist = round(row.distance_miles, 2) if row.distance_miles is not None else 0.0
        features.append(
            RiskFeature(
                id=f"RB-{row.infrastructure_type[0].upper()}-{row.infra_id}",
                name=row.name or row.infrastructure_type.replace("_", " ").title(),
                infrastructure_type=row.infrastructure_type,
                severity=severity,
                distance_miles=dist,
                lat=row.lat,
                lon=row.lon,
                detail=_detail_text(row.infrastructure_type, rb_severity),
            )
        )

    # Sort: Concern first, Caution second, Safe last; then by distance
    features.sort(key=lambda f: (SEVERITY_SORT.get(f.severity, 9), f.distance_miles))

    response = RisksResponse(features=features)

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

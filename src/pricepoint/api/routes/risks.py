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
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_X, ST_Y, ST_DWithin, ST_MakePoint, ST_SetSRID
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
# Approximate degree-per-mile at mid-latitudes (~35-40°N) for fast geometry queries.
_MILES_TO_DEGREES = 1.0 / 69.0

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


def _st_dwithin_geometry(geom_col, point, radius_miles: float):  # noqa: ANN001, ANN201
    """ST_DWithin using geometry (degrees) for fast GiST-indexed spatial filter."""
    return func.ST_DWithin(geom_col, point, radius_miles * _MILES_TO_DEGREES)


def _st_distance_geography(geom_col, point):  # noqa: ANN001, ANN201
    """ST_Distance using geography cast for meter-based distance."""
    return func.ST_Distance(
        cast(geom_col, Geography()),
        cast(point, Geography()),
    )


def _build_infra_query(  # noqa: ANN201
    property_point,  # noqa: ANN001
    radius_miles: float,
):
    """Build UNION ALL across 5 infrastructure tables (no JOIN to risk_boundaries).

    Each sub-query selects up to 4 generic metadata columns (meta1..meta4) with
    type-specific values so the caller can build a per-type metadata dict.
    """
    _null = literal(None).label  # shorthand for NULL placeholders
    queries = []

    # (model, type_label, geom_col, name_expr, meta1, meta2, meta3, meta4)
    infra_defs: list[tuple] = [
        (
            CellTower,
            "cell_tower",
            CellTower.geom,
            func.coalesce(CellTower.licensee, "Cell Tower"),
            cast(CellTower.structure_type, String).label("meta1"),
            cast(CellTower.height_ft, String).label("meta2"),
            _null("meta3"),
            _null("meta4"),
        ),
        (
            TransmissionLine,
            "transmission_line",
            TransmissionLine.geom,
            func.coalesce(TransmissionLine.owner, "Transmission Line"),
            cast(TransmissionLine.line_type, String).label("meta1"),
            cast(TransmissionLine.status, String).label("meta2"),
            cast(TransmissionLine.volt_class, String).label("meta3"),
            _null("meta4"),
        ),
        (
            PowerPlant,
            "power_plant",
            PowerPlant.geom,
            func.coalesce(PowerPlant.name, "Power Plant"),
            cast(PowerPlant.primary_source, String).label("meta1"),
            cast(PowerPlant.utility_name, String).label("meta2"),
            _null("meta3"),
            _null("meta4"),
        ),
        (
            NatGasPipeline,
            "nat_gas_pipeline",
            NatGasPipeline.geom,
            func.coalesce(NatGasPipeline.operator, "Natural Gas Pipeline"),
            cast(NatGasPipeline.pipe_type, String).label("meta1"),
            cast(NatGasPipeline.status, String).label("meta2"),
            _null("meta3"),
            _null("meta4"),
        ),
        (
            PetroleumPipeline,
            "petroleum_pipeline",
            PetroleumPipeline.geom,
            func.coalesce(PetroleumPipeline.operator, "Petroleum Pipeline"),
            _null("meta1"),
            _null("meta2"),
            _null("meta3"),
            _null("meta4"),
        ),
    ]

    for model, type_label, geom_col, name_expr, m1, m2, m3, m4 in infra_defs:
        is_line = model in _LINE_MODELS
        lat_expr = ST_Y(func.ST_PointOnSurface(geom_col)) if is_line else ST_Y(geom_col)
        lon_expr = ST_X(func.ST_PointOnSurface(geom_col)) if is_line else ST_X(geom_col)

        q = select(
            cast(model.id, String).label("infra_id"),  # type: ignore[union-attr]
            name_expr.label("name"),
            literal(type_label).label("infrastructure_type"),
            lat_expr.label("lat"),
            lon_expr.label("lon"),
            (_st_distance_geography(geom_col, property_point) / METERS_PER_MILE).label(
                "distance_miles"
            ),
            m1,
            m2,
            m3,
            m4,
        ).where(
            geom_col.isnot(None),
            _st_dwithin_geometry(geom_col, property_point, radius_miles),
        )
        queries.append(q)

    return union_all(*queries).cte("all_risks")


def _build_boundaries_query(  # noqa: ANN201
    property_point,  # noqa: ANN001
    radius_miles: float,
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
        _st_dwithin_geometry(RiskBoundary.geom, property_point, radius_miles),
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


def _build_metadata(
    infra_type: str,
    meta1: str | None,
    meta2: str | None,
    meta3: str | None,
    meta4: str | None,  # noqa: ARG001
) -> dict[str, str | float | None]:
    """Build a type-specific metadata dict from the generic meta1..meta4 columns."""
    if infra_type == "cell_tower":
        return {"structure_type": meta1, "height_ft": meta2}
    if infra_type == "power_plant":
        return {"fuel_source": meta1, "utility_name": meta2}
    if infra_type == "nat_gas_pipeline":
        return {"pipe_type": meta1, "status": meta2}
    if infra_type == "petroleum_pipeline":
        return {"operator": meta1}
    if infra_type == "transmission_line":
        return {"line_type": meta1, "status": meta2, "voltage_class": meta3}
    return {}


_INFRA_MODELS: dict[str, tuple] = {
    "cell_tower": (
        CellTower,
        CellTower.geom,
        func.coalesce(CellTower.licensee, "Cell Tower"),
        [CellTower.structure_type, CellTower.height_ft, None, None],
    ),
    "transmission_line": (
        TransmissionLine,
        TransmissionLine.geom,
        func.coalesce(TransmissionLine.owner, "Transmission Line"),
        [TransmissionLine.line_type, TransmissionLine.status, TransmissionLine.volt_class, None],
    ),
    "power_plant": (
        PowerPlant,
        PowerPlant.geom,
        func.coalesce(PowerPlant.name, "Power Plant"),
        [PowerPlant.primary_source, PowerPlant.utility_name, None, None],
    ),
    "nat_gas_pipeline": (
        NatGasPipeline,
        NatGasPipeline.geom,
        func.coalesce(NatGasPipeline.operator, "Natural Gas Pipeline"),
        [NatGasPipeline.pipe_type, NatGasPipeline.status, None, None],
    ),
    "petroleum_pipeline": (
        PetroleumPipeline,
        PetroleumPipeline.geom,
        func.coalesce(PetroleumPipeline.operator, "Petroleum Pipeline"),
        [None, None, None, None],
    ),
}


def _fetch_remote_infra(
    db: Session,
    missing: dict[tuple[str, str], str],
    property_point,  # noqa: ANN001
) -> list[RiskFeature]:
    """Fetch infrastructure items whose boundaries contain the property but are
    outside the normal search radius (e.g. large nuclear plant caution zones)."""
    features: list[RiskFeature] = []
    # Group by infra type
    by_type: dict[str, list[tuple[str, str]]] = {}
    for (itype, iid), severity in missing.items():
        by_type.setdefault(itype, []).append((iid, severity))

    for itype, items in by_type.items():
        cfg = _INFRA_MODELS.get(itype)
        if cfg is None:
            continue
        model, geom_col, name_expr, meta_cols = cfg
        is_line = model in _LINE_MODELS
        lat_expr = ST_Y(func.ST_PointOnSurface(geom_col)) if is_line else ST_Y(geom_col)
        lon_expr = ST_X(func.ST_PointOnSurface(geom_col)) if is_line else ST_X(geom_col)

        ids = [int(iid) for iid, _ in items]
        sev_map = {iid: sev for iid, sev in items}

        meta_selects = []
        for i, c in enumerate(meta_cols):
            lbl = f"meta{i + 1}"
            col = cast(c, String).label(lbl) if c is not None else literal(None).label(lbl)
            meta_selects.append(col)

        rows = db.execute(
            select(
                cast(model.id, String).label("infra_id"),  # type: ignore[union-attr]
                name_expr.label("name"),
                lat_expr.label("lat"),
                lon_expr.label("lon"),
                (_st_distance_geography(geom_col, property_point) / METERS_PER_MILE).label(
                    "distance_miles"
                ),
                *meta_selects,
            ).where(model.id.in_(ids))  # type: ignore[union-attr]
        ).all()

        for row in rows:
            rb_severity = sev_map.get(row.infra_id)
            severity = _severity_label(rb_severity)
            dist = round(row.distance_miles, 2) if row.distance_miles is not None else 0.0
            features.append(
                RiskFeature(
                    id=f"RB-{itype[0].upper()}-{row.infra_id}",
                    name=row.name or itype.replace("_", " ").title(),
                    infrastructure_type=itype,
                    severity=severity,
                    distance_miles=dist,
                    lat=row.lat,
                    lon=row.lon,
                    detail=_detail_text(itype, rb_severity),
                    metadata=_build_metadata(itype, row.meta1, row.meta2, row.meta3, row.meta4),
                )
            )

    return features


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

    property_point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

    # Query 1: infrastructure features (no JOIN to risk_boundaries)
    cte = _build_infra_query(property_point, radius_miles)

    rows = db.execute(
        select(
            cte.c.infra_id,
            cte.c.name,
            cte.c.infrastructure_type,
            cte.c.lat,
            cte.c.lon,
            cte.c.distance_miles,
            cte.c.meta1,
            cte.c.meta2,
            cte.c.meta3,
            cte.c.meta4,
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
        boundary_rows = db.execute(_build_boundaries_query(property_point, radius_miles)).all()

        # Build severity lookup from boundaries that contain the property point.
        # risk_boundaries stores plural types (e.g. "cell_towers") but the infra
        # CTE uses singular (e.g. "cell_tower"), so strip the trailing "s".
        for brow in boundary_rows:
            if brow.contains_property:
                infra_type_singular = brow.infrastructure_type.rstrip("s")
                key = (infra_type_singular, str(brow.infrastructure_id))
                if key not in severity_lookup or brow.severity == "critical":
                    severity_lookup[key] = brow.severity

    # Build set of infrastructure IDs already found in the radius query
    found_infra_keys = {(row.infrastructure_type, row.infra_id) for row in rows}

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
                metadata=_build_metadata(
                    row.infrastructure_type, row.meta1, row.meta2, row.meta3, row.meta4
                ),
            )
        )

    # Add features for infrastructure whose boundary contains the property but
    # whose source is outside the search radius (e.g. large nuclear plant zones).
    missing = {k: v for k, v in severity_lookup.items() if k not in found_infra_keys}
    if missing:
        features.extend(_fetch_remote_infra(db, missing, property_point))

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

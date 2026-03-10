"""Reusable query helpers for nuisance sources and risk features.

Extracted from the nuisances and risks route handlers so that the
comparables endpoint can obtain per-property nuisance / risk data
without duplicating query logic.
"""

from __future__ import annotations

import logging

from geoalchemy2 import Geography
from geoalchemy2.functions import ST_DWithin, ST_MakePoint, ST_SetSRID
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from pricepoint.api.schemas.comparables import CompNuisance, CompRisk
from pricepoint.db.models import (
    Airport,
    CellTower,
    NatGasPipeline,
    PetroleumPipeline,
    PowerPlant,
    PropertyGeoLookup,
    Railroad,
    RedfinListing,
    RiskBoundary,
    Road,
    TransmissionLine,
    TransportationNoise,
)

logger = logging.getLogger(__name__)

METERS_PER_MILE = 1609.344
_INFRA_SEARCH_RADIUS_MILES = 30.0
_MILES_TO_DEGREES = 1.0 / 69.0
_LINE_MODELS = {TransmissionLine, NatGasPipeline, PetroleumPipeline}

TYPE_LABELS: dict[str, str] = {
    "cell_tower": "Cell Tower",
    "transmission_line": "Transmission Line",
    "power_plant": "Power Plant",
    "nat_gas_pipeline": "Natural Gas Pipeline",
    "petroleum_pipeline": "Petroleum Pipeline",
}

SEVERITY_MAP: dict[str, str] = {
    "critical": "Concern",
    "caution": "Caution",
}

SEVERITY_PHRASES: dict[str, str] = {
    "critical": "within critical risk zone",
    "caution": "within caution risk zone",
}


def query_nuisance_sources(db: Session, lat: float, lon: float) -> list[CompNuisance]:
    """Return nuisance sources near a location (lightweight version for comps)."""
    property_point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
    geog_type = Geography(srid=4326)

    # Fast-path check
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
        return []

    # Find noise polygons containing the property
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

    results: list[CompNuisance] = []
    for row in noise_rows:
        source_layer: str = row.source_layer
        max_db: int = row.max_db
        noise_band: str = row.noise_band
        severity = "Concern" if max_db >= 55 else "Caution"

        infra = _find_nearest_infra(db, property_point, geog_type, source_layer)
        if infra:
            results.append(
                CompNuisance(
                    name=infra["name"],
                    source_type=source_layer,
                    severity=severity,
                    distance_miles=infra["distance_miles"],
                    detail=f"Noise zone ({noise_band})",
                )
            )

    return results


def _find_nearest_infra(
    db: Session,
    point: object,
    geog_type: Geography,
    source_layer: str,
) -> dict | None:
    """Find the nearest infrastructure feature for a given noise source layer."""
    if source_layer == "aviation":
        dist_col = func.ST_Distance(cast(Airport.geom, geog_type), cast(point, geog_type)).label(
            "dist_m"
        )
        row = db.execute(
            select(Airport.name, dist_col)
            .where(
                Airport.geom.isnot(None),
                ST_DWithin(Airport.geom, point, _INFRA_SEARCH_RADIUS_MILES * _MILES_TO_DEGREES),
            )
            .order_by(dist_col)
            .limit(1)
        ).first()
        if row:
            dist = round(row.dist_m / METERS_PER_MILE, 1)
            return {"name": row.name or "Airport", "distance_miles": dist}
    elif source_layer == "road":
        dist_col = func.ST_Distance(cast(Road.geom, geog_type), cast(point, geog_type)).label(
            "dist_m"
        )
        row = db.execute(
            select(Road.fullname, dist_col)
            .where(
                Road.geom.isnot(None),
                ST_DWithin(Road.geom, point, _INFRA_SEARCH_RADIUS_MILES * _MILES_TO_DEGREES),
            )
            .order_by(dist_col)
            .limit(1)
        ).first()
        if row:
            return {
                "name": row.fullname or "Road",
                "distance_miles": round(row.dist_m / METERS_PER_MILE, 1),
            }
    elif source_layer == "rail":
        dist_col = func.ST_Distance(cast(Railroad.geom, geog_type), cast(point, geog_type)).label(
            "dist_m"
        )
        row = db.execute(
            select(Railroad.rrowner1, dist_col)
            .where(
                Railroad.geom.isnot(None),
                ST_DWithin(Railroad.geom, point, _INFRA_SEARCH_RADIUS_MILES * _MILES_TO_DEGREES),
            )
            .order_by(dist_col)
            .limit(1)
        ).first()
        if row:
            return {
                "name": row.rrowner1 or "Railroad",
                "distance_miles": round(row.dist_m / METERS_PER_MILE, 1),
            }
    return None


def query_risk_features(
    db: Session, lat: float, lon: float, radius_miles: float = 3.0
) -> list[CompRisk]:
    """Return infrastructure risk features near a location (lightweight for comps)."""
    property_point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

    # Fast-path check
    risk_lookup = db.execute(
        select(PropertyGeoLookup.in_risk_zone)
        .join(RedfinListing, RedfinListing.id == PropertyGeoLookup.property_id)
        .where(
            RedfinListing.location.isnot(None),
            ST_DWithin(RedfinListing.location, property_point, 0.001),
        )
        .limit(1)
    ).scalar_one_or_none()

    if risk_lookup is not None and not risk_lookup:
        return []

    # Check which boundaries contain the property
    boundary_rows = db.execute(
        select(
            RiskBoundary.infrastructure_type,
            RiskBoundary.infrastructure_id,
            RiskBoundary.severity,
            func.ST_Contains(RiskBoundary.geom, property_point).label("contains_property"),
        ).where(
            func.ST_DWithin(RiskBoundary.geom, property_point, radius_miles * _MILES_TO_DEGREES),
        )
    ).all()

    severity_lookup: dict[tuple[str, int], str] = {}
    for brow in boundary_rows:
        if brow.contains_property:
            key = (brow.infrastructure_type, brow.infrastructure_id)
            if key not in severity_lookup or brow.severity == "critical":
                severity_lookup[key] = brow.severity

    if not severity_lookup:
        return []

    # Query the actual infrastructure for names and distances
    results: list[CompRisk] = []
    infra_defs: list[tuple] = [
        (CellTower, "cell_towers", CellTower.geom, CellTower.licensee),
        (TransmissionLine, "transmission_lines", TransmissionLine.geom, TransmissionLine.owner),
        (PowerPlant, "power_plants", PowerPlant.geom, PowerPlant.name),
        (NatGasPipeline, "nat_gas_pipelines", NatGasPipeline.geom, NatGasPipeline.operator),
        (
            PetroleumPipeline,
            "petroleum_pipelines",
            PetroleumPipeline.geom,
            PetroleumPipeline.operator,
        ),
    ]

    for model, type_key, geom_col, name_col in infra_defs:
        matching_ids = [iid for (itype, iid), _ in severity_lookup.items() if itype == type_key]
        if not matching_ids:
            continue

        dist_col = func.ST_Distance(
            cast(geom_col, Geography()),
            cast(property_point, Geography()),
        ).label("dist_m")

        rows = db.execute(
            select(model.id, name_col.label("name"), dist_col).where(model.id.in_(matching_ids))  # type: ignore[union-attr]  # type: ignore[union-attr]
        ).all()

        singular_type = type_key.rstrip("s")
        label = TYPE_LABELS.get(singular_type, singular_type.replace("_", " ").title())

        for row in rows:
            rb_sev = severity_lookup.get((type_key, row.id))
            severity = SEVERITY_MAP.get(rb_sev, "Safe") if rb_sev else "Safe"
            phrase = (
                SEVERITY_PHRASES.get(rb_sev, "outside risk zones")
                if rb_sev
                else "outside risk zones"
            )
            dist = round(row.dist_m / METERS_PER_MILE, 2) if row.dist_m else 0.0
            results.append(
                CompRisk(
                    name=row.name or label,
                    infrastructure_type=singular_type,
                    severity=severity,
                    distance_miles=dist,
                    detail=f"{label} — {phrase}",
                )
            )

    return results

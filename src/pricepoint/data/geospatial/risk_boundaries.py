"""Build gold-layer risk boundary polygons around infrastructure.

Generates pre-computed buffer polygons (critical and caution severity)
around cell towers, transmission lines, power plants, and pipelines.
Enables fast spatial queries to determine if a property falls within
a risk zone without computing buffers at query time.

Sources: cell_towers, transmission_lines, power_plants,
         nat_gas_pipelines, petroleum_pipelines
Target:  risk_boundaries (gold)
"""

from __future__ import annotations

import logging
from typing import Any

from geoalchemy2 import Geometry
from geoalchemy2.types import Geography
from sqlalchemy import cast, delete, func, insert, literal, select
from sqlalchemy.orm import Session

from pricepoint.config.settings import get_settings
from pricepoint.db.models import (
    CellTower,
    NatGasPipeline,
    PetroleumPipeline,
    PowerPlant,
    RiskBoundary,
    TransmissionLine,
)

logger = logging.getLogger(__name__)

_FT_TO_M = 0.3048


def _get_distances(infra_type: str, primary_source: str | None = None) -> dict[str, float]:
    """Look up critical/caution distances in meters for an infrastructure type.

    For power plants, uses ``primary_source`` (case-insensitive) to find
    source-specific distances, falling back to ``_default``.
    """
    settings = get_settings()
    distances_ft = settings.risk_boundary_distances_ft

    if infra_type == "power_plants" and primary_source is not None:
        plant_distances = distances_ft["power_plants"]
        key = primary_source.lower().strip()
        entry = plant_distances.get(key, plant_distances["_default"])
    elif infra_type == "power_plants":
        entry = distances_ft["power_plants"]["_default"]
    else:
        entry = distances_ft[infra_type]

    return {
        "critical": entry["critical"] * _FT_TO_M,
        "caution": entry["caution"] * _FT_TO_M,
    }


def _buffer_expr(geom_col: Any, distance_m: float) -> Any:
    """Create a ST_Buffer expression casting geometry to geography and back."""
    return cast(
        func.ST_Buffer(cast(geom_col, Geography), distance_m),
        Geometry,
    )


def _build_simple_buffers(
    session: Session,
    model: Any,
    infra_type: str,
) -> int:
    """Build risk boundaries for a simple (non-power-plant) infrastructure type.

    Inserts critical buffer and caution annular ring (caution minus critical)
    for every record in the source table.
    """
    distances = _get_distances(infra_type)
    critical_m = distances["critical"]
    caution_m = distances["caution"]

    # Critical buffer
    critical_stmt = insert(RiskBoundary).from_select(
        ["infrastructure_type", "infrastructure_id", "severity", "geom"],
        select(
            literal(infra_type),
            model.id,
            literal("critical"),
            _buffer_expr(model.geom, critical_m),
        ).where(model.geom.isnot(None)),
    )
    result_critical = session.execute(critical_stmt)

    # Caution ring (annular: caution buffer minus critical buffer)
    caution_stmt = insert(RiskBoundary).from_select(
        ["infrastructure_type", "infrastructure_id", "severity", "geom"],
        select(
            literal(infra_type),
            model.id,
            literal("caution"),
            cast(
                func.ST_Difference(
                    _buffer_expr(model.geom, caution_m),
                    _buffer_expr(model.geom, critical_m),
                ),
                Geometry,
            ),
        ).where(model.geom.isnot(None)),
    )
    result_caution = session.execute(caution_stmt)

    count = (result_critical.rowcount or 0) + (result_caution.rowcount or 0)  # type: ignore[attr-defined]
    logger.info("Built %d risk boundaries for %s", count, infra_type)
    return count


def _build_power_plant_buffers(session: Session) -> int:
    """Build risk boundaries for power plants, grouped by primary_source."""
    # Get distinct primary sources
    sources = (
        session.execute(
            select(PowerPlant.primary_source).where(PowerPlant.geom.isnot(None)).distinct()
        )
        .scalars()
        .all()
    )

    total = 0
    for source in sources:
        distances = _get_distances("power_plants", source)  # type: ignore[arg-type]
        critical_m = distances["critical"]
        caution_m = distances["caution"]

        if source is not None:
            filter_cond = PowerPlant.primary_source == source
        else:
            filter_cond = PowerPlant.primary_source.is_(None)

        # Critical buffer
        critical_stmt = insert(RiskBoundary).from_select(
            ["infrastructure_type", "infrastructure_id", "severity", "geom"],
            select(
                literal("power_plants"),
                PowerPlant.id,
                literal("critical"),
                _buffer_expr(PowerPlant.geom, critical_m),
            ).where(PowerPlant.geom.isnot(None), filter_cond),
        )
        result_critical = session.execute(critical_stmt)

        # Caution ring
        caution_stmt = insert(RiskBoundary).from_select(
            ["infrastructure_type", "infrastructure_id", "severity", "geom"],
            select(
                literal("power_plants"),
                PowerPlant.id,
                literal("caution"),
                cast(
                    func.ST_Difference(
                        _buffer_expr(PowerPlant.geom, caution_m),
                        _buffer_expr(PowerPlant.geom, critical_m),
                    ),
                    Geometry,
                ),
            ).where(PowerPlant.geom.isnot(None), filter_cond),
        )
        result_caution = session.execute(caution_stmt)

        source_count = (result_critical.rowcount or 0) + (result_caution.rowcount or 0)  # type: ignore[attr-defined]
        total += source_count
        logger.info(
            "Built %d risk boundaries for power_plants source=%s",
            source_count,
            source,
        )

    return total


def build_risk_boundaries(session: Session) -> int:
    """Build the gold ``risk_boundaries`` table.

    Deletes existing data and rebuilds from all infrastructure sources.
    Caller is responsible for committing the transaction.

    Returns total record count inserted.
    """
    # Delete existing (single transaction — no FKs reference this table)
    deleted = session.execute(delete(RiskBoundary))
    logger.info(
        "Deleted %d existing risk boundaries",
        deleted.rowcount or 0,  # type: ignore[attr-defined]
    )

    total = 0

    # Simple infrastructure types (single distance per type)
    simple_types: list[tuple[Any, str]] = [
        (CellTower, "cell_towers"),
        (TransmissionLine, "transmission_lines"),
        (NatGasPipeline, "nat_gas_pipelines"),
        (PetroleumPipeline, "petroleum_pipelines"),
    ]

    for model, infra_type in simple_types:
        total += _build_simple_buffers(session, model, infra_type)

    # Power plants (distance varies by primary_source)
    total += _build_power_plant_buffers(session)

    logger.info("Built %d total risk boundaries", total)
    return total


def verify_risk_boundaries(session: Session) -> None:
    """Verify that risk_boundaries has been populated.

    Raises RuntimeError if the table is empty.
    """
    count = session.scalar(select(func.count()).select_from(RiskBoundary)) or 0
    if not count:
        raise RuntimeError("No records in risk_boundaries table after build")
    logger.info("Verified risk_boundaries: %d records", count)

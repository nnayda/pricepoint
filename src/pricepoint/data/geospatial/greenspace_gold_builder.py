"""Build gold-layer greenspaces table from Wake open space bronze data.

Filters to relevant open space types (Gameland, Open Space, Greenway, Park)
and normalises the type values to title case.
"""

from __future__ import annotations

import logging

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from pricepoint.db.models import Greenspace, StagingWakeOpenSpace

logger = logging.getLogger(__name__)

ALLOWED_TYPES = {"GAMELAND", "OPEN SPACE", "GREENWAY", "PARK"}


def build_greenspaces_gold(session: Session) -> dict[str, int]:
    """Truncate-and-rebuild the ``greenspaces`` gold table.

    Returns a stats dict with count of inserted rows.
    """
    session.execute(delete(Greenspace))
    session.flush()

    rows = (
        session.execute(
            select(StagingWakeOpenSpace).where(
                StagingWakeOpenSpace.type.in_(ALLOWED_TYPES)
            )
        )
        .scalars()
        .all()
    )

    for row in rows:
        session.add(
            Greenspace(
                source="staging_wake_open_space",
                source_id=row.id,
                name=row.name,
                acres=row.acres,
                type=row.type.title(),
                geom=row.geom,
            )
        )
    session.flush()

    logger.info("Greenspace gold build complete: inserted %d rows", len(rows))
    return {"inserted": len(rows)}

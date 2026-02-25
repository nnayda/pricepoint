"""Build gold-layer greenspaces table from Wake open space bronze data.

Filters to relevant open space types (Gameland, Open Space, Greenway, Park)
and normalises the type values to title case.  Uses upsert (ON CONFLICT)
to preserve stable ``id`` values across rebuilds.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from pricepoint.db.models import Greenspace, StagingWakeOpenSpace

logger = logging.getLogger(__name__)

ALLOWED_TYPES = {"GAMELAND", "OPEN SPACE", "GREENWAY", "PARK"}


def build_greenspaces_gold(
    session: Session,
    *,
    run_started: datetime | None = None,
) -> dict[str, int]:
    """Upsert the ``greenspaces`` gold table from bronze open-space data.

    Rows are matched on ``(source, source_id)``.  After upserting all current
    source rows, any gold row whose ``built_at`` is older than *run_started*
    is deleted (stale-row cleanup).

    Returns a stats dict with counts of upserted and deleted rows.
    """
    if run_started is None:
        run_started = datetime.now(UTC)

    rows = (
        session.execute(
            select(StagingWakeOpenSpace).where(
                StagingWakeOpenSpace.type.in_(ALLOWED_TYPES)
            )
        )
        .scalars()
        .all()
    )

    upserted = 0
    for row in rows:
        values = {
            "source": "staging_wake_open_space",
            "source_id": row.id,
            "name": row.name,
            "acres": row.acres,
            "type": row.type.title(),
            "geom": row.geom,
            "built_at": run_started,
        }
        stmt = pg_insert(Greenspace).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["source", "source_id"],
            set_={
                "name": stmt.excluded.name,
                "acres": stmt.excluded.acres,
                "type": stmt.excluded.type,
                "geom": stmt.excluded.geom,
                "built_at": stmt.excluded.built_at,
            },
        )
        session.execute(stmt)
        upserted += 1
    session.flush()

    # Remove stale rows no longer present in any source
    result = session.execute(
        delete(Greenspace).where(Greenspace.built_at < run_started)
    )
    stale_deleted = result.rowcount  # type: ignore[attr-defined]
    session.flush()

    logger.info(
        "Greenspace gold build complete: upserted %d rows, deleted %d stale",
        upserted,
        stale_deleted,
    )
    return {"upserted": upserted, "stale_deleted": stale_deleted}

"""Build gold-layer greenways table from Wake, Cary, and Raleigh bronze data.

Merges three overlapping greenway datasets into a single canonical table.
Wake County geometry is used as the baseline; town-level attributes (Cary,
Raleigh) overwrite county values when non-NULL.  Matching is spatial —
``ST_DWithin(50m)`` with greatest-overlap tiebreaker.

Uses upsert (ON CONFLICT) to preserve stable ``id`` values across rebuilds.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from geoalchemy2.types import Geography
from sqlalchemy import cast, delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from pricepoint.db.models import (
    CaryGreenway,
    Greenway,
    RaleighGreenway,
    WakeGreenway,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Surface-type normalisation
# ---------------------------------------------------------------------------

_WAKE_SURFACE_MAP: dict[str | None, str] = {
    "CONCRETE": "Paved",
    "ASPHALT": "Paved",
    "IMPORTED LOOSE MATERIAL": "Crushed Stone",
    "NATIVE MATERIAL": "Natural",
    "CHUNK WOOD": "Natural",
}

_CARY_SURFACE_MAP: dict[str | None, str] = {
    "Asphalt": "Paved",
    "Concrete": "Paved",
    "Limestone": "Paved",
    "Aggregate": "Crushed Stone",
    "Gravel": "Crushed Stone",
    "Decking": "Decking",
}

_RALEIGH_SURFACE_MAP: dict[str | None, str] = {
    "Asphalt": "Paved",
    "Concrete": "Paved",
    "Brick": "Paved",
    "Metal": "Paved",
    "NCDOT Bridge": "Paved",
    "Gravel": "Crushed Stone",
    "Natural": "Natural",
    "Steel - Wood Decking": "Decking",
    "Wood Decking": "Decking",
    "Trex Decking": "Decking",
}


def normalize_wake_surface(raw: str | None) -> str:
    """Normalise a Wake County ``trail_surface`` value."""
    if raw is None:
        return "Unknown"
    return _WAKE_SURFACE_MAP.get(raw.strip(), "Unknown")


def normalize_cary_surface(raw: str | None) -> str:
    """Normalise a Cary ``surface_type`` value."""
    if raw is None:
        return "Unknown"
    return _CARY_SURFACE_MAP.get(raw.strip(), "Unknown")


def normalize_raleigh_surface(raw: str | None) -> str:
    """Normalise a Raleigh ``material`` value."""
    if raw is None:
        return "Unknown"
    return _RALEIGH_SURFACE_MAP.get(raw.strip(), "Unknown")


# ---------------------------------------------------------------------------
# Status normalisation
# ---------------------------------------------------------------------------


def normalize_wake_status(raw: str | None) -> str:
    """Normalise a Wake County ``trail_status`` value."""
    if raw is not None and raw.strip().upper() == "EXISTING":
        return "Existing"
    return "Proposed"


def normalize_cary_status(raw: str | None) -> str:
    """Pass through Cary ``status`` as-is (already clean)."""
    return raw or "Unknown"


def normalize_raleigh_status(status: str | None, gw_status: str | None) -> str:
    """Normalise Raleigh ``status`` with ``gw_status`` fallback."""
    raw = status or gw_status
    if raw is None:
        return "Unknown"
    cleaned = raw.strip()
    if cleaned in ("Existing", "Maintenance"):
        return "Existing"
    if cleaned == "Under Construction":
        return "Proposed"
    return cleaned


# ---------------------------------------------------------------------------
# Name extraction
# ---------------------------------------------------------------------------


def extract_wake_name(row: Any) -> str | None:
    """Pick the best available name from a Wake greenway row."""
    return row.trail_name or row.corridor_name or row.subsegment_name  # type: ignore[return-value]


def extract_cary_name(row: Any) -> str | None:
    """Pick the best available name from a Cary greenway row."""
    return row.name or row.segment or row.loop_name or row.loop_trail  # type: ignore[return-value]


def extract_raleigh_name(row: Any) -> str | None:
    """Pick the best available name from a Raleigh greenway row."""
    return row.trail_name  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Row → gold field extraction
# ---------------------------------------------------------------------------


def extract_wake_fields(row: Any) -> dict[str, Any]:
    """Extract gold-table fields from a Wake greenway row."""
    return {
        "source": "staging_wake_greenways",
        "source_id": row.id,
        "name": extract_wake_name(row),
        "surface_type": normalize_wake_surface(row.trail_surface),
        "status": normalize_wake_status(row.trail_status),
        "length": row.length,
        "width": row.width,
        "geom": row.geom,
    }


def extract_cary_fields(row: Any) -> dict[str, Any]:
    """Extract gold-table fields from a Cary greenway row."""
    return {
        "source": "staging_cary_greenways",
        "source_id": row.id,
        "name": extract_cary_name(row),
        "surface_type": normalize_cary_surface(row.surface_type),
        "status": normalize_cary_status(row.status),
        "length": row.length,
        "width": row.width,
        "geom": row.geom,
    }


def extract_raleigh_fields(row: Any) -> dict[str, Any]:
    """Extract gold-table fields from a Raleigh greenway row."""
    return {
        "source": "staging_raleigh_greenways",
        "source_id": row.id,
        "name": extract_raleigh_name(row),
        "surface_type": normalize_raleigh_surface(row.material),
        "status": normalize_raleigh_status(row.status, row.gw_status),
        "length": row.map_miles,
        "width": row.width_ft,
        "geom": row.geom,
    }


# ---------------------------------------------------------------------------
# Augmentation (town overwrites gold)
# ---------------------------------------------------------------------------

_AUGMENT_FIELDS = ("name", "surface_type", "status", "length", "width")


def augment_gold_record(
    gold: Greenway,
    town_fields: dict[str, Any],
    *,
    built_at: datetime | None = None,
) -> None:
    """Overwrite gold record attributes with non-NULL town values."""
    for field in _AUGMENT_FIELDS:
        town_val = town_fields.get(field)
        if town_val is not None:
            setattr(gold, field, town_val)
    if built_at is not None:
        gold.built_at = built_at  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Spatial matching
# ---------------------------------------------------------------------------

_MATCH_BUFFER_METERS = 50


def _find_best_match(
    session: Session,
    town_geom: Any,
    matched_gold_ids: set[int],
) -> Greenway | None:
    """Find the best spatially-overlapping gold record for a town geometry.

    Uses ``ST_DWithin`` (50 m geography buffer) to find candidates, then
    ranks by ``ST_Length(ST_Intersection(...))`` to pick the greatest-overlap
    match.  Already-matched gold IDs are excluded to enforce one-to-one.
    """
    gold_geom = Greenway.geom
    gold_geog = cast(gold_geom, Geography)
    # WKBElement cannot be cast directly to Geography — GeoAlchemy2 wraps it
    # with ST_GeogFromText which expects WKT, not WKB.  Convert via EWKT.
    town_geog = func.ST_GeogFromText(func.ST_AsEWKT(town_geom))

    candidates_q = select(Greenway).where(
        func.ST_DWithin(gold_geog, town_geog, _MATCH_BUFFER_METERS)
    )
    if matched_gold_ids:
        candidates_q = candidates_q.where(Greenway.id.notin_(matched_gold_ids))

    candidates_q = candidates_q.order_by(
        func.ST_Length(func.ST_Intersection(gold_geom, town_geom)).desc()
    ).limit(1)

    return session.execute(candidates_q).scalar_one_or_none()


# ---------------------------------------------------------------------------
# Upsert helper
# ---------------------------------------------------------------------------


def _upsert_greenway(session: Session, fields: dict[str, Any]) -> None:
    """Insert-or-update a single greenway row keyed on (source, source_id)."""
    stmt = pg_insert(Greenway).values(**fields)
    stmt = stmt.on_conflict_do_update(
        index_elements=["source", "source_id"],
        set_={
            "name": stmt.excluded.name,
            "surface_type": stmt.excluded.surface_type,
            "status": stmt.excluded.status,
            "length": stmt.excluded.length,
            "width": stmt.excluded.width,
            "geom": stmt.excluded.geom,
            "built_at": stmt.excluded.built_at,
        },
    )
    session.execute(stmt)


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------


def build_greenways_gold(
    session: Session,
    *,
    run_started: datetime | None = None,
) -> dict[str, int]:
    """Upsert the ``greenways`` gold table from bronze sources.

    Uses ON CONFLICT upsert for Wake baseline and unmatched town rows,
    ORM updates for spatially-matched augmentations, and stale-row cleanup
    to remove rows no longer present in any source.

    Returns a stats dict with counts of upserted, matched, new, and stale records.
    """
    if run_started is None:
        run_started = datetime.now(UTC)

    # 1. Upsert all Wake greenways as baseline
    wake_rows = session.execute(select(WakeGreenway)).scalars().all()
    for row in wake_rows:
        fields = extract_wake_fields(row)
        fields["built_at"] = run_started
        _upsert_greenway(session, fields)
    session.flush()

    stats: dict[str, int] = {
        "wake_upserted": len(wake_rows),
        "cary_matched": 0,
        "cary_new": 0,
        "raleigh_matched": 0,
        "raleigh_new": 0,
        "stale_deleted": 0,
    }

    # 2. Merge Cary greenways
    matched_gold_ids: set[int] = set()
    cary_rows = session.execute(select(CaryGreenway)).scalars().all()
    for cary_row in cary_rows:
        fields = extract_cary_fields(cary_row)
        match = _find_best_match(session, cary_row.geom, matched_gold_ids)
        if match is not None:
            matched_gold_ids.add(int(match.id))  # type: ignore[arg-type]
            augment_gold_record(match, fields, built_at=run_started)
            stats["cary_matched"] += 1
        else:
            fields["built_at"] = run_started
            _upsert_greenway(session, fields)
            stats["cary_new"] += 1
    session.flush()

    # 3. Merge Raleigh greenways
    raleigh_rows = session.execute(select(RaleighGreenway)).scalars().all()
    for ral_row in raleigh_rows:
        fields = extract_raleigh_fields(ral_row)
        match = _find_best_match(session, ral_row.geom, matched_gold_ids)
        if match is not None:
            matched_gold_ids.add(int(match.id))  # type: ignore[arg-type]
            augment_gold_record(match, fields, built_at=run_started)
            stats["raleigh_matched"] += 1
        else:
            fields["built_at"] = run_started
            _upsert_greenway(session, fields)
            stats["raleigh_new"] += 1
    session.flush()

    # 4. Remove stale rows no longer present in any source
    result = session.execute(
        delete(Greenway).where(Greenway.built_at < run_started)
    )
    stats["stale_deleted"] = result.rowcount  # type: ignore[attr-defined]
    session.flush()

    logger.info("Greenway gold build complete: %s", stats)
    return stats

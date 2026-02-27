"""Collect trail data from USGS National Digital Trails dataset.

Downloads polyline features from the USGS National Map ArcGIS endpoint
and upserts into the trails table keyed on permanentidentifier.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from pricepoint.config.settings import get_settings
from pricepoint.data.geospatial.arcgis_client import (
    build_multilinestring_wkb,
    query_arcgis_page,
)
from pricepoint.db import SessionLocal
from pricepoint.db.models import Trail

logger = logging.getLogger(__name__)

_PAGE_SIZE = 2000
_WHERE = "trailtype <> 'Water Trail'"
_BATCH_SIZE = 2000

_UPDATABLE_COLUMNS = [
    "name",
    "trail_type",
    "length_miles",
    "maintainer",
    "national_designation",
    "hiker_pedestrian",
    "bicycle",
    "pack_saddle",
    "atv",
    "motorcycle",
    "ohv_over_50_inches",
    "snowshoe",
    "cross_country_ski",
    "dogsled",
    "snowmobile",
    "non_motorized_watercraft",
    "motorized_watercraft",
    "geom",
    "loaded_at",
]


def _parse_trail(feature: dict) -> dict | None:
    """Map an ArcGIS feature to Trail column values.

    Returns None if the feature lacks a permanentidentifier or geometry.
    """
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")

    permanent_id = attrs.get("permanentidentifier")
    if not permanent_id:
        return None

    paths = geometry.get("paths") if geometry else None
    geom = build_multilinestring_wkb(paths)
    if geom is None:
        return None

    return {
        "permanentidentifier": permanent_id,
        "name": attrs.get("name"),
        "trail_type": attrs.get("trailtype"),
        "length_miles": attrs.get("lengthmiles"),
        "maintainer": attrs.get("primarytrailmaintainer"),
        "national_designation": attrs.get("nationaltraildesignation"),
        "hiker_pedestrian": attrs.get("hikerpedestrian"),
        "bicycle": attrs.get("bicycle"),
        "pack_saddle": attrs.get("packsaddle"),
        "atv": attrs.get("atv"),
        "motorcycle": attrs.get("motorcycle"),
        "ohv_over_50_inches": attrs.get("ohvover50inches"),
        "snowshoe": attrs.get("snowshoe"),
        "cross_country_ski": attrs.get("crosscountryski"),
        "dogsled": attrs.get("dogsled"),
        "snowmobile": attrs.get("snowmobile"),
        "non_motorized_watercraft": attrs.get("nonmotorizedwatercraft"),
        "motorized_watercraft": attrs.get("motorizedwatercraft"),
        "geom": geom,
    }


def _deduplicate_batch(batch: list[dict]) -> list[dict]:
    """Remove duplicate permanentidentifier entries, keeping the longest segment."""
    seen: dict[str, int] = {}
    for i, row in enumerate(batch):
        pid = row["permanentidentifier"]
        if pid in seen:
            prev = batch[seen[pid]]
            prev_len = prev.get("length_miles") or 0
            curr_len = row.get("length_miles") or 0
            if curr_len > prev_len:
                logger.warning(
                    "Dropping shorter duplicate trail: permanentidentifier=%s name=%s length_miles=%s"
                    " (keeping length_miles=%s)",
                    pid,
                    prev.get("name"),
                    prev_len,
                    curr_len,
                )
                seen[pid] = i
            else:
                logger.warning(
                    "Dropping shorter duplicate trail: permanentidentifier=%s name=%s length_miles=%s"
                    " (keeping length_miles=%s)",
                    pid,
                    row.get("name"),
                    curr_len,
                    prev_len,
                )
        else:
            seen[pid] = i
    return [batch[i] for i in sorted(seen.values())]


def _upsert_batch(session: Any, batch: list[dict]) -> None:
    """Upsert a batch of trail records."""
    batch = _deduplicate_batch(batch)
    stmt = pg_insert(Trail).values(batch)
    stmt = stmt.on_conflict_do_update(
        index_elements=["permanentidentifier"],
        set_={col: stmt.excluded[col] for col in _UPDATABLE_COLUMNS},
    )
    session.execute(stmt)
    session.commit()


def fetch_trails() -> None:
    """Paginate USGS trails endpoint and upsert into PostGIS.

    After all pages, stale rows (loaded_at < run start) are removed.
    """
    settings = get_settings()
    run_started = datetime.now(UTC)

    session = SessionLocal()
    try:
        offset = 0
        total = 0
        batch: list[dict] = []

        while True:
            data = query_arcgis_page(
                settings.trails_base_url, offset, _PAGE_SIZE, where_clause=_WHERE
            )
            features = data.get("features", [])
            if not features:
                break

            for f in features:
                values = _parse_trail(f)
                if values is None:
                    continue
                values["loaded_at"] = run_started
                batch.append(values)

                if len(batch) >= _BATCH_SIZE:
                    _upsert_batch(session, batch)
                    total += len(batch)
                    logger.info("Upserted %d trail records so far", total)
                    batch = []

            offset += len(features)
            if len(features) < _PAGE_SIZE:
                break

        if batch:
            _upsert_batch(session, batch)
            total += len(batch)

        # Remove stale rows not seen in this run
        if total > 0:
            stale_count = session.execute(
                delete(Trail).where(Trail.loaded_at < run_started)
            ).rowcount  # type: ignore[union-attr, attr-defined]
            session.commit()
            if stale_count:
                logger.info("Removed %d stale trail records", stale_count)

        logger.info("USGS trails load complete: %d records", total)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def verify_trails() -> None:
    """Verify trail records were loaded. Raises RuntimeError if empty."""
    session = SessionLocal()
    try:
        count = session.execute(select(func.count()).select_from(Trail)).scalar() or 0
        if not count:
            raise RuntimeError("No records found in trails after USGS load")
        logger.info("Verified %d trail records", count)
    finally:
        session.close()

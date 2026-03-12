"""Collect subdivision boundaries from county ArcGIS MapServer endpoints.

Generic collector parameterized by county FIPS, base URL, and field mapping.
Replaces the Wake-specific collector with a single table keyed on
``(county_fips, source_id)``.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from geoalchemy2.shape import from_shape
from shapely.geometry import MultiPolygon, Polygon
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from pricepoint.db import SessionLocal
from pricepoint.db.models import Subdivision

logger = logging.getLogger(__name__)

_PAGE_SIZE = 2000
_MIN_RECORDS = 10


@dataclass
class FieldMap:
    """Maps ArcGIS field names to gold ``Subdivision`` columns."""

    source_id: str
    name: str
    acres: str | None = None
    lots: str | None = None
    density: str | None = None


@dataclass
class SubdivisionSource:
    """Configuration for a single county ArcGIS subdivision endpoint."""

    county_fips: str
    base_url: str
    field_map: FieldMap


SOURCES: list[SubdivisionSource] = [
    SubdivisionSource(
        county_fips="37183",
        base_url="https://maps.wake.gov/arcgis/rest/services/Planning/Subdivisions/MapServer/0",
        field_map=FieldMap(
            source_id="SNUMBER",
            name="NAME",
            acres="ACRES",
            lots="LOTS",
            density="DENSITY",
        ),
    ),
]


def _parse_arcgis_timestamp(value: int | None) -> datetime | None:
    """Convert an ArcGIS epoch-millisecond timestamp to a UTC datetime."""
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


def _build_multipolygon_wkb(rings: list[list[list[float]]] | None) -> object | None:
    """Convert ArcGIS rings to a WKB MultiPolygon.

    ArcGIS returns geometry as ``{"rings": [[[x,y], ...], ...]}``.
    Each ring is a list of coordinate pairs.  The first ring in each group is
    the exterior; subsequent rings (if any) are holes.
    """
    if not rings:
        return None
    try:
        polygons: list[Polygon] = []
        exterior: list[tuple[float, float]] | None = None
        holes: list[list[tuple[float, float]]] = []
        for ring in rings:
            coords = [(pt[0], pt[1]) for pt in ring]
            if exterior is not None:
                polygons.append(Polygon(exterior, holes))
                holes = []
            exterior = coords
        if exterior is not None:
            polygons.append(Polygon(exterior, holes))
        if not polygons:
            return None
        return from_shape(MultiPolygon(polygons), srid=4326)
    except (TypeError, ValueError) as exc:
        logger.warning("Failed to build MultiPolygon from rings: %s", exc)
        return None


def _query_page(base_url: str, offset: int, page_size: int) -> dict:
    """Query a page of features from an ArcGIS MapServer endpoint."""
    params: dict[str, str | int] = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": 4326,
        "resultOffset": offset,
        "resultRecordCount": page_size,
        "f": "json",
    }
    response = httpx.get(f"{base_url}/query", params=params, timeout=120)
    response.raise_for_status()
    return response.json()


def _extract_field(attrs: dict, field_name: str | None) -> object | None:
    """Safely extract a field value, returning None when the field is not mapped."""
    if field_name is None:
        return None
    return attrs.get(field_name)


def fetch_subdivisions(sources: list[SubdivisionSource] | None = None) -> dict[str, int]:
    """Fetch subdivision boundaries for all configured counties.

    For each source, paginates the ArcGIS endpoint, upserts records into the
    ``subdivisions`` table, and deletes stale rows that were not refreshed.

    Returns a dict mapping county FIPS to the number of records loaded.
    """
    if sources is None:
        sources = SOURCES

    stats: dict[str, int] = {}
    session = SessionLocal()
    try:
        for source in sources:
            run_started = datetime.now(UTC)
            offset = 0
            total = 0

            while True:
                data = _query_page(source.base_url, offset, _PAGE_SIZE)
                features = data.get("features", [])
                if not features:
                    break

                for feature in features:
                    attrs = feature.get("attributes", {})
                    geometry = feature.get("geometry")
                    rings = geometry.get("rings") if geometry else None

                    sid = attrs.get(source.field_map.source_id)
                    if sid is None:
                        continue

                    values = {
                        "county_fips": source.county_fips,
                        "source_id": str(sid),
                        "name": attrs.get(source.field_map.name),
                        "acres": _extract_field(attrs, source.field_map.acres),
                        "lots": _extract_field(attrs, source.field_map.lots),
                        "density": _extract_field(attrs, source.field_map.density),
                        "geom": _build_multipolygon_wkb(rings),
                        "built_at": run_started,
                    }

                    stmt = pg_insert(Subdivision).values(**values)
                    stmt = stmt.on_conflict_do_update(
                        constraint="uq_subdivisions_county_source",
                        set_={
                            "name": stmt.excluded.name,
                            "acres": stmt.excluded.acres,
                            "lots": stmt.excluded.lots,
                            "density": stmt.excluded.density,
                            "geom": stmt.excluded.geom,
                            "built_at": stmt.excluded.built_at,
                        },
                    )
                    session.execute(stmt)

                total += len(features)
                offset += len(features)
                logger.info(
                    "County %s: loaded %d records (total: %d)",
                    source.county_fips,
                    len(features),
                    total,
                )

                if len(features) < _PAGE_SIZE:
                    break

            session.commit()

            # Delete stale rows for this county that were not refreshed
            if total > 0:
                stale = delete(Subdivision).where(
                    Subdivision.county_fips == source.county_fips,
                    Subdivision.built_at < run_started,
                )
                result = session.execute(stale)
                session.commit()
                deleted = result.rowcount  # type: ignore[attr-defined]
                if deleted:
                    logger.info(
                        "County %s: deleted %d stale rows",
                        source.county_fips,
                        deleted,
                    )

            stats[source.county_fips] = total
            logger.info(
                "County %s subdivision load complete: %d records",
                source.county_fips,
                total,
            )

        return stats
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def verify_subdivisions(sources: list[SubdivisionSource] | None = None) -> None:
    """Verify that each configured county has subdivision records loaded."""
    if sources is None:
        sources = SOURCES

    session = SessionLocal()
    try:
        for source in sources:
            count = session.execute(
                select(func.count())
                .select_from(Subdivision)
                .where(Subdivision.county_fips == source.county_fips)
            ).scalar()
            if not count or count < _MIN_RECORDS:
                raise RuntimeError(
                    f"County {source.county_fips}: expected >= {_MIN_RECORDS} "
                    f"subdivision records, found {count}"
                )
            logger.info(
                "Verified %d records for county %s",
                count,
                source.county_fips,
            )
    finally:
        session.close()

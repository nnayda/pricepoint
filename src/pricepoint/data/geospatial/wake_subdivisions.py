"""Collect Wake County subdivision boundaries from ArcGIS MapServer.

Downloads subdivision polygon records from the Wake County Planning
Subdivisions MapServer and loads them into PostGIS.
"""

import logging
from datetime import UTC, datetime

import httpx
from geoalchemy2.shape import from_shape
from shapely.geometry import MultiPolygon, Polygon
from sqlalchemy import delete, func, select

from pricepoint.config.settings import get_settings
from pricepoint.db import SessionLocal
from pricepoint.db.models import WakeSubdivision

logger = logging.getLogger(__name__)

_PAGE_SIZE = 2000


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
    Each ring is a list of coordinate pairs. The first ring in each group is
    the exterior; subsequent rings (if any) are holes.
    """
    if not rings:
        return None
    try:
        polygons = []
        exterior = None
        holes: list[list[tuple[float, float]]] = []
        for ring in rings:
            coords = [(pt[0], pt[1]) for pt in ring]
            # Simple heuristic: treat each ring as an exterior (wake subdivisions
            # are generally simple polygons without holes)
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


def _query_subdivisions_page(base_url: str, offset: int, count: int) -> dict:
    """Query a page of subdivision features from the ArcGIS MapServer."""
    params: dict[str, str | int] = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": 4326,
        "resultOffset": offset,
        "resultRecordCount": count,
        "f": "json",
    }
    response = httpx.get(f"{base_url}/query", params=params, timeout=120)
    response.raise_for_status()
    return response.json()


def _map_subdivision_record(feature: dict) -> WakeSubdivision:
    """Map an ArcGIS JSON feature to a WakeSubdivision model instance."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")
    rings = geometry.get("rings") if geometry else None

    return WakeSubdivision(
        objectid=attrs.get("OBJECTID"),
        name=attrs.get("NAME"),
        snumber=attrs.get("SNUMBER"),
        access_rd=attrs.get("ACCESS_RD"),
        jurisdiction=attrs.get("JURISDICTION"),
        status=attrs.get("STATUS"),
        acres=attrs.get("ACRES"),
        lots=attrs.get("LOTS"),
        density=attrs.get("DENSITY"),
        mapclass=attrs.get("MAPCLASS"),
        iscluster=attrs.get("ISCLUSTER"),
        approvdate=_parse_arcgis_timestamp(attrs.get("APPROVDATE")),
        appldate=_parse_arcgis_timestamp(attrs.get("APPLDATE")),
        last_edited_date=_parse_arcgis_timestamp(attrs.get("last_edited_date")),
        geom=_build_multipolygon_wkb(rings),
    )


def fetch_wake_subdivisions() -> None:
    """Fetch all Wake County subdivision boundaries and load into PostGIS.

    Deletes existing records, paginates through all features, and bulk inserts.
    """
    settings = get_settings()
    base_url = settings.wake_subdivisions_base_url

    session = SessionLocal()
    try:
        session.execute(delete(WakeSubdivision))
        session.commit()

        offset = 0
        total = 0
        while True:
            data = _query_subdivisions_page(base_url, offset, _PAGE_SIZE)
            features = data.get("features", [])
            if not features:
                break

            records = [_map_subdivision_record(f) for f in features]
            session.add_all(records)
            session.commit()

            total += len(records)
            offset += len(features)
            logger.info("Loaded %d subdivision records (total: %d)", len(records), total)

            if len(features) < _PAGE_SIZE:
                break

        logger.info("Wake County subdivisions load complete: %d records", total)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def verify_wake_subdivisions() -> None:
    """Verify that subdivision records were loaded successfully."""
    session = SessionLocal()
    try:
        count = session.execute(select(func.count()).select_from(WakeSubdivision)).scalar()
        if not count:
            raise RuntimeError("No records found in wake_subdivisions after load")
        logger.info("Verified %d records in wake_subdivisions", count)
    finally:
        session.close()

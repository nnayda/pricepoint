"""Shared ArcGIS REST API client utilities.

Provides reusable helpers for paginated feature queries, geometry
conversion, and truncate-and-reload patterns used across all Wake County
ArcGIS data collectors.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, TypeVar

import httpx
from geoalchemy2.shape import from_shape
from shapely.geometry import MultiLineString, MultiPolygon, Point, Polygon
from sqlalchemy import delete, func, select
from sqlalchemy.orm import DeclarativeBase

from pricepoint.db import SessionLocal

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=DeclarativeBase)

DEFAULT_PAGE_SIZE = 2000


def parse_arcgis_timestamp(value: int | None) -> datetime | None:
    """Convert an ArcGIS epoch-millisecond timestamp to a UTC datetime."""
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


def build_point_wkb(geometry: dict[str, Any] | None) -> object | None:
    """Convert ArcGIS point geometry ``{"x": ..., "y": ...}`` to WKB."""
    if geometry is None:
        return None
    try:
        x = geometry.get("x")
        y = geometry.get("y")
        if x is None or y is None:
            return None
        return from_shape(Point(float(x), float(y)), srid=4326)
    except (TypeError, ValueError) as exc:
        logger.warning("Failed to build Point from geometry: %s", exc)
        return None


def build_multipolygon_wkb(rings: list[list[list[float]]] | None) -> object | None:
    """Convert ArcGIS rings to a WKB MultiPolygon.

    ArcGIS returns geometry as ``{"rings": [[[x,y], ...], ...]}``.
    Each ring is a list of coordinate pairs.
    """
    if not rings:
        return None
    try:
        polygons = []
        exterior = None
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


def build_multilinestring_wkb(paths: list[list[list[float]]] | None) -> object | None:
    """Convert ArcGIS paths to a WKB MultiLineString.

    ArcGIS returns polyline geometry as ``{"paths": [[[x,y], ...], ...]}``.
    """
    if not paths:
        return None
    try:
        lines = [[(pt[0], pt[1]) for pt in path] for path in paths]
        if not lines:
            return None
        return from_shape(MultiLineString(lines), srid=4326)
    except (TypeError, ValueError) as exc:
        logger.warning("Failed to build MultiLineString from paths: %s", exc)
        return None


def query_arcgis_page(
    base_url: str,
    offset: int,
    count: int,
    where_clause: str = "1=1",
    geometry_envelope: tuple[float, float, float, float] | None = None,
) -> dict:
    """Query a page of features from an ArcGIS REST endpoint."""
    params: dict[str, str | int] = {
        "where": where_clause,
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": 4326,
        "resultOffset": offset,
        "resultRecordCount": count,
        "f": "json",
    }
    if geometry_envelope is not None:
        xmin, ymin, xmax, ymax = geometry_envelope
        params["geometry"] = f"{xmin},{ymin},{xmax},{ymax}"
        params["geometryType"] = "esriGeometryEnvelope"
        params["spatialRel"] = "esriSpatialRelIntersects"
        params["inSR"] = 4326
    response = httpx.get(f"{base_url}/query", params=params, timeout=120)
    response.raise_for_status()
    return response.json()


def fetch_arcgis_dataset(
    base_url: str,
    model_class: type[T],
    mapper: Callable[[dict], T],
    dataset_name: str,
    page_size: int = DEFAULT_PAGE_SIZE,
    where_clause: str = "1=1",
    geometry_envelope: tuple[float, float, float, float] | None = None,
) -> None:
    """Generic truncate-and-reload for an ArcGIS feature dataset.

    Deletes all existing records, paginates through all features from the
    ArcGIS REST endpoint, maps each to a model instance, and bulk inserts.
    """
    session = SessionLocal()
    try:
        session.execute(delete(model_class))

        offset = 0
        total = 0
        while True:
            data = query_arcgis_page(base_url, offset, page_size, where_clause, geometry_envelope)
            features = data.get("features", [])
            if not features:
                break

            records = [mapper(f) for f in features]
            session.add_all(records)
            session.flush()

            total += len(records)
            offset += len(features)
            logger.info("Loaded %d %s records (total: %d)", len(records), dataset_name, total)

            if len(features) < page_size:
                break

        session.commit()
        logger.info("%s load complete: %d records", dataset_name, total)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def verify_arcgis_dataset(model_class: type[T], dataset_name: str) -> None:
    """Verify that records were loaded for the given model class."""
    session = SessionLocal()
    try:
        count = session.execute(select(func.count()).select_from(model_class)).scalar()
        if not count:
            raise RuntimeError(f"No records found in {dataset_name} after load")
        logger.info("Verified %d records in %s", count, dataset_name)
    finally:
        session.close()

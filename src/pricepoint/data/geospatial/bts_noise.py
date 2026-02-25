"""Collect transportation noise data from BTS National Noise Map tiles.

Downloads pre-rendered PNG map tiles at zoom 12 from the BTS NTAD
Aviation+Road+Rail noise layer, classifies pixel colors into dB bands,
vectorizes into polygons with regional merging, and stores in PostGIS.

Tile endpoint:
    https://geo.dot.gov/server/rest/services/Hosted/
    NTAD_Noise_2020_CONUS_Aviation_Road_Rail/MapServer/tile/{z}/{y}/{x}
"""

from __future__ import annotations

import logging
import math
import time
from datetime import UTC, datetime
from io import BytesIO
from typing import Any

import httpx
import numpy as np
from geoalchemy2.shape import from_shape
from PIL import Image
from pyproj import Transformer
from rasterio.features import shapes as rasterio_shapes
from rasterio.transform import from_bounds
from scipy.ndimage import binary_closing
from shapely.geometry import MultiPolygon, shape
from shapely.ops import unary_union
from sqlalchemy import delete, func, select

from pricepoint.config.settings import get_settings
from pricepoint.db import SessionLocal
from pricepoint.db.models import TransportationNoise

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Color-to-dB-band mapping
# ---------------------------------------------------------------------------
# Each entry: (R, G, B) -> (min_db, max_db | None, band_label)
# Populated from BTS tile color ramp. max_db=None means "X dB+".
COLOR_TO_DB_BAND: dict[tuple[int, int, int], tuple[int, int | None, str]] = {
    (0, 157, 25): (45, 50, "45-50"),
    (0, 177, 28): (45, 50, "45-50"),
    (158, 213, 0): (50, 55, "50-55"),
    (178, 233, 0): (50, 55, "50-55"),
    (255, 255, 0): (55, 60, "55-60"),
    (255, 235, 0): (55, 60, "55-60"),
    (255, 200, 0): (60, 65, "60-65"),
    (255, 170, 0): (60, 65, "60-65"),
    (255, 127, 0): (65, 70, "65-70"),
    (255, 100, 0): (65, 70, "65-70"),
    (255, 60, 0): (70, 75, "70-75"),
    (255, 40, 0): (70, 75, "70-75"),
    (255, 0, 0): (75, 80, "75-80"),
    (230, 0, 0): (75, 80, "75-80"),
    (200, 0, 0): (80, 85, "80-85"),
    (180, 0, 0): (80, 85, "80-85"),
    (150, 0, 0): (85, 90, "85-90"),
    (130, 0, 0): (85, 90, "85-90"),
    (100, 0, 50): (90, None, "90+"),
    (80, 0, 40): (90, None, "90+"),
}

_COLOR_TOLERANCE = 20

# EPSG:3857 constants
_ORIGIN_SHIFT = 2 * math.pi * 6378137 / 2.0  # ~20037508.34 metres
_TILE_SIZE = 256
_SOURCE_LAYER = "aviation_road_rail"


# ---------------------------------------------------------------------------
# Tile math helpers
# ---------------------------------------------------------------------------
def _lat_lon_to_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    """Convert lat/lon to tile x, y at the given zoom level."""
    n = 2**zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    x = max(0, min(n - 1, x))
    y = max(0, min(n - 1, y))
    return x, y


def _tile_to_lat_lon(x: int, y: int, zoom: int) -> tuple[float, float]:
    """Convert tile x, y to lat/lon of the tile's NW corner."""
    n = 2**zoom
    lon = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat = math.degrees(lat_rad)
    return lat, lon


def _enumerate_tiles(
    south: float, north: float, west: float, east: float, zoom: int
) -> list[tuple[int, int]]:
    """Return all (x, y) tiles that cover the given bounding box at zoom level."""
    x_min, y_max = _lat_lon_to_tile(south, west, zoom)
    x_max, y_min = _lat_lon_to_tile(north, east, zoom)
    tiles = []
    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            tiles.append((x, y))
    return tiles


def _tile_bounds_3857(x: int, y: int, zoom: int) -> tuple[float, float, float, float]:
    """Return (west, south, east, north) in EPSG:3857 metres for the tile."""
    n = 2**zoom
    tile_size = 2 * _ORIGIN_SHIFT / n
    west = -_ORIGIN_SHIFT + x * tile_size
    east = west + tile_size
    north = _ORIGIN_SHIFT - y * tile_size
    south = north - tile_size
    return west, south, east, north


def _tile_affine(x: int, y: int, zoom: int) -> Any:
    """Return a rasterio Affine transform for a tile in EPSG:3857."""
    west, south, east, north = _tile_bounds_3857(x, y, zoom)
    return from_bounds(west, south, east, north, _TILE_SIZE, _TILE_SIZE)


# ---------------------------------------------------------------------------
# Tile download
# ---------------------------------------------------------------------------
def _download_tile(
    client: httpx.Client,
    url_template: str,
    z: int,
    x: int,
    y: int,
    rate_limit: float = 0.05,
) -> bytes | None:
    """Download a single PNG tile. Returns bytes or None on failure."""
    url = url_template.format(z=z, y=y, x=x)
    try:
        resp = client.get(url, timeout=30)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        if rate_limit > 0:
            time.sleep(rate_limit)
        return resp.content
    except httpx.HTTPError:
        logger.warning("Failed to download tile z=%d x=%d y=%d", z, x, y)
        return None


# ---------------------------------------------------------------------------
# Color classification
# ---------------------------------------------------------------------------
def _match_color(
    r: int, g: int, b: int, tolerance: int = _COLOR_TOLERANCE
) -> tuple[int, int | None, str] | None:
    """Find the nearest dB band for an RGB color within tolerance."""
    best_dist = float("inf")
    best_band: tuple[int, int | None, str] | None = None
    for (cr, cg, cb), band in COLOR_TO_DB_BAND.items():
        dist = math.sqrt((r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2)
        if dist < best_dist and dist <= tolerance:
            best_dist = dist
            best_band = band
    return best_band


def _classify_tile(png_bytes: bytes) -> np.ndarray:
    """Classify tile pixels into dB band indices.

    Returns a (256, 256) uint8 array where 0 = no data/transparent
    and 1..N maps to distinct dB bands. The band mapping is returned
    via the module-level BAND_INDEX_TO_DB dict built on first call.
    """
    img = Image.open(BytesIO(png_bytes)).convert("RGBA")
    pixels = np.array(img)

    classified = np.zeros((_TILE_SIZE, _TILE_SIZE), dtype=np.uint8)

    # Build a cache of unique (R,G,B) -> band_index seen in this tile
    band_labels = _get_band_labels()
    label_to_index = {label: i + 1 for i, label in enumerate(band_labels)}

    for row in range(_TILE_SIZE):
        for col in range(_TILE_SIZE):
            r, g, b, a = pixels[row, col]
            if a < 128:  # transparent = no data
                continue
            match = _match_color(int(r), int(g), int(b))
            if match is not None:
                _, _, label = match
                classified[row, col] = label_to_index[label]

    return classified


def _get_band_labels() -> list[str]:
    """Return sorted unique band labels from COLOR_TO_DB_BAND."""
    labels: set[str] = set()
    for _, _, label in COLOR_TO_DB_BAND.values():
        labels.add(label)
    return sorted(labels)


def _get_band_info(label: str) -> tuple[int, int | None]:
    """Return (min_db, max_db) for a band label."""
    for _, (min_db, max_db, lbl) in COLOR_TO_DB_BAND.items():
        if lbl == label:
            return min_db, max_db
    raise ValueError(f"Unknown band label: {label}")


# ---------------------------------------------------------------------------
# Morphological smoothing (pre-vectorization)
# ---------------------------------------------------------------------------
def _smooth_classified(classified: np.ndarray) -> np.ndarray:
    """Apply morphological closing per band to fill single-pixel gaps.

    Uses a 3×3 cross (4-connected) structuring element so closing fills
    narrow gaps without aggressively expanding into diagonal neighbours.
    Only unclassified (0) pixels are overwritten; existing band boundaries
    are preserved.

    Returns a new array; the input is not mutated.
    """
    # 4-connected cross kernel
    structure = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=bool)

    result = classified.copy()
    max_band = int(classified.max())

    for band_idx in range(1, max_band + 1):
        mask = classified == band_idx
        closed = binary_closing(mask, structure=structure)
        # Only fill pixels that are currently unclassified (0)
        fill = closed & (result == 0)
        result[fill] = band_idx

    return result


# ---------------------------------------------------------------------------
# Vectorization
# ---------------------------------------------------------------------------
def _vectorize_tiles(
    tile_data: list[tuple[tuple[int, int], np.ndarray]],
    zoom: int,
) -> dict[str, list[Any]]:
    """Vectorize classified tile arrays into shapely polygons per dB band.

    Returns {band_label: [polygon, ...]} in EPSG:3857.
    """
    band_labels = _get_band_labels()
    result: dict[str, list[Any]] = {label: [] for label in band_labels}

    for (tx, ty), classified in tile_data:
        transform = _tile_affine(tx, ty, zoom)
        for geom_dict, value in rasterio_shapes(classified, transform=transform):
            if value == 0:
                continue
            idx = int(value) - 1
            if 0 <= idx < len(band_labels):
                label = band_labels[idx]
                poly = shape(geom_dict)
                if poly.is_valid and not poly.is_empty:
                    result[label].append(poly)

    return result


# ---------------------------------------------------------------------------
# Merge & reproject
# ---------------------------------------------------------------------------
_transformer_3857_to_4326 = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)


def _reproject_3857_to_4326(geom: Any) -> Any:
    """Reproject a shapely geometry from EPSG:3857 to EPSG:4326."""
    from shapely.ops import transform as shapely_transform

    return shapely_transform(_transformer_3857_to_4326.transform, geom)


def _merge_batch_polygons(
    band_polygons: dict[str, list[Any]],
    simplify_tolerance: float,
    min_area_sq_m: float,
    smooth_buffer_m: float = 0.0,
) -> list[dict[str, Any]]:
    """Merge polygons per band, simplify, reproject, and return insert dicts."""
    records: list[dict[str, Any]] = []

    for label, polys in band_polygons.items():
        if not polys:
            continue
        merged = unary_union(polys)
        if merged.is_empty:
            continue

        # Morphological closing in EPSG:3857 (metres): inflate then
        # deflate.  The positive buffer expands pixel squares so that
        # staircase notches (each ~38 m at zoom 12) are absorbed; the
        # negative buffer shrinks back to the original width while
        # keeping the smoothed outline.  Set smooth_buffer_m > pixel
        # size (~38 m at zoom 12) for full staircase elimination.
        if smooth_buffer_m > 0:
            merged = merged.buffer(smooth_buffer_m).buffer(-smooth_buffer_m)
            if not merged.is_valid:
                merged = merged.buffer(0)
            if merged.is_empty:
                continue

        # Ensure we have a list of individual polygons/multipolygons
        if merged.geom_type == "Polygon":
            parts = [merged]
        elif merged.geom_type == "MultiPolygon":
            parts = list(merged.geoms)
        elif merged.geom_type == "GeometryCollection":
            parts = [g for g in merged.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
        else:
            continue

        for part in parts:
            if part.area < min_area_sq_m:
                continue
            simplified = part.simplify(simplify_tolerance, preserve_topology=True)
            if simplified.is_empty:
                continue
            reprojected = _reproject_3857_to_4326(simplified)
            if reprojected.geom_type == "Polygon":
                reprojected = MultiPolygon([reprojected])

            min_db, max_db = _get_band_info(label)
            records.append(
                {
                    "noise_min_db": min_db,
                    "noise_max_db": max_db,
                    "noise_band": label,
                    "source_layer": _SOURCE_LAYER,
                    "area_sq_m": part.area,
                    "geom": reprojected,
                }
            )

    return records


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------
def fetch_transportation_noise() -> int:
    """Download BTS noise tiles, vectorize, and load into PostGIS.

    Returns the total number of polygon records inserted.
    """
    settings = get_settings()
    zoom = settings.bts_noise_zoom
    url_template = settings.bts_noise_tile_url
    rate_limit = settings.bts_noise_tile_rate_limit
    batch_size = settings.bts_noise_batch_size
    simplify_tol = settings.bts_noise_simplify_tolerance
    min_area = settings.bts_noise_min_polygon_area_sq_m
    morphological_closing = settings.bts_noise_morphological_closing
    smooth_buffer_m = settings.bts_noise_smooth_buffer_m

    tiles = _enumerate_tiles(
        settings.bts_noise_bbox_south,
        settings.bts_noise_bbox_north,
        settings.bts_noise_bbox_west,
        settings.bts_noise_bbox_east,
        zoom,
    )
    logger.info("Enumerated %d tiles at zoom %d", len(tiles), zoom)

    run_started = datetime.now(UTC)
    total_records = 0

    client = httpx.Client()
    session = SessionLocal()
    try:
        # Process tiles in spatial batches
        for batch_start in range(0, len(tiles), batch_size):
            batch_tiles = tiles[batch_start : batch_start + batch_size]
            tile_data: list[tuple[tuple[int, int], np.ndarray]] = []

            for tx, ty in batch_tiles:
                png_bytes = _download_tile(client, url_template, zoom, tx, ty, rate_limit)
                if png_bytes is None:
                    continue
                classified = _classify_tile(png_bytes)
                if morphological_closing:
                    classified = _smooth_classified(classified)
                if classified.any():
                    tile_data.append(((tx, ty), classified))

            if not tile_data:
                continue

            band_polygons = _vectorize_tiles(tile_data, zoom)
            records = _merge_batch_polygons(band_polygons, simplify_tol, min_area, smooth_buffer_m)

            for rec in records:
                geom_wkb = from_shape(rec["geom"], srid=4326)
                noise = TransportationNoise(
                    noise_min_db=rec["noise_min_db"],
                    noise_max_db=rec["noise_max_db"],
                    noise_band=rec["noise_band"],
                    source_layer=rec["source_layer"],
                    area_sq_m=rec["area_sq_m"],
                    geom=geom_wkb,
                    loaded_at=run_started,
                )
                session.add(noise)

            session.commit()
            total_records += len(records)
            logger.info(
                "Batch %d-%d: inserted %d polygons",
                batch_start,
                batch_start + len(batch_tiles),
                len(records),
            )

        # Clean up stale rows from previous runs
        if total_records > 0:
            stale_count = session.execute(
                delete(TransportationNoise).where(TransportationNoise.loaded_at < run_started)
            ).rowcount  # type: ignore[union-attr, attr-defined]
            session.commit()
            if stale_count:
                logger.info("Removed %d stale noise polygons", stale_count)

        logger.info("Transportation noise total loaded: %d polygons", total_records)
        return total_records

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        client.close()


def verify_transportation_noise() -> int:
    """Verify that records were loaded into the noises table.

    Returns the record count. Raises RuntimeError if the table is empty.
    """
    session = SessionLocal()
    try:
        count = session.execute(select(func.count()).select_from(TransportationNoise)).scalar() or 0
        if not count:
            raise RuntimeError("No records found in noises after load")
        logger.info("Verified %d noise polygon records", count)
        return count
    finally:
        session.close()


def discover_tile_colors(
    sample_tiles: list[tuple[int, int]] | None = None,
    zoom: int = 12,
) -> set[tuple[int, int, int]]:
    """Dev utility: extract unique non-transparent RGB values from sample tiles.

    Useful for populating/verifying the COLOR_TO_DB_BAND mapping.
    """
    settings = get_settings()
    url_template = settings.bts_noise_tile_url

    if sample_tiles is None:
        # Default: a few tiles near Wake County
        sample_tiles = [
            (1133, 1594),
            (1134, 1594),
            (1133, 1595),
            (1134, 1595),
        ]

    colors: set[tuple[int, int, int]] = set()
    client = httpx.Client()
    try:
        for tx, ty in sample_tiles:
            png_bytes = _download_tile(client, url_template, zoom, tx, ty)
            if png_bytes is None:
                continue
            img = Image.open(BytesIO(png_bytes)).convert("RGBA")
            pixels = np.array(img)
            for row in range(_TILE_SIZE):
                for col in range(_TILE_SIZE):
                    r, g, b, a = pixels[row, col]
                    if a >= 128:
                        colors.add((int(r), int(g), int(b)))
    finally:
        client.close()

    logger.info("Discovered %d unique colors from %d tiles", len(colors), len(sample_tiles))
    return colors

"""Collect transportation noise data from BTS National Noise Map tiles.

Downloads pre-rendered PNG map tiles at zoom 12 from BTS NTAD noise
layers (aviation, road, rail, combined), classifies pixel colors into
dB bands, vectorizes into raw polygons stored in a staging table, then
uses PostGIS to cluster, merge, smooth (Chaikin), and promote to the
production ``noises`` table.

Tile endpoint pattern:
    {base_url}/{service_name}/MapServer/tile/{z}/{y}/{x}
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
from sqlalchemy import delete, func, select, text

from pricepoint.config.settings import Settings, get_settings
from pricepoint.db import SessionLocal
from pricepoint.db.models import StagingTransportationNoise, TransportationNoise

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Color-to-dB-band mapping
# ---------------------------------------------------------------------------
# Each entry: (R, G, B) -> (min_db, max_db | None, band_label)
# Matched to the official BTS National Noise Map legend (24-hr LAeq dBA).
# max_db=None means "X dB+".
COLOR_TO_DB_BAND: dict[tuple[int, int, int], tuple[int, int | None, str]] = {
    (255, 193, 7): (45, 50, "45.0-49.9"),
    (255, 128, 0): (50, 55, "50.0-54.9"),
    (255, 0, 0): (55, 60, "55.0-59.9"),
    (255, 51, 153): (60, 70, "60.0-69.9"),
    (163, 0, 204): (70, 80, "70.0-79.9"),
    (82, 0, 204): (80, 90, "80.0-89.9"),
    (0, 0, 255): (90, None, ">90.0"),
}

_COLOR_TOLERANCE = 20

# EPSG:3857 constants
_ORIGIN_SHIFT = 2 * math.pi * 6378137 / 2.0  # ~20037508.34 metres
_TILE_SIZE = 256

# ---------------------------------------------------------------------------
# BTS noise mode registry
# ---------------------------------------------------------------------------
# Maps mode key -> BTS tile service name.  All four use the same color ramp,
# zoom levels, and classification logic — only the URL differs.
NOISE_MODES: dict[str, str] = {
    "aviation": "NTAD_Noise_2020_CONUS_Aviation",
    "road": "NTAD_Noise_2020_CONUS_Road",
    "rail": "NTAD_Noise_2020_CONUS_Rail",
    "aviation_road_rail": "NTAD_Noise_2020_CONUS_Aviation_Road_Rail",
}


def _tile_url_template(base_url: str, service_name: str) -> str:
    """Build a tile URL template from the base URL and service name."""
    return f"{base_url}/{service_name}/MapServer/tile/{{z}}/{{y}}/{{x}}"


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

    Uses a 3x3 cross (4-connected) structuring element so closing fills
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
# Merge & reproject (for staging insertion)
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
    source_layer: str,
) -> list[dict[str, Any]]:
    """Merge polygons per band within a batch, reproject, and return insert dicts.

    Raw polygons are merged via ``unary_union`` to reduce row count within a
    batch, then reprojected to EPSG:4326 for staging insertion.  Final
    cross-batch merging and smoothing happens in ``_build_noise_production``.
    """
    records: list[dict[str, Any]] = []

    for label, polys in band_polygons.items():
        if not polys:
            continue
        merged = unary_union(polys)
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
                    "source_layer": source_layer,
                    "area_sq_m": part.area,
                    "geom": reprojected,
                }
            )

    return records


# ---------------------------------------------------------------------------
# PostGIS smoothing: staging -> production
# ---------------------------------------------------------------------------
_PROMOTE_SQL = """\
WITH smoothed_raw AS (
    SELECT
        noise_min_db, noise_max_db, noise_band, source_layer, loaded_at,
        ST_Multi(
            ST_SimplifyPreserveTopology(
                ST_ChaikinSmoothing(
                    ST_Buffer(
                        ST_Buffer(ST_Union(geom), :buffer_dist),
                        -:buffer_dist
                    ),
                    :iterations
                ),
                :tolerance
            )
        ) AS smoothed_geom
    FROM (
        SELECT *,
            ST_ClusterDBSCAN(geom, eps := :cluster_eps, minpoints := 1)
                OVER (PARTITION BY noise_band) AS cluster_id
        FROM staging_noises
        WHERE loaded_at = :run_started AND source_layer = :source_layer
    ) clustered
    GROUP BY noise_min_db, noise_max_db, noise_band, source_layer, loaded_at, cluster_id
),
smoothed AS (
    SELECT * FROM smoothed_raw
    WHERE smoothed_geom IS NOT NULL AND NOT ST_IsEmpty(smoothed_geom)
),
band_merged AS (
    SELECT
        noise_min_db, noise_max_db, noise_band, source_layer, loaded_at,
        ST_Union(smoothed_geom) AS band_geom
    FROM smoothed
    GROUP BY noise_min_db, noise_max_db, noise_band, source_layer, loaded_at
),
holes_filled AS (
    SELECT
        noise_min_db, noise_max_db, noise_band, source_layer, loaded_at,
        ST_Multi(ST_Collect(filled_poly)) AS band_geom
    FROM (
        SELECT
            noise_min_db, noise_max_db, noise_band, source_layer, loaded_at,
            COALESCE(
                ST_MakePolygon(
                    ST_ExteriorRing(poly),
                    (SELECT array_agg(ST_InteriorRingN(poly, gs.n))
                     FROM generate_series(1, ST_NumInteriorRings(poly)) gs(n)
                     WHERE ST_Area(
                         ST_MakePolygon(ST_InteriorRingN(poly, gs.n))::geography
                     ) >= :max_hole_area)
                ),
                ST_MakePolygon(ST_ExteriorRing(poly))
            ) AS filled_poly
        FROM (
            SELECT *, (ST_Dump(band_geom)).geom AS poly
            FROM band_merged
        ) dumped
        WHERE ST_GeometryType(poly) = 'ST_Polygon'
    ) filled
    GROUP BY noise_min_db, noise_max_db, noise_band, source_layer, loaded_at
),
higher_union AS (
    SELECT
        b.noise_min_db,
        ST_Union(louder.band_geom) AS louder_geom
    FROM holes_filled b
    JOIN holes_filled louder ON louder.noise_min_db > b.noise_min_db
    GROUP BY b.noise_min_db
),
cut AS (
    SELECT
        b.noise_min_db, b.noise_max_db, b.noise_band,
        b.source_layer, b.loaded_at,
        ST_Multi(
            ST_CollectionExtract(
                COALESCE(
                    ST_Difference(b.band_geom, h.louder_geom),
                    b.band_geom
                ),
                3
            )
        ) AS cut_geom
    FROM holes_filled b
    LEFT JOIN higher_union h ON h.noise_min_db = b.noise_min_db
)
INSERT INTO noises (
    noise_min_db, noise_max_db, noise_band, source_layer,
    area_sq_m, geom, loaded_at
)
SELECT
    noise_min_db, noise_max_db, noise_band, source_layer,
    ST_Area(cut_geom::geography) AS area_sq_m,
    cut_geom AS geom,
    loaded_at
FROM cut
WHERE cut_geom IS NOT NULL AND NOT ST_IsEmpty(cut_geom)
    AND ST_Area(cut_geom::geography) >= :min_area
"""


def _build_noise_production(
    session: Any,
    source_layer: str,
    run_started: datetime,
    settings: Settings,
) -> int:
    """Cluster, merge, smooth, and promote staging noise polygons to production for one mode."""
    result = session.execute(
        text(_PROMOTE_SQL),
        {
            "iterations": settings.bts_noise_chaikin_iterations,
            "tolerance": settings.bts_noise_simplify_tolerance,
            "cluster_eps": settings.bts_noise_cluster_eps,
            "buffer_dist": settings.bts_noise_buffer_distance,
            "max_hole_area": settings.bts_noise_max_hole_area_sq_m,
            "min_area": settings.bts_noise_min_polygon_area_sq_m,
            "run_started": run_started,
            "source_layer": source_layer,
        },
    )
    session.commit()
    count: int = result.rowcount  # type: ignore[assignment]
    logger.info(
        "Promoted %d smoothed production polygons for %s",
        count,
        source_layer,
    )
    return count


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------
def fetch_transportation_noise(
    mode: str = "aviation_road_rail",
    bbox: tuple[float, float, float, float] | None = None,
) -> int:
    """Download BTS noise tiles for one mode, vectorize, stage, smooth, and load.

    Args:
        mode: One of the ``NOISE_MODES`` keys (aviation, road, rail,
              aviation_road_rail).
        bbox: Optional ``(south, north, west, east)`` bounding box in
              degrees.  When *None*, falls back to the settings defaults.

    Returns the number of production polygon records inserted.
    """
    if mode not in NOISE_MODES:
        raise ValueError(f"Unknown noise mode {mode!r}; choose from {list(NOISE_MODES)}")

    settings = get_settings()
    zoom = settings.bts_noise_zoom
    service_name = NOISE_MODES[mode]
    url_template = _tile_url_template(settings.bts_noise_base_url, service_name)
    rate_limit = settings.bts_noise_tile_rate_limit
    batch_size = settings.bts_noise_batch_size
    simplify_tol = settings.bts_noise_simplify_tolerance
    min_area = settings.bts_noise_min_polygon_area_sq_m
    morphological_closing = settings.bts_noise_morphological_closing
    source_layer = mode

    if bbox is not None:
        bb_south, bb_north, bb_west, bb_east = bbox
    else:
        bb_south = settings.bts_noise_bbox_south
        bb_north = settings.bts_noise_bbox_north
        bb_west = settings.bts_noise_bbox_west
        bb_east = settings.bts_noise_bbox_east

    tiles = _enumerate_tiles(bb_south, bb_north, bb_west, bb_east, zoom)
    logger.info("Enumerated %d tiles at zoom %d for mode %s", len(tiles), zoom, mode)

    run_started = datetime.now(UTC)
    staging_count = 0

    client = httpx.Client()
    session = SessionLocal()
    try:
        # Phase 1: download tiles → classify → vectorize → insert into staging
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
            records = _merge_batch_polygons(band_polygons, simplify_tol, min_area, source_layer)

            for rec in records:
                geom_wkb = from_shape(rec["geom"], srid=4326)
                staging = StagingTransportationNoise(
                    noise_min_db=rec["noise_min_db"],
                    noise_max_db=rec["noise_max_db"],
                    noise_band=rec["noise_band"],
                    source_layer=rec["source_layer"],
                    area_sq_m=rec["area_sq_m"],
                    geom=geom_wkb,
                    loaded_at=run_started,
                )
                session.add(staging)

            session.commit()
            staging_count += len(records)
            logger.info(
                "Batch %d-%d: staged %d polygons for %s",
                batch_start,
                batch_start + len(batch_tiles),
                len(records),
                mode,
            )

        if staging_count == 0:
            logger.info("No staging polygons for mode %s — skipping promotion", mode)
            return 0

        # Phase 2: PostGIS clustering + smoothing → production
        prod_count = _build_noise_production(session, source_layer, run_started, settings)

        # Clean up stale production rows for this source_layer only
        stale_count = session.execute(
            delete(TransportationNoise).where(
                TransportationNoise.loaded_at < run_started,
                TransportationNoise.source_layer == source_layer,
            )
        ).rowcount  # type: ignore[union-attr, attr-defined]
        session.commit()
        if stale_count:
            logger.info("Removed %d stale production polygons for %s", stale_count, mode)

        # Clean up staging rows for this run+mode
        session.execute(
            delete(StagingTransportationNoise).where(
                StagingTransportationNoise.loaded_at == run_started,
                StagingTransportationNoise.source_layer == source_layer,
            )
        )
        session.commit()

        logger.info("Mode %s total loaded: %d production polygons", mode, prod_count)
        return prod_count

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        client.close()


def fetch_all_transportation_noise(
    bbox: tuple[float, float, float, float] | None = None,
) -> int:
    """Fetch all configured BTS noise modes and return total production count.

    Args:
        bbox: Optional ``(south, north, west, east)`` bounding box passed
              through to each :func:`fetch_transportation_noise` call.
    """
    settings = get_settings()
    total = 0
    for mode in settings.bts_noise_modes:
        total += fetch_transportation_noise(mode=mode, bbox=bbox)
    return total


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
    mode: str = "aviation_road_rail",
) -> set[tuple[int, int, int]]:
    """Dev utility: extract unique non-transparent RGB values from sample tiles.

    Useful for populating/verifying the COLOR_TO_DB_BAND mapping.
    """
    settings = get_settings()
    service_name = NOISE_MODES.get(mode, NOISE_MODES["aviation_road_rail"])
    url_template = _tile_url_template(settings.bts_noise_base_url, service_name)

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

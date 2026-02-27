"""Collect PAD-US (Protected Areas Database) greenspace data.

Downloads the PAD-US Geodatabase ZIP from USGS ScienceBase, extracts the
.gdb, filters to publicly accessible terrestrial areas, and upserts into
the greenspaces table keyed on source_id (PAD-US FID).
"""

from __future__ import annotations

import logging
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import httpx
from geoalchemy2.shape import from_shape
from shapely.geometry import MultiPolygon
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from pricepoint.config.settings import get_settings
from pricepoint.db import SessionLocal
from pricepoint.db.models import Greenspace

logger = logging.getLogger(__name__)

_BATCH_SIZE = 500

# Designation types to exclude (marine / aquatic / unknown)
_EXCLUDED_DES_TP = {"MPA", "MR", "RNA", "UNKW"}

# Public access values to keep (Open Access, Restricted Access)
_ALLOWED_PUB_ACCESS = {"OA", "RA"}

# Columns to update on upsert conflict (everything except source_id and id)
_UPDATABLE_COLUMNS = [
    "name",
    "gis_acres",
    "manager_type",
    "manager_name",
    "designation_type",
    "pub_access",
    "gap_sts",
    "state_name",
    "category",
    "geom",
    "loaded_at",
]


def _should_include(row: Any) -> bool:
    """Return True if the PAD-US feature should be included."""
    pub_access = row.get("Pub_Access")
    des_tp = row.get("Des_Tp")
    if pub_access not in _ALLOWED_PUB_ACCESS:
        return False
    return des_tp not in _EXCLUDED_DES_TP


def _to_multipolygon_wkb(geom: Any) -> Any:
    """Convert a shapely geometry to a WKB MultiPolygon (SRID 4326)."""
    if geom is None:
        return None
    if geom.geom_type == "Polygon":
        geom = MultiPolygon([geom])
    return from_shape(geom, srid=4326)


def _parse_pad_us_row(row: Any) -> dict[str, Any]:
    """Extract model column values from a GeoDataFrame row."""
    gap_raw = row.get("GAP_Sts")
    gap_sts = int(gap_raw) if gap_raw is not None and gap_raw != "" else None

    return {
        "source_id": int(row.get("FID")) if row.get("FID") is not None else int(row.name),
        "name": row.get("Unit_Nm"),
        "gis_acres": float(row.get("GIS_Acres")) if row.get("GIS_Acres") is not None else None,
        "manager_type": row.get("Mang_Type"),
        "manager_name": row.get("Mang_Name"),
        "designation_type": row.get("Des_Tp"),
        "pub_access": row.get("Pub_Access"),
        "gap_sts": gap_sts,
        "state_name": row.get("d_State_Nm"),
        "category": row.get("Category"),
        "geom": _to_multipolygon_wkb(row.geometry),
    }


def fetch_pad_us() -> int:
    """Download PAD-US GeoPackage and upsert Fee features into greenspaces.

    Uses direct upsert keyed on source_id.  After all batches, stale rows
    (loaded_at < run start) are cleaned up.

    Returns the total record count.
    """
    settings = get_settings()
    run_started = datetime.now(UTC)

    # Download Geodatabase ZIP and extract
    logger.info("Downloading PAD-US Geodatabase ZIP from %s", settings.pad_us_download_url)
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "padus.zip"
        with httpx.stream(
            "GET", settings.pad_us_download_url, timeout=600, follow_redirects=True
        ) as resp:
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "application/zip" not in content_type and "application/octet-stream" not in content_type:
                raise RuntimeError(
                    f"PAD-US download URL returned unexpected content "
                    f"(content-type: {content_type}). Expected a ZIP file. "
                    f"The ScienceBase URL may have changed — check "
                    f"pad_us_download_url in settings."
                )
            with open(zip_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)

        logger.info("Extracting ZIP archive")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmpdir)

        # Find the .gdb directory inside the extracted files
        gdb_dirs = list(Path(tmpdir).rglob("*.gdb"))
        if not gdb_dirs:
            raise FileNotFoundError("No .gdb directory found in PAD-US ZIP archive")
        gdb_path = gdb_dirs[0]

        logger.info("Reading layer %s from %s", settings.pad_us_layer_name, gdb_path.name)
        gdf = gpd.read_file(gdb_path, layer=settings.pad_us_layer_name)

    logger.info("PAD-US raw features: %d", len(gdf))

    total = 0
    batch: list[dict[str, Any]] = []

    for _, row in gdf.iterrows():
        if not _should_include(row):
            continue

        values = _parse_pad_us_row(row)
        values["loaded_at"] = run_started
        batch.append(values)

        if len(batch) >= _BATCH_SIZE:
            _upsert_batch_safe(batch)
            total += len(batch)
            logger.info("PAD-US upserted %d records so far", total)
            batch = []

    if batch:
        _upsert_batch_safe(batch)
        total += len(batch)

    # Remove stale rows not seen in this run
    if total > 0:
        session = SessionLocal()
        try:
            stale_count = session.execute(
                delete(Greenspace).where(Greenspace.loaded_at < run_started)
            ).rowcount  # type: ignore[union-attr, attr-defined]
            session.commit()
            if stale_count:
                logger.info("Removed %d stale greenspace records", stale_count)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    logger.info("PAD-US total loaded: %d records", total)
    return total


def _upsert_batch_safe(batch: list[dict[str, Any]]) -> None:
    """Upsert a batch of records using a short-lived session.

    Each batch gets its own session to avoid long-lived connections that
    PostgreSQL may terminate during large multi-batch loads.
    """
    session = SessionLocal()
    try:
        stmt = pg_insert(Greenspace).values(batch)
        stmt = stmt.on_conflict_do_update(
            index_elements=["source_id"],
            set_={col: stmt.excluded[col] for col in _UPDATABLE_COLUMNS},
        )
        session.execute(stmt)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def verify_pad_us() -> int:
    """Verify that records were loaded into the greenspaces table.

    Returns the record count. Raises RuntimeError if the table is empty.
    """
    session = SessionLocal()
    try:
        count = session.execute(select(func.count()).select_from(Greenspace)).scalar() or 0
        if not count:
            raise RuntimeError("No records found in greenspaces after PAD-US load")
        logger.info("Verified %d greenspace records", count)
        return count
    finally:
        session.close()

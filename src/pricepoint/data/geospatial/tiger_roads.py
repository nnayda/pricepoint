"""Collect US Census TIGER/Line primary and secondary road shapefiles into PostGIS.

Downloads state-level PRISECROADS shapefiles (containing both S1100 primary
and S1200 secondary road MTFCC classes) for all US states and loads them
into the ``roads`` table.
"""

import logging
import tempfile
from pathlib import Path

import geopandas as gpd
import httpx
from geoalchemy2.shape import from_shape
from shapely.geometry import MultiLineString
from sqlalchemy import delete, func, select

from pricepoint.config.settings import get_settings
from pricepoint.data.geospatial.tiger_boundaries import US_STATE_FIPS
from pricepoint.db import SessionLocal
from pricepoint.db.models import Road

logger = logging.getLogger(__name__)


_FALLBACK_YEARS = 3  # Number of previous years to try if current year fails


def _tiger_road_url(state_fips: str, year: int | None = None) -> str:
    """Build a TIGER/Line PRISECROADS shapefile download URL."""
    settings = get_settings()
    yr = year if year is not None else settings.tiger_year
    return f"{settings.tiger_base_url}/TIGER{yr}/PRISECROADS/tl_{yr}_{state_fips}_prisecroads.zip"


def _is_valid_zip(response: httpx.Response) -> bool:
    """Check if an HTTP response contains a valid ZIP file."""
    content_type = response.headers.get("content-type", "")
    if "application/zip" not in content_type and "application/octet-stream" not in content_type:
        return False
    return response.content[:4] == b"PK\x03\x04"


def _download_tiger_zip(url: str) -> bytes:
    """Download a TIGER/Line shapefile zip archive."""
    logger.info("Downloading TIGER shapefile: %s", url)
    response = httpx.get(url, timeout=300, follow_redirects=True)
    response.raise_for_status()

    if not _is_valid_zip(response):
        content_type = response.headers.get("content-type", "")
        raise RuntimeError(
            f"TIGER download returned unexpected content "
            f"(content-type: {content_type}). Expected a ZIP file. "
            f"URL: {url}"
        )

    return response.content


def _read_shapefile(zip_bytes: bytes) -> gpd.GeoDataFrame:
    """Read a shapefile from zip archive bytes into a GeoDataFrame."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        zip_path = Path(tmp_dir) / "shapefile.zip"
        zip_path.write_bytes(zip_bytes)
        return gpd.read_file(zip_path)


def _to_multilinestring_wkb(geom):
    """Convert a shapely geometry to a WKB MultiLineString."""
    if geom.geom_type == "LineString":
        geom = MultiLineString([geom])
    return from_shape(geom, srid=4326)


def _download_with_year_fallback(state_fips: str, year: int) -> bytes | None:
    """Try downloading TIGER roads for the given year, falling back to previous years.

    Returns the ZIP bytes on success, or None if the state is unavailable.
    """
    for yr in range(year, year - _FALLBACK_YEARS - 1, -1):
        url = _tiger_road_url(state_fips, yr)
        try:
            return _download_tiger_zip(url)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.warning("TIGER PRISECROADS %d not found for state %s", yr, state_fips)
            else:
                raise
        except RuntimeError:
            if yr > year - _FALLBACK_YEARS:
                logger.warning(
                    "TIGER PRISECROADS %d unavailable for state %s, trying %d",
                    yr,
                    state_fips,
                    yr - 1,
                )
            else:
                logger.warning(
                    "TIGER PRISECROADS unavailable for state %s (tried years %d–%d)",
                    state_fips,
                    year,
                    yr,
                )
    return None


def fetch_roads(state_fips: str | None = None) -> None:
    """Fetch TIGER/Line primary and secondary roads (PRISECROADS) for all US states.

    Downloads state-level PRISECROADS shapefiles which contain both S1100
    (primary) and S1200 (secondary) MTFCC road classes.

    Args:
        state_fips: If provided, fetch only this state. Otherwise fetch all states.
    """
    fips_list = [state_fips] if state_fips else US_STATE_FIPS

    session = SessionLocal()
    try:
        session.execute(delete(Road))

        settings = get_settings()
        total = 0
        seen_linearids: set[str] = set()
        for fips in fips_list:
            zip_bytes = _download_with_year_fallback(fips, settings.tiger_year)
            if zip_bytes is None:
                continue

            gdf = _read_shapefile(zip_bytes)

            records = []
            dupes = 0
            for _, row in gdf.iterrows():
                lid = row.get("LINEARID")
                if lid in seen_linearids:
                    dupes += 1
                    continue
                seen_linearids.add(lid)
                records.append(
                    Road(
                        linearid=lid,
                        fullname=row.get("FULLNAME"),
                        rttyp=row.get("RTTYP"),
                        mtfcc=row.get("MTFCC"),
                        geom=_to_multilinestring_wkb(row.geometry),
                    )
                )

            if records:
                session.add_all(records)
                session.flush()

            if dupes:
                logger.info(
                    "TIGER roads state %s: %d records (%d duplicate linearids skipped)",
                    fips,
                    len(records),
                    dupes,
                )
            else:
                logger.info("TIGER roads state %s: %d records", fips, len(records))
            total += len(records)

        session.commit()
        logger.info("TIGER roads total: %d records", total)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def verify_roads() -> None:
    """Verify records were loaded into the roads table.

    Raises:
        RuntimeError: If no records found.
    """
    session = SessionLocal()
    try:
        count = session.execute(select(func.count()).select_from(Road)).scalar()
        if not count:
            raise RuntimeError("No records found in roads after load")
        logger.info("Verified %d records in roads", count)
    finally:
        session.close()

"""Collect US Census TIGER/Line primary and secondary road shapefiles into PostGIS.

Downloads state-level PRISECROADS shapefiles (containing both S1100 primary
and S1200 secondary road MTFCC classes) for all US states and loads them
into the ``roads`` table.
"""

import logging
import os
import tempfile

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


def _tiger_road_url(state_fips: str) -> str:
    """Build a TIGER/Line PRISECROADS shapefile download URL."""
    settings = get_settings()
    return (
        f"{settings.tiger_base_url}/TIGER{settings.tiger_year}"
        f"/PRISECROADS/tl_{settings.tiger_year}_{state_fips}_prisecroads.zip"
    )


def _download_tiger_zip(url: str) -> bytes:
    """Download a TIGER/Line shapefile zip archive."""
    logger.info("Downloading TIGER shapefile: %s", url)
    response = httpx.get(url, timeout=300, follow_redirects=True)
    response.raise_for_status()
    return response.content


def _read_shapefile(zip_bytes: bytes) -> gpd.GeoDataFrame:
    """Read a shapefile from zip archive bytes into a GeoDataFrame."""
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)  # noqa: SIM115
    try:
        tmp.write(zip_bytes)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        return gpd.read_file(tmp.name)
    finally:
        os.unlink(tmp.name)


def _to_multilinestring_wkb(geom):
    """Convert a shapely geometry to a WKB MultiLineString."""
    if geom.geom_type == "LineString":
        geom = MultiLineString([geom])
    return from_shape(geom, srid=4326)


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

        total = 0
        for fips in fips_list:
            url = _tiger_road_url(fips)
            try:
                zip_bytes = _download_tiger_zip(url)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    logger.warning("TIGER PRISECROADS not found for state %s, skipping", fips)
                    continue
                raise

            gdf = _read_shapefile(zip_bytes)

            records = []
            for _, row in gdf.iterrows():
                records.append(
                    Road(
                        linearid=row.get("LINEARID"),
                        fullname=row.get("FULLNAME"),
                        rttyp=row.get("RTTYP"),
                        mtfcc=row.get("MTFCC"),
                        geom=_to_multilinestring_wkb(row.geometry),
                    )
                )

            if records:
                session.add_all(records)
                session.flush()

            total += len(records)
            logger.info("TIGER roads state %s: %d records", fips, len(records))

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

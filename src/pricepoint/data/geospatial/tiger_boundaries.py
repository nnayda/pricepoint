"""Collect US Census TIGER/Line boundary shapefiles into PostGIS.

Downloads TIGER/Line shapefiles for census blocks, block groups, tracts,
school districts, counties, and county subdivisions.
"""

import io
import logging

import geopandas as gpd
import httpx
from geoalchemy2.shape import from_shape
from shapely.geometry import MultiPolygon
from sqlalchemy import delete

from pricepoint.config.settings import get_settings
from pricepoint.db import SessionLocal
from pricepoint.db.models import (
    TigerBlockGroup,
    TigerCensusBlock,
    TigerCounty,
    TigerCountySubdivision,
    TigerSchoolDistrict,
    TigerTract,
)

logger = logging.getLogger(__name__)


def _tiger_url(layer: str, fips: str, suffix: str) -> str:
    """Build a TIGER/Line shapefile download URL."""
    settings = get_settings()
    return (
        f"{settings.tiger_base_url}/TIGER{settings.tiger_year}"
        f"/{layer}/tl_{settings.tiger_year}_{fips}_{suffix}.zip"
    )


def _download_tiger_zip(url: str) -> bytes:
    """Download a TIGER/Line shapefile zip archive."""
    logger.info("Downloading TIGER shapefile: %s", url)
    response = httpx.get(url, timeout=300, follow_redirects=True)
    response.raise_for_status()
    return response.content


def _read_shapefile(zip_bytes: bytes) -> gpd.GeoDataFrame:
    """Read a shapefile from zip archive bytes into a GeoDataFrame."""
    return gpd.read_file(io.BytesIO(zip_bytes))


def _to_multipolygon_wkb(geom):
    """Convert a shapely geometry to a WKB MultiPolygon."""
    if geom.geom_type == "Polygon":
        geom = MultiPolygon([geom])
    return from_shape(geom, srid=4326)


def fetch_tiger_census_blocks() -> None:
    """Fetch TIGER/Line census block boundaries (TABBLOCK20) for the configured county."""
    settings = get_settings()
    url = _tiger_url("TABBLOCK20", settings.tiger_state_fips, "tabblock20")

    session = SessionLocal()
    try:
        session.execute(delete(TigerCensusBlock))
        session.commit()

        zip_bytes = _download_tiger_zip(url)
        gdf = _read_shapefile(zip_bytes)
        gdf = gdf[gdf["COUNTYFP20"] == settings.tiger_county_fips]

        records = []
        for _, row in gdf.iterrows():
            records.append(
                TigerCensusBlock(
                    statefp20=row.get("STATEFP20"),
                    countyfp20=row.get("COUNTYFP20"),
                    tractce20=row.get("TRACTCE20"),
                    blockce20=row.get("BLOCKCE20"),
                    geoid20=row.get("GEOID20"),
                    name20=row.get("NAME20"),
                    aland20=row.get("ALAND20"),
                    awater20=row.get("AWATER20"),
                    intptlat20=row.get("INTPTLAT20"),
                    intptlon20=row.get("INTPTLON20"),
                    funcstat20=row.get("FUNCSTAT20"),
                    mtfcc20=row.get("MTFCC20"),
                    ur20=row.get("UR20"),
                    uace20=row.get("UACE20"),
                    uatype20=row.get("UATYPE20"),
                    housing20=row.get("HOUSING20"),
                    pop20=row.get("POP20"),
                    geom=_to_multipolygon_wkb(row.geometry),
                )
            )

        if records:
            session.add_all(records)
            session.commit()

        logger.info("TIGER census blocks loaded: %d records", len(records))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def fetch_tiger_block_groups() -> None:
    """Fetch TIGER/Line block group boundaries (BG) for the configured county."""
    settings = get_settings()
    url = _tiger_url("BG", settings.tiger_state_fips, "bg")

    session = SessionLocal()
    try:
        session.execute(delete(TigerBlockGroup))
        session.commit()

        zip_bytes = _download_tiger_zip(url)
        gdf = _read_shapefile(zip_bytes)
        gdf = gdf[gdf["COUNTYFP"] == settings.tiger_county_fips]

        records = []
        for _, row in gdf.iterrows():
            records.append(
                TigerBlockGroup(
                    statefp=row.get("STATEFP"),
                    countyfp=row.get("COUNTYFP"),
                    tractce=row.get("TRACTCE"),
                    blkgrpce=row.get("BLKGRPCE"),
                    geoid=row.get("GEOID"),
                    namelsad=row.get("NAMELSAD"),
                    aland=row.get("ALAND"),
                    awater=row.get("AWATER"),
                    intptlat=row.get("INTPTLAT"),
                    intptlon=row.get("INTPTLON"),
                    funcstat=row.get("FUNCSTAT"),
                    mtfcc=row.get("MTFCC"),
                    geom=_to_multipolygon_wkb(row.geometry),
                )
            )

        if records:
            session.add_all(records)
            session.commit()

        logger.info("TIGER block groups loaded: %d records", len(records))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def fetch_tiger_tracts() -> None:
    """Fetch TIGER/Line census tract boundaries (TRACT) for the configured county."""
    settings = get_settings()
    url = _tiger_url("TRACT", settings.tiger_state_fips, "tract")

    session = SessionLocal()
    try:
        session.execute(delete(TigerTract))
        session.commit()

        zip_bytes = _download_tiger_zip(url)
        gdf = _read_shapefile(zip_bytes)
        gdf = gdf[gdf["COUNTYFP"] == settings.tiger_county_fips]

        records = []
        for _, row in gdf.iterrows():
            records.append(
                TigerTract(
                    statefp=row.get("STATEFP"),
                    countyfp=row.get("COUNTYFP"),
                    tractce=row.get("TRACTCE"),
                    geoid=row.get("GEOID"),
                    name=row.get("NAME"),
                    namelsad=row.get("NAMELSAD"),
                    aland=row.get("ALAND"),
                    awater=row.get("AWATER"),
                    intptlat=row.get("INTPTLAT"),
                    intptlon=row.get("INTPTLON"),
                    funcstat=row.get("FUNCSTAT"),
                    mtfcc=row.get("MTFCC"),
                    geom=_to_multipolygon_wkb(row.geometry),
                )
            )

        if records:
            session.add_all(records)
            session.commit()

        logger.info("TIGER tracts loaded: %d records", len(records))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def fetch_tiger_school_districts() -> None:
    """Fetch TIGER/Line school district boundaries (ELSD/SCSD/UNSD) for the configured state."""
    settings = get_settings()

    sub_layers = [
        ("ELSD", "elsd", "elementary"),
        ("SCSD", "scsd", "secondary"),
        ("UNSD", "unsd", "unified"),
    ]

    session = SessionLocal()
    try:
        session.execute(delete(TigerSchoolDistrict))
        session.commit()

        total = 0
        for layer, suffix, district_type in sub_layers:
            url = _tiger_url(layer, settings.tiger_state_fips, suffix)
            try:
                zip_bytes = _download_tiger_zip(url)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    logger.warning(
                        "TIGER %s shapefile not found (404), skipping %s districts",
                        layer,
                        district_type,
                    )
                    continue
                raise

            gdf = _read_shapefile(zip_bytes)

            records = []
            for _, row in gdf.iterrows():
                records.append(
                    TigerSchoolDistrict(
                        district_type=district_type,
                        statefp=row.get("STATEFP"),
                        geoid=row.get("GEOID"),
                        name=row.get("NAME"),
                        lsad=row.get("LSAD"),
                        lograde=row.get("LOGRADE"),
                        higrade=row.get("HIGRADE"),
                        aland=row.get("ALAND"),
                        awater=row.get("AWATER"),
                        intptlat=row.get("INTPTLAT"),
                        intptlon=row.get("INTPTLON"),
                        funcstat=row.get("FUNCSTAT"),
                        mtfcc=row.get("MTFCC"),
                        sdtyp=row.get("SDTYP"),
                        geom=_to_multipolygon_wkb(row.geometry),
                    )
                )

            if records:
                session.add_all(records)
                session.commit()

            total += len(records)
            logger.info("TIGER %s school districts loaded: %d records", district_type, len(records))

        logger.info("TIGER school districts total: %d records", total)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def fetch_tiger_counties() -> None:
    """Fetch TIGER/Line county boundaries (COUNTY) from the national file."""
    settings = get_settings()
    url = _tiger_url("COUNTY", "us", "county")

    session = SessionLocal()
    try:
        session.execute(delete(TigerCounty))
        session.commit()

        zip_bytes = _download_tiger_zip(url)
        gdf = _read_shapefile(zip_bytes)
        gdf = gdf[
            (gdf["STATEFP"] == settings.tiger_state_fips)
            & (gdf["COUNTYFP"] == settings.tiger_county_fips)
        ]

        records = []
        for _, row in gdf.iterrows():
            records.append(
                TigerCounty(
                    statefp=row.get("STATEFP"),
                    countyfp=row.get("COUNTYFP"),
                    countyns=row.get("COUNTYNS"),
                    geoid=row.get("GEOID"),
                    name=row.get("NAME"),
                    namelsad=row.get("NAMELSAD"),
                    lsad=row.get("LSAD"),
                    classfp=row.get("CLASSFP"),
                    aland=row.get("ALAND"),
                    awater=row.get("AWATER"),
                    intptlat=row.get("INTPTLAT"),
                    intptlon=row.get("INTPTLON"),
                    funcstat=row.get("FUNCSTAT"),
                    mtfcc=row.get("MTFCC"),
                    csafp=row.get("CSAFP"),
                    cbsafp=row.get("CBSAFP"),
                    metdivfp=row.get("METDIVFP"),
                    geom=_to_multipolygon_wkb(row.geometry),
                )
            )

        if records:
            session.add_all(records)
            session.commit()

        logger.info("TIGER counties loaded: %d records", len(records))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def fetch_tiger_county_subdivisions() -> None:
    """Fetch TIGER/Line county subdivision boundaries (COUSUB) for the configured county."""
    settings = get_settings()
    url = _tiger_url("COUSUB", settings.tiger_state_fips, "cousub")

    session = SessionLocal()
    try:
        session.execute(delete(TigerCountySubdivision))
        session.commit()

        zip_bytes = _download_tiger_zip(url)
        gdf = _read_shapefile(zip_bytes)
        gdf = gdf[gdf["COUNTYFP"] == settings.tiger_county_fips]

        records = []
        for _, row in gdf.iterrows():
            records.append(
                TigerCountySubdivision(
                    statefp=row.get("STATEFP"),
                    countyfp=row.get("COUNTYFP"),
                    cousubfp=row.get("COUSUBFP"),
                    cousubns=row.get("COUSUBNS"),
                    geoid=row.get("GEOID"),
                    name=row.get("NAME"),
                    namelsad=row.get("NAMELSAD"),
                    lsad=row.get("LSAD"),
                    classfp=row.get("CLASSFP"),
                    aland=row.get("ALAND"),
                    awater=row.get("AWATER"),
                    intptlat=row.get("INTPTLAT"),
                    intptlon=row.get("INTPTLON"),
                    funcstat=row.get("FUNCSTAT"),
                    mtfcc=row.get("MTFCC"),
                    cnectafp=row.get("CNECTAFP"),
                    nectafp=row.get("NECTAFP"),
                    geom=_to_multipolygon_wkb(row.geometry),
                )
            )

        if records:
            session.add_all(records)
            session.commit()

        logger.info("TIGER county subdivisions loaded: %d records", len(records))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

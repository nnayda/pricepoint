"""Collect US Census TIGER/Line boundary shapefiles into PostGIS.

Downloads TIGER/Line shapefiles for census blocks, block groups, tracts,
school districts, counties, and county subdivisions for all US states.
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
    Block,
    BlockGroup,
    County,
    SchoolDistrict,
    Township,
    Tract,
)

logger = logging.getLogger(__name__)

# All 50 US states + DC FIPS codes.
US_STATE_FIPS = [
    "01",
    "02",
    "04",
    "05",
    "06",
    "08",
    "09",
    "10",
    "11",
    "12",
    "13",
    "15",
    "16",
    "17",
    "18",
    "19",
    "20",
    "21",
    "22",
    "23",
    "24",
    "25",
    "26",
    "27",
    "28",
    "29",
    "30",
    "31",
    "32",
    "33",
    "34",
    "35",
    "36",
    "37",
    "38",
    "39",
    "40",
    "41",
    "42",
    "44",
    "45",
    "46",
    "47",
    "48",
    "49",
    "50",
    "51",
    "53",
    "54",
    "55",
    "56",
]


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


def fetch_tiger_census_blocks(state_fips: str | None = None) -> None:
    """Fetch TIGER/Line census block boundaries (TABBLOCK20) for all US states.

    Args:
        state_fips: If provided, fetch only this state. Otherwise fetch all states.
    """
    fips_list = [state_fips] if state_fips else US_STATE_FIPS

    session = SessionLocal()
    try:
        session.execute(delete(Block))
        session.commit()

        total = 0
        for fips in fips_list:
            url = _tiger_url("TABBLOCK20", fips, "tabblock20")
            try:
                zip_bytes = _download_tiger_zip(url)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    logger.warning("TIGER TABBLOCK20 not found for state %s, skipping", fips)
                    continue
                raise

            gdf = _read_shapefile(zip_bytes)

            records = []
            for _, row in gdf.iterrows():
                records.append(
                    Block(
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

            total += len(records)
            logger.info("TIGER census blocks state %s: %d records", fips, len(records))

        logger.info("TIGER census blocks total: %d records", total)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def fetch_tiger_block_groups(state_fips: str | None = None) -> None:
    """Fetch TIGER/Line block group boundaries (BG) for all US states.

    Args:
        state_fips: If provided, fetch only this state. Otherwise fetch all states.
    """
    fips_list = [state_fips] if state_fips else US_STATE_FIPS

    session = SessionLocal()
    try:
        session.execute(delete(BlockGroup))
        session.commit()

        total = 0
        for fips in fips_list:
            url = _tiger_url("BG", fips, "bg")
            try:
                zip_bytes = _download_tiger_zip(url)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    logger.warning("TIGER BG not found for state %s, skipping", fips)
                    continue
                raise

            gdf = _read_shapefile(zip_bytes)

            records = []
            for _, row in gdf.iterrows():
                records.append(
                    BlockGroup(
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

            total += len(records)
            logger.info("TIGER block groups state %s: %d records", fips, len(records))

        logger.info("TIGER block groups total: %d records", total)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def fetch_tiger_tracts(state_fips: str | None = None) -> None:
    """Fetch TIGER/Line census tract boundaries (TRACT) for all US states.

    Args:
        state_fips: If provided, fetch only this state. Otherwise fetch all states.
    """
    fips_list = [state_fips] if state_fips else US_STATE_FIPS

    session = SessionLocal()
    try:
        session.execute(delete(Tract))
        session.commit()

        total = 0
        for fips in fips_list:
            url = _tiger_url("TRACT", fips, "tract")
            try:
                zip_bytes = _download_tiger_zip(url)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    logger.warning("TIGER TRACT not found for state %s, skipping", fips)
                    continue
                raise

            gdf = _read_shapefile(zip_bytes)

            records = []
            for _, row in gdf.iterrows():
                records.append(
                    Tract(
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

            total += len(records)
            logger.info("TIGER tracts state %s: %d records", fips, len(records))

        logger.info("TIGER tracts total: %d records", total)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def fetch_tiger_school_districts(state_fips: str | None = None) -> None:
    """Fetch TIGER/Line school district boundaries (ELSD/SCSD/UNSD) for all US states.

    Args:
        state_fips: If provided, fetch only this state. Otherwise fetch all states.
    """
    fips_list = [state_fips] if state_fips else US_STATE_FIPS

    sub_layers = [
        ("ELSD", "elsd", "elementary"),
        ("SCSD", "scsd", "secondary"),
        ("UNSD", "unsd", "unified"),
    ]

    session = SessionLocal()
    try:
        session.execute(delete(SchoolDistrict))
        session.commit()

        total = 0
        for fips in fips_list:
            for layer, suffix, district_type in sub_layers:
                url = _tiger_url(layer, fips, suffix)
                try:
                    zip_bytes = _download_tiger_zip(url)
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 404:
                        logger.warning(
                            "TIGER %s shapefile not found for state %s, skipping %s districts",
                            layer,
                            fips,
                            district_type,
                        )
                        continue
                    raise

                gdf = _read_shapefile(zip_bytes)

                records = []
                for _, row in gdf.iterrows():
                    records.append(
                        SchoolDistrict(
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
                logger.info(
                    "TIGER %s school districts state %s: %d records",
                    district_type,
                    fips,
                    len(records),
                )

            logger.info("TIGER school districts state %s done", fips)

        logger.info("TIGER school districts total: %d records", total)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def fetch_tiger_counties() -> None:
    """Fetch TIGER/Line county boundaries (COUNTY) from the national file."""
    url = _tiger_url("COUNTY", "us", "county")

    session = SessionLocal()
    try:
        session.execute(delete(County))
        session.commit()

        zip_bytes = _download_tiger_zip(url)
        gdf = _read_shapefile(zip_bytes)

        records = []
        for _, row in gdf.iterrows():
            records.append(
                County(
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


def fetch_tiger_county_subdivisions(state_fips: str | None = None) -> None:
    """Fetch TIGER/Line county subdivision boundaries (COUSUB) for all US states.

    Args:
        state_fips: If provided, fetch only this state. Otherwise fetch all states.
    """
    fips_list = [state_fips] if state_fips else US_STATE_FIPS

    session = SessionLocal()
    try:
        session.execute(delete(Township))
        session.commit()

        total = 0
        for fips in fips_list:
            url = _tiger_url("COUSUB", fips, "cousub")
            try:
                zip_bytes = _download_tiger_zip(url)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    logger.warning("TIGER COUSUB not found for state %s, skipping", fips)
                    continue
                raise

            gdf = _read_shapefile(zip_bytes)

            records = []
            for _, row in gdf.iterrows():
                records.append(
                    Township(
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

            total += len(records)
            logger.info("TIGER county subdivisions state %s: %d records", fips, len(records))

        logger.info("TIGER county subdivisions total: %d records", total)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

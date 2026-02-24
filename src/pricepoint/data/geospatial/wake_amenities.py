"""Collect Wake County amenity locations (farmers markets, libraries, hospitals).

Downloads point features from various ArcGIS endpoints and loads them into PostGIS.
"""

import logging

from pricepoint.config.settings import get_settings
from pricepoint.data.geospatial.arcgis_client import (
    build_point_wkb,
    fetch_arcgis_dataset,
    parse_arcgis_timestamp,
    verify_arcgis_dataset,
)
from pricepoint.db.models import WakeFarmersMarket, WakeHospital, WakeLibrary

logger = logging.getLogger(__name__)


# -- Farmers Markets ----------------------------------------------------------


def _map_farmers_market(feature: dict) -> WakeFarmersMarket:
    """Map an ArcGIS feature to a WakeFarmersMarket model instance."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")
    return WakeFarmersMarket(
        objectid=attrs.get("OBJECTID"),
        name=attrs.get("NAME"),
        location_desc=attrs.get("LOCATION"),
        organization=attrs.get("ORGANIZATI"),
        active_day=attrs.get("ACTIVEDAY"),
        months=attrs.get("MONTHS"),
        hours=attrs.get("HOURS"),
        website=attrs.get("WEBSITE"),
        phone=attrs.get("PHONE"),
        geom=build_point_wkb(geometry),
    )


def fetch_farmers_markets() -> None:
    """Fetch all farmers market locations and load into PostGIS."""
    settings = get_settings()
    fetch_arcgis_dataset(
        base_url=settings.wake_farmers_markets_base_url,
        model_class=WakeFarmersMarket,
        mapper=_map_farmers_market,
        dataset_name="wake_farmers_markets",
    )


def verify_farmers_markets() -> None:
    """Verify farmers market records were loaded."""
    verify_arcgis_dataset(WakeFarmersMarket, "wake_farmers_markets")


# -- Libraries ----------------------------------------------------------------


def _map_library(feature: dict) -> WakeLibrary:
    """Map an ArcGIS feature to a WakeLibrary model instance."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")
    return WakeLibrary(
        objectid=attrs.get("OBJECTID"),
        name=attrs.get("NAME"),
        address=attrs.get("FAC_ADDRESS"),
        city=attrs.get("CITY"),
        code=attrs.get("CODE"),
        label=attrs.get("LABEL"),
        status=attrs.get("STATUS"),
        facility_type=attrs.get("TYPE"),
        hours_mt=attrs.get("M_T"),
        hours_fri=attrs.get("FRI"),
        hours_sat=attrs.get("SAT"),
        hours_sun=attrs.get("SUN"),
        geom=build_point_wkb(geometry),
    )


def fetch_libraries() -> None:
    """Fetch all library locations and load into PostGIS."""
    settings = get_settings()
    fetch_arcgis_dataset(
        base_url=settings.wake_libraries_base_url,
        model_class=WakeLibrary,
        mapper=_map_library,
        dataset_name="wake_libraries",
        page_size=1000,
    )


def verify_libraries() -> None:
    """Verify library records were loaded."""
    verify_arcgis_dataset(WakeLibrary, "wake_libraries")


# -- Hospitals ----------------------------------------------------------------


def _map_hospital(feature: dict) -> WakeHospital:
    """Map an ArcGIS feature to a WakeHospital model instance."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")
    return WakeHospital(
        objectid=attrs.get("OBJECTID"),
        facility=attrs.get("FACILITY") or attrs.get("Facility"),
        address=attrs.get("ADDRESS") or attrs.get("Address"),
        city=attrs.get("CITY") or attrs.get("City"),
        acute_care=attrs.get("ACUTE_CARE") or attrs.get("Acute_Care"),
        url=attrs.get("URL") or attrs.get("Url"),
        telephone=attrs.get("TELEPHONE") or attrs.get("Telephone"),
        gis_edit_date=parse_arcgis_timestamp(attrs.get("GIS_EDT_DT")),
        geom=build_point_wkb(geometry),
    )


def fetch_hospitals() -> None:
    """Fetch all hospital locations and load into PostGIS."""
    settings = get_settings()
    fetch_arcgis_dataset(
        base_url=settings.wake_hospitals_base_url,
        model_class=WakeHospital,
        mapper=_map_hospital,
        dataset_name="wake_hospitals",
    )


def verify_hospitals() -> None:
    """Verify hospital records were loaded."""
    verify_arcgis_dataset(WakeHospital, "wake_hospitals")

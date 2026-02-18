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
        name=attrs.get("Name"),
        location_desc=attrs.get("Location_Desc") or attrs.get("Location_desc"),
        organization=attrs.get("Organization"),
        active_day=attrs.get("Active_Day") or attrs.get("Active_day"),
        months=attrs.get("Months"),
        hours=attrs.get("Hours"),
        website=attrs.get("Website"),
        phone=attrs.get("Phone"),
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
        name=attrs.get("NAME") or attrs.get("Name"),
        address=attrs.get("ADDRESS") or attrs.get("Address"),
        city=attrs.get("CITY") or attrs.get("City"),
        code=attrs.get("CODE") or attrs.get("Code"),
        label=attrs.get("LABEL") or attrs.get("Label"),
        status=attrs.get("STATUS") or attrs.get("Status"),
        facility_type=attrs.get("FACILITY_TYPE") or attrs.get("Facility_Type"),
        hours_mt=attrs.get("HOURS_MT") or attrs.get("Hours_MT"),
        hours_fri=attrs.get("HOURS_FRI") or attrs.get("Hours_Fri"),
        hours_sat=attrs.get("HOURS_SAT") or attrs.get("Hours_Sat"),
        hours_sun=attrs.get("HOURS_SUN") or attrs.get("Hours_Sun"),
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
        gis_edit_date=parse_arcgis_timestamp(attrs.get("GIS_EDIT_DATE")),
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

"""Collect greenway trail data from Wake County, Raleigh, and Cary.

Downloads polyline features from ArcGIS endpoints and loads them into PostGIS.
"""

import logging

from pricepoint.config.settings import get_settings
from pricepoint.data.geospatial.arcgis_client import (
    build_multilinestring_wkb,
    fetch_arcgis_dataset,
    parse_arcgis_timestamp,
    verify_arcgis_dataset,
)
from pricepoint.db.models import CaryGreenway, RaleighGreenway, WakeGreenway

logger = logging.getLogger(__name__)


# -- Wake Greenways -----------------------------------------------------------


def _map_wake_greenway(feature: dict) -> WakeGreenway:
    """Map an ArcGIS feature to a WakeGreenway model instance."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")
    paths = geometry.get("paths") if geometry else None
    return WakeGreenway(
        objectid=attrs.get("OBJECTID"),
        trail_name=attrs.get("TRAIL_NAME"),
        corridor_name=attrs.get("CORRIDOR_NAME"),
        owner=attrs.get("OWNER"),
        trail_status=attrs.get("TRAIL_STATUS"),
        trail_surface=attrs.get("TRAIL_SURFACE"),
        trail_class=attrs.get("TRAIL_CLASS"),
        length=attrs.get("LENGTH"),
        width=attrs.get("WIDTH"),
        open_date=parse_arcgis_timestamp(attrs.get("OPEN_DATE")),
        public_access=attrs.get("PUBLIC_ACCESS"),
        accessibility_status=attrs.get("ACCESSIBILITY_STATUS"),
        trail_condition=attrs.get("TRAIL_CONDITION"),
        slope=attrs.get("SLOPE"),
        subsegment_name=attrs.get("SUBSEGMENT_NAME"),
        geom=build_multilinestring_wkb(paths),
    )


def fetch_wake_greenways() -> None:
    """Fetch all Wake County greenway trails and load into PostGIS."""
    settings = get_settings()
    fetch_arcgis_dataset(
        base_url=settings.wake_greenways_base_url,
        model_class=WakeGreenway,
        mapper=_map_wake_greenway,
        dataset_name="wake_greenways",
    )


def verify_wake_greenways() -> None:
    """Verify Wake County greenway records were loaded."""
    verify_arcgis_dataset(WakeGreenway, "wake_greenways")


# -- Raleigh Greenways --------------------------------------------------------


def _map_raleigh_greenway(feature: dict) -> RaleighGreenway:
    """Map an ArcGIS feature to a RaleighGreenway model instance."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")
    paths = geometry.get("paths") if geometry else None
    return RaleighGreenway(
        objectid=attrs.get("OBJECTID"),
        trail_name=attrs.get("TRAIL_NAME"),
        greenway_type=attrs.get("TYPE"),
        location_desc=attrs.get("LOCATION"),
        status=attrs.get("STATUS"),
        material=attrs.get("MATERIAL"),
        map_miles=attrs.get("MAP_MILES"),
        width_ft=attrs.get("WIDTH_FT"),
        owner=attrs.get("OWNER"),
        ada=attrs.get("ADA"),
        gw_status=attrs.get("GWSTATUS"),
        geom=build_multilinestring_wkb(paths),
    )


def fetch_raleigh_greenways() -> None:
    """Fetch all Raleigh greenway trails and load into PostGIS."""
    settings = get_settings()
    fetch_arcgis_dataset(
        base_url=settings.raleigh_greenways_base_url,
        model_class=RaleighGreenway,
        mapper=_map_raleigh_greenway,
        dataset_name="raleigh_greenways",
    )


def verify_raleigh_greenways() -> None:
    """Verify Raleigh greenway records were loaded."""
    verify_arcgis_dataset(RaleighGreenway, "raleigh_greenways")


# -- Cary Greenways -----------------------------------------------------------


def _map_cary_greenway(feature: dict) -> CaryGreenway:
    """Map an ArcGIS feature to a CaryGreenway model instance."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")
    paths = geometry.get("paths") if geometry else None
    return CaryGreenway(
        objectid=attrs.get("OBJECTID"),
        name=attrs.get("NAME"),
        segment=attrs.get("SEGMENT"),
        length=attrs.get("LENGTH"),
        width=attrs.get("WIDTH"),
        trail_type=attrs.get("TRAILTYPE"),
        surface_type=attrs.get("SURFTYPE"),
        status=attrs.get("STATUS"),
        install_date=parse_arcgis_timestamp(attrs.get("INSTALLDATE")),
        open_to_public=attrs.get("OPENTOPUBLIC"),
        project_name=attrs.get("PROJNAME"),
        project_number=attrs.get("PROJNUM"),
        notes=attrs.get("NOTES"),
        loop_trail=attrs.get("LOOPTRAIL"),
        loop_name=attrs.get("LOOPNAME"),
        official_cary_greenway_miles=attrs.get("CARYGWAYMICOUNT"),
        geom=build_multilinestring_wkb(paths),
    )


def fetch_cary_greenways() -> None:
    """Fetch all Cary greenway trails and load into PostGIS."""
    settings = get_settings()
    fetch_arcgis_dataset(
        base_url=settings.cary_greenways_base_url,
        model_class=CaryGreenway,
        mapper=_map_cary_greenway,
        dataset_name="cary_greenways",
    )


def verify_cary_greenways() -> None:
    """Verify Cary greenway records were loaded."""
    verify_arcgis_dataset(CaryGreenway, "cary_greenways")

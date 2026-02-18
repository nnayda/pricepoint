"""Collect Wake County transportation and utility infrastructure.

Downloads polyline features (railroads, major roads, highways, utility easements)
from ArcGIS endpoints and loads them into PostGIS.
"""

import logging

from pricepoint.config.settings import get_settings
from pricepoint.data.geospatial.arcgis_client import (
    build_multilinestring_wkb,
    fetch_arcgis_dataset,
    verify_arcgis_dataset,
)
from pricepoint.db.models import WakeHighway, WakeMajorRoad, WakeRailroad, WakeUtilityEasement

logger = logging.getLogger(__name__)


# -- Railroads ----------------------------------------------------------------


def _map_railroad(feature: dict) -> WakeRailroad:
    """Map an ArcGIS feature to a WakeRailroad model instance."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")
    paths = geometry.get("paths") if geometry else None
    return WakeRailroad(
        objectid=attrs.get("OBJECTID"),
        branch_or=attrs.get("BRANCH_OR"),
        track_type=attrs.get("TRACK_TYPE"),
        track_owner=attrs.get("TRACK_OWNER"),
        shape_length=attrs.get("Shape__Length") or attrs.get("SHAPE__Length"),
        geom=build_multilinestring_wkb(paths),
    )


def fetch_railroads() -> None:
    """Fetch all Wake County railroad features and load into PostGIS."""
    settings = get_settings()
    fetch_arcgis_dataset(
        base_url=settings.wake_railroads_base_url,
        model_class=WakeRailroad,
        mapper=_map_railroad,
        dataset_name="wake_railroads",
    )


def verify_railroads() -> None:
    """Verify railroad records were loaded."""
    verify_arcgis_dataset(WakeRailroad, "wake_railroads")


# -- Major Roads --------------------------------------------------------------


def _map_major_road(feature: dict) -> WakeMajorRoad:
    """Map an ArcGIS feature to a WakeMajorRoad model instance."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")
    paths = geometry.get("paths") if geometry else None
    return WakeMajorRoad(
        objectid=attrs.get("OBJECTID"),
        street_name=attrs.get("STREET_NAME"),
        street_type=attrs.get("STREET_TYPE"),
        dir_prefix=attrs.get("DIR_PREFIX"),
        dir_suffix=attrs.get("DIR_SUFFIX"),
        state_road=attrs.get("STATE_ROAD"),
        carto_name=attrs.get("CARTO_NAME"),
        corporation=attrs.get("CORPORATION"),
        class_name=attrs.get("CLASS_NAME"),
        label_name=attrs.get("LABEL_NAME"),
        geom=build_multilinestring_wkb(paths),
    )


def fetch_major_roads() -> None:
    """Fetch all Wake County major road features and load into PostGIS."""
    settings = get_settings()
    fetch_arcgis_dataset(
        base_url=settings.wake_major_roads_base_url,
        model_class=WakeMajorRoad,
        mapper=_map_major_road,
        dataset_name="wake_major_roads",
    )


def verify_major_roads() -> None:
    """Verify major road records were loaded."""
    verify_arcgis_dataset(WakeMajorRoad, "wake_major_roads")


# -- Highways -----------------------------------------------------------------


def _map_highway(feature: dict) -> WakeHighway:
    """Map an ArcGIS feature to a WakeHighway model instance."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")
    paths = geometry.get("paths") if geometry else None
    return WakeHighway(
        objectid=attrs.get("OBJECTID"),
        street_name=attrs.get("STREET_NAME"),
        street_type=attrs.get("STREET_TYPE"),
        dir_prefix=attrs.get("DIR_PREFIX"),
        dir_suffix=attrs.get("DIR_SUFFIX"),
        from_left=attrs.get("FROM_LEFT"),
        to_left=attrs.get("TO_LEFT"),
        from_right=attrs.get("FROM_RIGHT"),
        to_right=attrs.get("TO_RIGHT"),
        state_road=attrs.get("STATE_ROAD"),
        carto_name=attrs.get("CARTO_NAME"),
        corporation=attrs.get("CORPORATION"),
        class_name=attrs.get("CLASS_NAME"),
        label_name=attrs.get("LABEL_NAME"),
        geom=build_multilinestring_wkb(paths),
    )


def fetch_highways() -> None:
    """Fetch all Wake County highway features and load into PostGIS."""
    settings = get_settings()
    fetch_arcgis_dataset(
        base_url=settings.wake_highways_base_url,
        model_class=WakeHighway,
        mapper=_map_highway,
        dataset_name="wake_highways",
    )


def verify_highways() -> None:
    """Verify highway records were loaded."""
    verify_arcgis_dataset(WakeHighway, "wake_highways")


# -- Utility Easements --------------------------------------------------------


def _map_utility_easement(feature: dict) -> WakeUtilityEasement:
    """Map an ArcGIS feature to a WakeUtilityEasement model instance."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")
    paths = geometry.get("paths") if geometry else None
    return WakeUtilityEasement(
        objectid=attrs.get("OBJECTID"),
        length=attrs.get("LENGTH"),
        ftr_code=attrs.get("FTR_CODE"),
        status=attrs.get("STATUS"),
        geom=build_multilinestring_wkb(paths),
    )


def fetch_utility_easements() -> None:
    """Fetch all Wake County utility easement features and load into PostGIS."""
    settings = get_settings()
    fetch_arcgis_dataset(
        base_url=settings.wake_utility_easements_base_url,
        model_class=WakeUtilityEasement,
        mapper=_map_utility_easement,
        dataset_name="wake_utility_easements",
    )


def verify_utility_easements() -> None:
    """Verify utility easement records were loaded."""
    verify_arcgis_dataset(WakeUtilityEasement, "wake_utility_easements")

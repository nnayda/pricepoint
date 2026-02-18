"""Collect park boundaries from Wake County, Raleigh, and Cary.

Downloads park features from ArcGIS endpoints and loads them into PostGIS.
Wake and Raleigh parks are polygons; Cary parks are points with amenity details.
"""

import logging

from pricepoint.config.settings import get_settings
from pricepoint.data.geospatial.arcgis_client import (
    build_multipolygon_wkb,
    build_point_wkb,
    fetch_arcgis_dataset,
    parse_arcgis_timestamp,
    verify_arcgis_dataset,
)
from pricepoint.db.models import CaryPark, RaleighPark, WakePark

logger = logging.getLogger(__name__)


# -- Wake Parks ---------------------------------------------------------------


def _map_wake_park(feature: dict) -> WakePark:
    """Map an ArcGIS feature to a WakePark model instance."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")
    rings = geometry.get("rings") if geometry else None
    return WakePark(
        objectid=attrs.get("OBJECTID"),
        name=attrs.get("NAME"),
        acres=attrs.get("ACRES"),
        owner=attrs.get("OWNER"),
        jurisdiction=attrs.get("JURISDICTION"),
        park_type=attrs.get("PARK_TYPE"),
        manager=attrs.get("MANAGER"),
        comments=attrs.get("COMMENTS"),
        corridor=attrs.get("CORRIDOR"),
        os_number=attrs.get("OS_NUMBER"),
        created_date=parse_arcgis_timestamp(attrs.get("created_date")),
        last_edited_date=parse_arcgis_timestamp(attrs.get("last_edited_date")),
        geom=build_multipolygon_wkb(rings),
    )


def fetch_wake_parks() -> None:
    """Fetch all Wake County park boundaries and load into PostGIS."""
    settings = get_settings()
    fetch_arcgis_dataset(
        base_url=settings.wake_parks_base_url,
        model_class=WakePark,
        mapper=_map_wake_park,
        dataset_name="wake_parks",
    )


def verify_wake_parks() -> None:
    """Verify Wake County park records were loaded."""
    verify_arcgis_dataset(WakePark, "wake_parks")


# -- Raleigh Parks ------------------------------------------------------------


def _map_raleigh_park(feature: dict) -> RaleighPark:
    """Map an ArcGIS feature to a RaleighPark model instance."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")
    rings = geometry.get("rings") if geometry else None
    return RaleighPark(
        objectid=attrs.get("OBJECTID"),
        name=attrs.get("NAME"),
        park_type=attrs.get("PARK_TYPE"),
        developed=attrs.get("DEVELOPED"),
        map_acres=attrs.get("MAP_ACRES"),
        address=attrs.get("ADDRESS"),
        zip_code=attrs.get("ZIP_CODE"),
        park_id=attrs.get("PARK_ID"),
        initial_acquisition_date=parse_arcgis_timestamp(attrs.get("INITIAL_ACQUISITION_DATE")),
        geom=build_multipolygon_wkb(rings),
    )


def fetch_raleigh_parks() -> None:
    """Fetch all Raleigh park boundaries and load into PostGIS."""
    settings = get_settings()
    fetch_arcgis_dataset(
        base_url=settings.raleigh_parks_base_url,
        model_class=RaleighPark,
        mapper=_map_raleigh_park,
        dataset_name="raleigh_parks",
    )


def verify_raleigh_parks() -> None:
    """Verify Raleigh park records were loaded."""
    verify_arcgis_dataset(RaleighPark, "raleigh_parks")


# -- Cary Parks ---------------------------------------------------------------


def _map_cary_park(feature: dict) -> CaryPark:
    """Map an ArcGIS feature to a CaryPark model instance."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")
    return CaryPark(
        objectid=attrs.get("OBJECTID"),
        name=attrs.get("NAME"),
        facility_id=attrs.get("FACILITY_ID"),
        address=attrs.get("ADDRESS"),
        park_area=attrs.get("PARK_AREA"),
        park_url=attrs.get("PARK_URL"),
        num_parking=attrs.get("NUM_PARKING"),
        restroom=attrs.get("RESTROOM"),
        ada_compliant=attrs.get("ADA_COMPLIANT"),
        camping=attrs.get("CAMPING"),
        swimming=attrs.get("SWIMMING"),
        hiking=attrs.get("HIKING"),
        fishing=attrs.get("FISHING"),
        picnic=attrs.get("PICNIC"),
        boating=attrs.get("BOATING"),
        road_cycle=attrs.get("ROAD_CYCLE"),
        mtb_cycle=attrs.get("MTB_CYCLE"),
        playground=attrs.get("PLAYGROUND"),
        golf=attrs.get("GOLF"),
        soccer=attrs.get("SOCCER"),
        baseball=attrs.get("BASEBALL"),
        basketball=attrs.get("BASKETBALL"),
        skatepark=attrs.get("SKATEPARK"),
        tennis_court=attrs.get("TENNIS_COURT"),
        volleyball=attrs.get("VOLLEYBALL"),
        fitness_trail=attrs.get("FITNESS_TRAIL"),
        nature_trail=attrs.get("NATURE_TRAIL"),
        trailhead=attrs.get("TRAILHEAD"),
        open_space=attrs.get("OPEN_SPACE"),
        lake=attrs.get("LAKE"),
        amphitheater=attrs.get("AMPHITHEATER"),
        dog_park=attrs.get("DOG_PARK"),
        disc_golf=attrs.get("DISC_GOLF"),
        climbing_rocks=attrs.get("CLIMBING_ROCKS"),
        climbing_ropes=attrs.get("CLIMBING_ROPES"),
        batting_cages=attrs.get("BATTING_CAGES"),
        geom=build_point_wkb(geometry),
    )


def fetch_cary_parks() -> None:
    """Fetch all Cary park locations and load into PostGIS."""
    settings = get_settings()
    fetch_arcgis_dataset(
        base_url=settings.cary_parks_base_url,
        model_class=CaryPark,
        mapper=_map_cary_park,
        dataset_name="cary_parks",
    )


def verify_cary_parks() -> None:
    """Verify Cary park records were loaded."""
    verify_arcgis_dataset(CaryPark, "cary_parks")

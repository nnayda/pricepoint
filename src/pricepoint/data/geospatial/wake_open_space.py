"""Collect Wake County open space boundaries from ArcGIS MapServer.

Downloads open space features and loads them into PostGIS as staging records.
"""

import logging

from pricepoint.config.settings import get_settings
from pricepoint.data.geospatial.arcgis_client import (
    build_multipolygon_wkb,
    fetch_arcgis_dataset,
    parse_arcgis_timestamp,
    verify_arcgis_dataset,
)
from pricepoint.db.models import StagingWakeOpenSpace

logger = logging.getLogger(__name__)


def _map_wake_open_space(feature: dict) -> StagingWakeOpenSpace:
    """Map an ArcGIS feature to a StagingWakeOpenSpace model instance."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")
    rings = geometry.get("rings") if geometry else None
    return StagingWakeOpenSpace(
        objectid=attrs.get("OBJECTID"),
        name=attrs.get("NAME"),
        acres=attrs.get("ACRES"),
        owner=attrs.get("OWNER"),
        jurisdiction=attrs.get("JURISDICTION"),
        type=attrs.get("TYPE"),
        manager=attrs.get("MANAGER"),
        comments=attrs.get("COMMENTS"),
        bldgcode=attrs.get("BLDGCODE"),
        corridor=attrs.get("CORRIDOR"),
        os_number=attrs.get("OS_NUMBER"),
        created_date=parse_arcgis_timestamp(attrs.get("created_date")),
        last_edited_date=parse_arcgis_timestamp(attrs.get("last_edited_date")),
        geom=build_multipolygon_wkb(rings),
    )


def fetch_wake_open_space() -> None:
    """Fetch all Wake County open space boundaries and load into PostGIS."""
    settings = get_settings()
    fetch_arcgis_dataset(
        base_url=settings.wake_open_space_base_url,
        model_class=StagingWakeOpenSpace,
        mapper=_map_wake_open_space,
        dataset_name="wake_open_space",
    )


def verify_wake_open_space() -> None:
    """Verify Wake County open space records were loaded."""
    verify_arcgis_dataset(StagingWakeOpenSpace, "wake_open_space")

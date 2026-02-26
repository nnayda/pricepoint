"""Collect HIFLD North American Rail Network lines from ArcGIS FeatureServer.

Downloads railroad line geometries for the entire US and loads them into the
railroads table. Uses the shared arcgis_client truncate-and-reload pattern.
"""

from __future__ import annotations

import logging

from pricepoint.config.settings import get_settings
from pricepoint.data.geospatial.arcgis_client import (
    build_multilinestring_wkb,
    fetch_arcgis_dataset,
    verify_arcgis_dataset,
)
from pricepoint.db.models import Railroad

logger = logging.getLogger(__name__)


def _map_railroad(feature: dict) -> Railroad:
    """Map an ArcGIS feature to a Railroad model instance."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")
    paths = geometry.get("paths") if geometry else None

    tracks_raw = attrs.get("TRACKS")
    tracks = int(tracks_raw) if tracks_raw is not None else None

    miles_raw = attrs.get("MILES")
    miles = float(miles_raw) if miles_raw is not None else None

    return Railroad(
        fraarcid=attrs.get("FRAARCID"),
        rrowner1=attrs.get("RROWNER1"),
        rrowner2=attrs.get("RROWNER2"),
        rrowner3=attrs.get("RROWNER3"),
        stateab=attrs.get("STATEAB"),
        cntyfips=attrs.get("CNTYFIPS"),
        subdivision=attrs.get("SUBDIVISIO") or attrs.get("SUBDIVISION"),
        branch=attrs.get("BRANCH"),
        passngr=attrs.get("PASSNGR"),
        tracks=tracks,
        miles=miles,
        net=attrs.get("NET"),
        geom=build_multilinestring_wkb(paths),
    )


def fetch_railroads() -> None:
    """Fetch all HIFLD railroad features for the entire US and load into PostGIS."""
    settings = get_settings()
    fetch_arcgis_dataset(
        base_url=settings.hifld_railroads_base_url,
        model_class=Railroad,
        mapper=_map_railroad,
        dataset_name="railroads",
    )


def verify_railroads() -> None:
    """Verify railroad records were loaded."""
    verify_arcgis_dataset(Railroad, "railroads")

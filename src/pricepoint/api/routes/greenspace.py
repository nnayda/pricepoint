"""Greenspace endpoint — returns parks and trails with stub data."""

from typing import Annotated

from fastapi import APIRouter, Query

from pricepoint.api.schemas.greenspace import (
    GreenspaceFeature,
    GreenspaceMetrics,
    GreenspaceResponse,
)

router = APIRouter(tags=["greenspace"])

_FEATURES = [
    GreenspaceFeature(
        id="GS-001",
        name="Fred G. Bond Metro Park",
        feature_type="park",
        lat=35.7855,
        lon=-78.7912,
        distance_miles=0.6,
        acreage=310.0,
    ),
    GreenspaceFeature(
        id="GS-002",
        name="Annie Jones Park",
        feature_type="park",
        lat=35.7932,
        lon=-78.7741,
        distance_miles=0.5,
        acreage=56.0,
    ),
    GreenspaceFeature(
        id="GS-003",
        name="Black Creek Greenway",
        feature_type="trail",
        lat=35.7879,
        lon=-78.7856,
        distance_miles=0.3,
        acreage=None,
    ),
    GreenspaceFeature(
        id="GS-004",
        name="Hinshaw Greenway",
        feature_type="trail",
        lat=35.7961,
        lon=-78.7789,
        distance_miles=0.9,
        acreage=None,
    ),
    GreenspaceFeature(
        id="GS-005",
        name="Cary Dog Park",
        feature_type="park",
        lat=35.7845,
        lon=-78.7695,
        distance_miles=1.1,
        acreage=4.5,
    ),
    GreenspaceFeature(
        id="GS-006",
        name="Hemlock Bluffs Nature Preserve",
        feature_type="park",
        lat=35.7768,
        lon=-78.7821,
        distance_miles=1.6,
        acreage=150.0,
    ),
]


@router.get("/greenspace", response_model=GreenspaceResponse)
async def get_greenspace(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    radius_miles: Annotated[float, Query(gt=0, le=10)] = 2.0,
) -> GreenspaceResponse:
    """Return greenspace features and metrics near the given location."""
    return GreenspaceResponse(
        features=_FEATURES,
        metrics=GreenspaceMetrics(
            parks_within_1mi=3,
            nearest_park_miles=0.3,
            total_green_acres_1mi=366.0,
            greenspace_z_score=0.85,
        ),
    )

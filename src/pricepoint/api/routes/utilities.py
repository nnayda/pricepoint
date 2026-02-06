"""Utilities endpoint — returns infrastructure features with stub data."""

from typing import Annotated

from fastapi import APIRouter, Query

from pricepoint.api.schemas.utilities import (
    UtilitiesMetrics,
    UtilitiesResponse,
    UtilityFeature,
)

router = APIRouter(tags=["utilities"])

_FEATURES = [
    UtilityFeature(
        id="UT-001",
        name="US-1 / US-64 Highway",
        feature_type="highway",
        lat=35.7985,
        lon=-78.7762,
        distance_miles=0.8,
    ),
    UtilityFeature(
        id="UT-002",
        name="I-40",
        feature_type="highway",
        lat=35.8041,
        lon=-78.7834,
        distance_miles=1.5,
    ),
    UtilityFeature(
        id="UT-003",
        name="CSX Railroad",
        feature_type="railroad",
        lat=35.7852,
        lon=-78.7691,
        distance_miles=1.0,
    ),
    UtilityFeature(
        id="UT-004",
        name="Duke Energy Transmission Line",
        feature_type="powerline",
        lat=35.7928,
        lon=-78.7723,
        distance_miles=0.6,
    ),
    UtilityFeature(
        id="UT-005",
        name="Cary Water Treatment Facility",
        feature_type="water_treatment",
        lat=35.7798,
        lon=-78.7901,
        distance_miles=1.3,
    ),
]


@router.get("/utilities", response_model=UtilitiesResponse)
async def get_utilities(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    radius_miles: Annotated[float, Query(gt=0, le=10)] = 1.0,
) -> UtilitiesResponse:
    """Return utility infrastructure features near the given location."""
    return UtilitiesResponse(
        features=_FEATURES,
        metrics=UtilitiesMetrics(
            nearest_highway_miles=0.8,
            nearest_railroad_miles=1.0,
            nearest_powerline_miles=0.6,
            nuisance_score=3.2,
        ),
    )

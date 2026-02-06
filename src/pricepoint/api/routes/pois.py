"""Points of interest endpoint — returns POI data with stub data."""

from typing import Annotated

from fastapi import APIRouter, Query

from pricepoint.api.schemas.pois import PointOfInterest, PoisResponse

router = APIRouter(tags=["pois"])

_POIS = [
    PointOfInterest(
        id="POI-001",
        name="Harris Teeter",
        category="grocery",
        lat=35.7892,
        lon=-78.7741,
        distance_miles=0.4,
        drive_minutes=2,
    ),
    PointOfInterest(
        id="POI-002",
        name="Publix",
        category="grocery",
        lat=35.7948,
        lon=-78.7695,
        distance_miles=0.9,
        drive_minutes=4,
    ),
    PointOfInterest(
        id="POI-003",
        name="Trader Joe's",
        category="grocery",
        lat=35.7835,
        lon=-78.7622,
        distance_miles=1.8,
        drive_minutes=7,
    ),
    PointOfInterest(
        id="POI-004",
        name="CVS Pharmacy",
        category="pharmacy",
        lat=35.7911,
        lon=-78.7763,
        distance_miles=0.3,
        drive_minutes=2,
    ),
    PointOfInterest(
        id="POI-005",
        name="Walgreens",
        category="pharmacy",
        lat=35.7865,
        lon=-78.7709,
        distance_miles=0.8,
        drive_minutes=3,
    ),
    PointOfInterest(
        id="POI-006",
        name="Target",
        category="retail",
        lat=35.7958,
        lon=-78.7688,
        distance_miles=1.2,
        drive_minutes=5,
    ),
    PointOfInterest(
        id="POI-007",
        name="Walmart Supercenter",
        category="retail",
        lat=35.7812,
        lon=-78.7591,
        distance_miles=2.1,
        drive_minutes=8,
    ),
    PointOfInterest(
        id="POI-008",
        name="Home Depot",
        category="retail",
        lat=35.7978,
        lon=-78.7654,
        distance_miles=1.6,
        drive_minutes=6,
    ),
    PointOfInterest(
        id="POI-009",
        name="Chick-fil-A",
        category="restaurant",
        lat=35.7905,
        lon=-78.7748,
        distance_miles=0.4,
        drive_minutes=2,
    ),
    PointOfInterest(
        id="POI-010",
        name="Olive Garden",
        category="restaurant",
        lat=35.7939,
        lon=-78.7712,
        distance_miles=0.8,
        drive_minutes=4,
    ),
    PointOfInterest(
        id="POI-011",
        name="Starbucks",
        category="restaurant",
        lat=35.7887,
        lon=-78.7772,
        distance_miles=0.2,
        drive_minutes=1,
    ),
    PointOfInterest(
        id="POI-012",
        name="WakeMed Cary Hospital",
        category="medical",
        lat=35.7821,
        lon=-78.7830,
        distance_miles=1.0,
        drive_minutes=4,
    ),
    PointOfInterest(
        id="POI-013",
        name="Planet Fitness",
        category="fitness",
        lat=35.7925,
        lon=-78.7699,
        distance_miles=0.9,
        drive_minutes=4,
    ),
    PointOfInterest(
        id="POI-014",
        name="Cary Regional Library",
        category="library",
        lat=35.7842,
        lon=-78.7755,
        distance_miles=0.6,
        drive_minutes=3,
    ),
    PointOfInterest(
        id="POI-015",
        name="Shell Gas Station",
        category="gas_station",
        lat=35.7915,
        lon=-78.7738,
        distance_miles=0.5,
        drive_minutes=2,
    ),
]


@router.get("/pois", response_model=PoisResponse)
async def get_pois(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    radius_miles: Annotated[float, Query(gt=0, le=10)] = 3.0,
) -> PoisResponse:
    """Return points of interest near the given location."""
    return PoisResponse(pois=_POIS)

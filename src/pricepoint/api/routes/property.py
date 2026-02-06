"""Property endpoint — returns property details with stub data."""

from typing import Annotated

from fastapi import APIRouter, Query

from pricepoint.api.schemas.property import (
    ClimateRisk,
    ExteriorFeatures,
    FinancialDetails,
    InteriorFeatures,
    PropertyDetails,
    PropertyImage,
    PropertyResponse,
    SaleHistoryEntry,
    SchoolNearby,
    TaxHistoryEntry,
    ValuationData,
)

router = APIRouter(tags=["property"])


@router.get("/property", response_model=PropertyResponse)
async def get_property(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    address: Annotated[str, Query(min_length=1)],
) -> PropertyResponse:
    """Return property details for the given location."""
    return PropertyResponse(
        details=PropertyDetails(
            address=address,
            city="Cary",
            state="NC",
            zip_code="27513",
            lat=lat,
            lon=lon,
            bedrooms=4,
            bathrooms=3.0,
            sqft=2847,
            lot_size_sqft=10890,
            year_built=2005,
            property_type="Single Family",
            stories=2,
            garage_spaces=2,
            description=(
                "Stunning 4-bedroom home in the heart of Cary featuring an open "
                "floor plan, gourmet kitchen with granite countertops, and a "
                "spacious master suite. The backyard offers a large deck perfect "
                "for entertaining, overlooking a private wooded lot."
            ),
            highlights=[
                "Open floor plan",
                "Granite countertops",
                "Hardwood floors throughout main level",
                "Spacious master suite with walk-in closet",
                "Large deck with wooded backyard",
                "Cul-de-sac location",
                "Top-rated school district",
            ],
            images=[
                PropertyImage(
                    url="/images/property/front.jpg",
                    alt="Front exterior view",
                    is_primary=True,
                ),
                PropertyImage(
                    url="/images/property/kitchen.jpg",
                    alt="Kitchen with granite countertops",
                ),
                PropertyImage(
                    url="/images/property/living.jpg",
                    alt="Living room with fireplace",
                ),
                PropertyImage(
                    url="/images/property/master.jpg",
                    alt="Master bedroom",
                ),
                PropertyImage(
                    url="/images/property/backyard.jpg",
                    alt="Backyard deck and wooded lot",
                ),
            ],
        ),
        valuation=ValuationData(
            listed_price=485000.0,
            last_sold_price=310000.0,
            last_sold_date="2018-06-15",
            predicted_value=472000.0,
            confidence_interval_low=449000.0,
            confidence_interval_high=495000.0,
            model_version="v2.3.1",
            prediction_date="2025-01-15",
        ),
        interior=InteriorFeatures(
            flooring=["Hardwood", "Carpet", "Tile"],
            appliances=[
                "Dishwasher",
                "Microwave",
                "Gas Range",
                "Refrigerator",
                "Disposal",
            ],
            heating="Forced Air",
            cooling="Central Air",
            fireplace=True,
            basement=None,
        ),
        exterior=ExteriorFeatures(
            roof="Architectural Shingle",
            siding="Fiber Cement",
            foundation="Slab",
            parking="2-Car Garage",
            pool=False,
            fence=True,
        ),
        financial=FinancialDetails(
            hoa_monthly=85.0,
            tax_annual=4234.0,
            tax_year=2024,
            assessed_value=412000.0,
        ),
        schools=[
            SchoolNearby(
                name="Mills Park Elementary",
                school_type="Elementary",
                rating=9,
                distance_miles=0.8,
                drive_minutes=3,
                walk_minutes=16,
            ),
            SchoolNearby(
                name="Mills Park Middle",
                school_type="Middle",
                rating=8,
                distance_miles=1.2,
                drive_minutes=5,
                walk_minutes=24,
            ),
            SchoolNearby(
                name="Green Hope High",
                school_type="High",
                rating=8,
                distance_miles=2.1,
                drive_minutes=7,
                walk_minutes=None,
            ),
            SchoolNearby(
                name="Northwoods Elementary",
                school_type="Elementary",
                rating=7,
                distance_miles=1.5,
                drive_minutes=5,
                walk_minutes=30,
            ),
            SchoolNearby(
                name="Salem Middle",
                school_type="Middle",
                rating=3,
                distance_miles=3.2,
                drive_minutes=10,
                walk_minutes=None,
            ),
        ],
        sale_history=[
            SaleHistoryEntry(date="2005-03-22", price=245000.0, event_type="Sold"),
            SaleHistoryEntry(date="2010-08-10", price=265000.0, event_type="Sold"),
            SaleHistoryEntry(date="2014-11-05", price=289000.0, event_type="Sold"),
            SaleHistoryEntry(date="2018-06-15", price=310000.0, event_type="Sold"),
            SaleHistoryEntry(date="2025-01-02", price=485000.0, event_type="Listed"),
        ],
        tax_history=[
            TaxHistoryEntry(year=2005, assessed_value=240000.0, tax_amount=2160.0),
            TaxHistoryEntry(year=2006, assessed_value=248000.0, tax_amount=2232.0),
            TaxHistoryEntry(year=2007, assessed_value=255000.0, tax_amount=2295.0),
            TaxHistoryEntry(year=2008, assessed_value=250000.0, tax_amount=2250.0),
            TaxHistoryEntry(year=2009, assessed_value=242000.0, tax_amount=2178.0),
            TaxHistoryEntry(year=2010, assessed_value=258000.0, tax_amount=2322.0),
            TaxHistoryEntry(year=2011, assessed_value=262000.0, tax_amount=2358.0),
            TaxHistoryEntry(year=2012, assessed_value=270000.0, tax_amount=2430.0),
            TaxHistoryEntry(year=2013, assessed_value=278000.0, tax_amount=2502.0),
            TaxHistoryEntry(year=2014, assessed_value=285000.0, tax_amount=2565.0),
            TaxHistoryEntry(year=2015, assessed_value=295000.0, tax_amount=2655.0),
            TaxHistoryEntry(year=2016, assessed_value=305000.0, tax_amount=2745.0),
            TaxHistoryEntry(year=2017, assessed_value=318000.0, tax_amount=2862.0),
            TaxHistoryEntry(year=2018, assessed_value=330000.0, tax_amount=2970.0),
            TaxHistoryEntry(year=2019, assessed_value=345000.0, tax_amount=3105.0),
            TaxHistoryEntry(year=2020, assessed_value=358000.0, tax_amount=3222.0),
            TaxHistoryEntry(year=2021, assessed_value=372000.0, tax_amount=3348.0),
            TaxHistoryEntry(year=2022, assessed_value=388000.0, tax_amount=3654.0),
            TaxHistoryEntry(year=2023, assessed_value=400000.0, tax_amount=3920.0),
            TaxHistoryEntry(year=2024, assessed_value=412000.0, tax_amount=4234.0),
        ],
        climate_risk=ClimateRisk(
            flood_risk="Moderate",
            flood_score=3,
            fire_risk="Low",
            fire_score=2,
        ),
    )

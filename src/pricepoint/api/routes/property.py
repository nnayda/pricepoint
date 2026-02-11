"""Property endpoint — returns property details from DB or stub data."""

import logging
from typing import Annotated

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_MakePoint, ST_SetSRID
from sqlalchemy import select
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db
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
from pricepoint.config.settings import get_settings
from pricepoint.db.models import PropertyDetail, PropertySchool, PropertyValuation, School

logger = logging.getLogger(__name__)

router = APIRouter(tags=["property"])


def _build_response_from_db(
    prop: PropertyDetail,
    db: Session,
    lat: float,
    lon: float,
) -> PropertyResponse:
    """Build a PropertyResponse from database records."""
    # Get Redfin valuation
    redfin_val = db.execute(
        select(PropertyValuation).where(
            PropertyValuation.property_id == prop.id,
            PropertyValuation.source == "redfin",
        )
    ).scalar_one_or_none()

    # Get ML valuation
    ml_val = db.execute(
        select(PropertyValuation).where(
            PropertyValuation.property_id == prop.id,
            PropertyValuation.source == "ml_model",
        )
    ).scalar_one_or_none()

    # Get schools via linkage
    school_links = db.execute(
        select(PropertySchool, School)
        .join(School, PropertySchool.school_id == School.id)
        .where(PropertySchool.property_id == prop.id)
    ).all()

    schools = [
        SchoolNearby(
            name=school.name,
            address=school.address,
            school_type=school.school_type or "Unknown",
            rating=int(school.rating) if school.rating else 0,
            distance_miles=link.distance_miles or 0.0,
            drive_minutes=link.drive_minutes or 0,
            walk_minutes=link.walk_minutes,
        )
        for link, school in school_links
    ]

    # Build sale history
    sale_history = []
    if prop.sale_history:
        for entry in prop.sale_history:
            if entry.get("date") and entry.get("price") is not None:
                sale_history.append(
                    SaleHistoryEntry(
                        date=entry["date"],
                        price=entry["price"],
                        event_type=entry.get("event_type", "Sold"),
                    )
                )

    # Build tax history
    tax_history = []
    if prop.tax_history:
        for entry in prop.tax_history:
            if entry.get("year") is not None:
                tax_history.append(
                    TaxHistoryEntry(
                        year=entry["year"],
                        assessed_value=entry.get("assessed_value") or 0.0,
                        tax_amount=entry.get("tax_amount") or 0.0,
                    )
                )

    # Build images from S3 paths — prefix with /api/photos/ for browser access
    images = []
    if prop.photo_s3_paths:
        for i, path in enumerate(prop.photo_s3_paths):
            images.append(
                PropertyImage(
                    url=f"/api/photos/{path}",
                    alt=f"Property photo {i + 1}",
                    is_primary=(i == 0),
                )
            )

    return PropertyResponse(
        property=PropertyDetails(
            address=prop.address,
            city=prop.city or "",
            state=prop.state or "",
            zip_code=prop.zip_code or "",
            lat=lat,
            lon=lon,
            bedrooms=prop.beds or 0,
            bathrooms=prop.baths or 0.0,
            sqft=prop.sqft or 0,
            lot_size_sqft=int(prop.lot_size_sqft) if prop.lot_size_sqft else 0,
            year_built=prop.year_built or 0,
            property_type=prop.property_type or "Single Family",
            stories=prop.stories or 1,
            garage_spaces=prop.garage_spaces or 0,
            description=prop.description or "",
            highlights=[],
            images=images,
            listing_status=prop.listing_status,
        ),
        valuation=ValuationData(
            listed_price=prop.listing_price,
            last_sold_price=prop.sold_price,
            last_sold_date=prop.sold_date.strftime("%Y-%m-%d") if prop.sold_date else None,
            redfin_estimate=redfin_val.value if redfin_val else None,
            predicted_value=ml_val.value if ml_val else None,
            confidence_interval_low=ml_val.confidence_low if ml_val else None,
            confidence_interval_high=ml_val.confidence_high if ml_val else None,
            model_version=ml_val.model_version if ml_val else None,
            prediction_date=(
                ml_val.estimated_at.strftime("%Y-%m-%d") if ml_val and ml_val.estimated_at else None
            ),
        ),
        interior=InteriorFeatures(
            flooring=prop.flooring or [],
            appliances=prop.appliances or [],
            heating=prop.heating or "Unknown",
            cooling=prop.cooling or "Unknown",
            fireplace=prop.fireplace is not None and prop.fireplace.lower() != "none",
            basement=prop.basement,
        ),
        exterior=ExteriorFeatures(
            roof=prop.roof or "Unknown",
            siding=prop.siding or "Unknown",
            foundation=prop.foundation or "Unknown",
            parking=prop.parking or "None",
            pool=prop.pool is not None and prop.pool.lower() not in ("none", "no"),
            fence=prop.fence or "None",
        ),
        financial=FinancialDetails(
            hoa_monthly=prop.hoa_monthly,
            tax_annual=prop.tax_annual or 0.0,
            tax_year=prop.tax_year or 0,
            assessed_value=prop.assessed_value or 0.0,
        ),
        schools=schools,
        sale_history=sale_history,
        tax_history=tax_history,
        climate_risk=ClimateRisk(
            flood_risk=prop.flood_risk or "Unknown",
            flood_score=prop.flood_score or 0,
            fire_risk=prop.fire_risk or "Unknown",
            fire_score=prop.fire_score or 0,
        ),
    )


def _build_stub_response(address: str, lat: float, lon: float) -> PropertyResponse:
    """Return hardcoded stub data for backward compatibility."""
    return PropertyResponse(
        property=PropertyDetails(
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
            listing_status="FOR SALE",
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
            fence="None",
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


@router.get("/property", response_model=PropertyResponse)
async def get_property(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    address: Annotated[str, Query(min_length=1)],
    db: Annotated[Session, Depends(get_db)],
) -> PropertyResponse:
    """Return property details for the given location.

    Lookup strategy:
    1. Spatial search — closest property within ~100 m of (lat, lon).
    2. Street-name prefix match — first comma-delimited segment of address.
    3. Fall back to stub data.
    """
    # 1. Spatial search (requires populated location column)
    tolerance = 0.001  # ~111 m at mid-latitudes
    point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

    prop = db.execute(
        select(PropertyDetail)
        .where(
            PropertyDetail.location.isnot(None),
            ST_DWithin(PropertyDetail.location, point, tolerance),
        )
        .order_by(ST_Distance(PropertyDetail.location, point))
        .limit(1)
    ).scalar_one_or_none()

    if prop:
        return _build_response_from_db(prop, db, lat, lon)

    # 2. Address text match — Nominatim display_name varies:
    #      "100, Clendenen Court, Preston, Cary, ..."   (number, street, ...)
    #      "100 Clendenen Ct, Cary, NC 27513, US"       (number street, ...)
    #    DB stores Redfin form: "100 Clendenen Ct, Cary, NC 27513".
    #    Extract house number + street keyword and ILIKE match.
    parts = [p.strip() for p in address.split(",") if p.strip()]
    house_number = parts[0] if parts else ""
    street_name = parts[1] if len(parts) > 1 else ""

    # If the first part has spaces (e.g. "100 Clendenen Ct"), it already
    # includes the street — use it as-is for a prefix match.
    if " " in house_number:
        prop = db.execute(
            select(PropertyDetail)
            .where(PropertyDetail.address.startswith(house_number + ","))
            .limit(1)
        ).scalar_one_or_none()
    elif house_number and street_name:
        # Nominatim splits "100" and "Clendenen Court" into separate parts.
        # Use the first word of the street name to avoid abbreviation mismatches
        # (e.g. "Court" vs "Ct"). ILIKE '100 Clendenen%' matches the DB row.
        street_keyword = street_name.split()[0] if street_name else ""
        if street_keyword:
            prop = db.execute(
                select(PropertyDetail)
                .where(PropertyDetail.address.ilike(f"{house_number} {street_keyword}%"))
                .limit(1)
            ).scalar_one_or_none()

    if prop:
        return _build_response_from_db(prop, db, lat, lon)

    return _build_stub_response(address, lat, lon)


@router.get("/photos/{path:path}")
async def get_photo(path: str) -> StreamingResponse:
    """Stream a property photo from S3 storage."""
    settings = get_settings()
    s3 = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    )
    try:
        obj = s3.get_object(Bucket=settings.s3_bucket, Key=path)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")
        if error_code in ("NoSuchKey", "404"):
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Photo not found") from exc
        raise

    content_type = obj.get("ContentType", "image/jpeg")
    return StreamingResponse(
        obj["Body"],
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )

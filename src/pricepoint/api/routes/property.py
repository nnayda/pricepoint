"""Property endpoint — returns property details from DB or stub data."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_MakePoint, ST_SetSRID
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db
from pricepoint.api.schemas.property import (
    ClimateRisk,
    ComparableProperty,
    ExteriorFeatures,
    FinancialDetails,
    InteriorFeatures,
    ListingQuality,
    PropertyDetails,
    PropertyImage,
    PropertyResponse,
    SaleHistoryEntry,
    SchoolNearby,
    TaxHistoryEntry,
    UtilityDetails,
    ValuationData,
)
from pricepoint.config.settings import get_settings
from pricepoint.db.models import (
    LlmQualityScore,
    PropertySchool,
    PropertyValuation,
    RedfinListing,
    SaleHistoryRecord,
    School,
    TaxHistoryRecord,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["property"])


def _split_csv(value: str | None) -> list[str]:
    """Split a comma-separated string into trimmed items, dropping empties."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _build_interior(prop: RedfinListing) -> InteriorFeatures:
    """Extract interior features from the property_details JSON column."""
    details: dict = prop.property_details or {}
    return InteriorFeatures(
        flooring=_split_csv(details.get("flooring")),
        appliances=_split_csv(details.get("appliances")),
        heating=details.get("heating") or "Unknown",
        cooling=details.get("cooling") or "Unknown",
        fireplace=prop.has_fireplace or False,
        basement=details.get("basement") or details.get("basement_details") or None,
        laundry=details.get("laundry") or None,
    )


def _build_exterior(prop: RedfinListing) -> ExteriorFeatures:
    """Extract exterior features from the property_details JSON column."""
    details: dict = prop.property_details or {}
    return ExteriorFeatures(
        roof=details.get("roof") or details.get("roof_details") or "Unknown",
        siding=prop.facade_type or details.get("construction_type") or "Unknown",
        foundation=details.get("foundation_details") or details.get("foundation_type") or "Unknown",
        parking=prop.parking_type or details.get("parking_features") or "None",
        pool=(prop.has_private_pool or prop.has_community_pool) or False,
        fence=details.get("fencing") or "None",
        lot_features=details.get("lot_features") or None,
    )


def _build_utilities(prop: RedfinListing) -> UtilityDetails | None:
    """Extract utility info from the property_details JSON column."""
    details: dict = prop.property_details or {}
    water = details.get("water_source") or None
    sewer = details.get("sewer") or None
    electric = details.get("electric") or None
    if not any([water, sewer, electric]):
        return None
    return UtilityDetails(water=water, sewer=sewer, electric=electric)


def _build_response_from_db(
    prop: RedfinListing,
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

    schools = []
    for link, school in school_links:
        # Build address from components
        addr_parts = [p for p in [school.street, school.city, school.state, school.zip_code] if p]
        address = ", ".join(addr_parts) if addr_parts else None

        # Extract lat/lon from geometry
        school_lat: float | None = None
        school_lon: float | None = None
        if school.location is not None:
            coords = db.execute(
                select(
                    func.ST_Y(school.location).label("lat"),
                    func.ST_X(school.location).label("lon"),
                )
            ).one()
            school_lat = coords.lat
            school_lon = coords.lon

        schools.append(
            SchoolNearby(
                name=school.name,
                address=address,
                school_type=school.school_type or "Unknown",
                school_level=school.school_level,
                rating=int(school.rating) if school.rating else 0,
                grades=school.grades,
                distance_miles=link.distance_miles or 0.0,
                drive_minutes=link.drive_minutes or 0,
                walk_minutes=link.walk_minutes,
                student_teacher_ratio=school.student_teacher_ratio,
                enrollment=school.enrollment,
                assigned=link.assigned or False,
                lat=school_lat,
                lon=school_lon,
            )
        )

    # Build sale history from relational table
    sale_records = (
        db.execute(
            select(SaleHistoryRecord)
            .where(SaleHistoryRecord.property_id == prop.id)
            .order_by(SaleHistoryRecord.date)
        )
        .scalars()
        .all()
    )

    sale_history = [
        SaleHistoryEntry(
            date=rec.date.strftime("%Y-%m-%d") if rec.date else "",
            price=rec.price or 0.0,
            event_type=rec.event or "Sold",
        )
        for rec in sale_records
        if rec.date and rec.price is not None
    ]

    # Build tax history from relational table
    tax_records = (
        db.execute(
            select(TaxHistoryRecord)
            .where(TaxHistoryRecord.property_id == prop.id)
            .order_by(TaxHistoryRecord.date.desc())
        )
        .scalars()
        .all()
    )

    tax_history = [
        TaxHistoryEntry(
            year=rec.date.year if rec.date else 0,
            assessed_value=rec.assessment_value or 0.0,
            tax_amount=rec.property_tax or 0.0,
        )
        for rec in tax_records
        if rec.date
    ]

    # Get LLM listing quality score (most recent)
    llm_score = db.execute(
        select(LlmQualityScore)
        .where(LlmQualityScore.listing_id == prop.id)
        .order_by(LlmQualityScore.extracted_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    # Build images from S3 paths — prefix with /api/photos/ for browser access
    images = []
    if prop.property_photos:
        for i, path in enumerate(prop.property_photos):
            images.append(
                PropertyImage(
                    url=f"/api/photos/{path}",
                    alt=f"Property photo {i + 1}",
                    is_primary=(i == 0),
                )
            )

    return PropertyResponse(
        listing_id=prop.id,
        property=PropertyDetails(
            address=prop.street_address or "",
            city=prop.city or "",
            state=prop.state or "",
            zip_code=prop.zip_code or "",
            lat=lat,
            lon=lon,
            bedrooms=prop.num_beds or 0,
            bathrooms=prop.num_baths or 0.0,
            sqft=prop.sqft or 0,
            lot_size_sqft=int(prop.lot_size * 43560) if prop.lot_size else 0,
            year_built=prop.year_built or 0,
            property_type="Single Family",
            stories=int(prop.num_stories) if prop.num_stories else 1,
            garage_spaces=prop.num_garage_spaces or 0,
            description=prop.description or "",
            highlights=[],
            images=images,
            listing_status=prop.listing_status,
            price_per_sqft=prop.price_per_sqft,
            days_on_market=(
                (datetime.now(tz=UTC) - prop.contract_date.replace(tzinfo=UTC)).days
                if prop.contract_date
                else None
            ),
            listed_date=(prop.contract_date.strftime("%Y-%m-%d") if prop.contract_date else None),
            hoa_monthly=(prop.association_fee / 12) if prop.association_fee else None,
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
        interior=_build_interior(prop),
        exterior=_build_exterior(prop),
        utilities=_build_utilities(prop),
        financial=FinancialDetails(
            hoa_monthly=(prop.association_fee / 12) if prop.association_fee else None,
            tax_annual=tax_history[0].tax_amount if tax_history else 0.0,
            tax_year=tax_history[0].year if tax_history else 0,
            assessed_value=tax_history[0].assessed_value if tax_history else 0.0,
        ),
        schools=schools,
        sale_history=sale_history,
        tax_history=tax_history,
        climate_risk=ClimateRisk(
            flood_risk=prop.flood_factor or "Unknown",
            flood_score=prop.flood_score or 0,
            fire_risk=prop.fire_factor or "Unknown",
            fire_score=prop.fire_score or 0,
        ),
        listing_quality=(
            ListingQuality(
                description_score=llm_score.quality_score,
                quality_reasoning=llm_score.quality_reasoning,
            )
            if llm_score and llm_score.quality_score is not None
            else None
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
    # Extract house number from the address for validation.
    # Nominatim display_name varies:
    #   "100, Clendenen Court, Preston, Cary, ..."   (number, street, ...)
    #   "100 Clendenen Ct, Cary, NC 27513, US"       (number street, ...)
    # DB stores Redfin form: "100 Clendenen Ct" in street_address.
    parts = [p.strip() for p in address.split(",") if p.strip()]
    first_part = parts[0] if parts else ""
    # House number is the leading digit sequence from the first segment.
    searched_house_num = first_part.split()[0] if first_part else ""

    # 1. Spatial search (requires populated location column)
    tolerance = 0.001  # ~111 m at mid-latitudes
    point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

    prop = db.execute(
        select(RedfinListing)
        .where(
            RedfinListing.location.isnot(None),
            ST_DWithin(RedfinListing.location, point, tolerance),
        )
        .order_by(ST_Distance(RedfinListing.location, point))
        .limit(1)
    ).scalar_one_or_none()

    if prop:
        # Verify the house number matches to avoid returning a neighbour.
        db_house_num = (prop.street_address or "").split()[0] if prop.street_address else ""
        if searched_house_num and db_house_num != searched_house_num:
            logger.info(
                "Spatial match house number mismatch: searched %s, found %s (%s)",
                searched_house_num,
                db_house_num,
                prop.street_address,
            )
            prop = None

    if prop:
        return _build_response_from_db(prop, db, lat, lon)

    # 2. Address text match — exact house number + street keyword via ILIKE.
    street_name = parts[1] if len(parts) > 1 else ""

    # If the first part has spaces (e.g. "100 Clendenen Ct"), it already
    # includes the street — use it for a prefix match on street_address.
    if " " in first_part:
        prop = db.execute(
            select(RedfinListing)
            .where(RedfinListing.street_address.startswith(first_part))
            .limit(1)
        ).scalar_one_or_none()
    elif searched_house_num and street_name:
        # Nominatim splits "100" and "Clendenen Court" into separate parts.
        street_keyword = street_name.split()[0] if street_name else ""
        if street_keyword:
            prop = db.execute(
                select(RedfinListing)
                .where(
                    RedfinListing.street_address.ilike(f"{searched_house_num} {street_keyword}%")
                )
                .limit(1)
            ).scalar_one_or_none()

    if prop:
        return _build_response_from_db(prop, db, lat, lon)

    raise HTTPException(status_code=404, detail="Property not found")


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


_MILES_TO_METERS = 1609.344


@router.get("/comparables", response_model=list[ComparableProperty])
async def get_comparables(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    beds: Annotated[int, Query(ge=0)],
    sqft: Annotated[float, Query(gt=0)],
    db: Annotated[Session, Depends(get_db)],
    radius_miles: Annotated[float, Query(gt=0, le=50)] = 3.0,
    limit: Annotated[int, Query(ge=1, le=50)] = 5,
) -> list[ComparableProperty]:
    """Return comparable recently-sold properties near a given location.

    Filters by radius, bedroom count (+/- 1), and square footage (+/- 25%).
    Results are ranked by a composite similarity score combining distance,
    size difference, and recency.
    """
    radius_meters = radius_miles * _MILES_TO_METERS
    cutoff_date = datetime.now(tz=UTC) - timedelta(days=365)
    sqft_low = sqft * 0.75
    sqft_high = sqft * 1.25

    point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

    # Distance in metres (geography cast for accurate measurement)
    dist_col = func.ST_Distance(
        cast(RedfinListing.location, Geography()),
        cast(point, Geography()),
    ).label("distance_m")

    stmt = select(RedfinListing, dist_col).where(
        RedfinListing.location.isnot(None),
        RedfinListing.sold_date.isnot(None),
        RedfinListing.sold_price.isnot(None),
        RedfinListing.sold_date >= cutoff_date,
        RedfinListing.num_beds.isnot(None),
        RedfinListing.sqft.isnot(None),
        RedfinListing.num_beds.between(beds - 1, beds + 1),
        RedfinListing.sqft.between(int(sqft_low), int(sqft_high)),
        ST_DWithin(
            cast(RedfinListing.location, Geography()),
            cast(point, Geography()),
            radius_meters,
        ),
    )

    rows = db.execute(stmt).all()

    now = datetime.now(tz=UTC)
    scored: list[tuple[float, RedfinListing, float]] = []
    for row_listing, distance_m in rows:
        distance_km = distance_m / 1000.0
        sqft_diff = abs((row_listing.sqft or 0) - sqft)
        days_since = (now - row_listing.sold_date.replace(tzinfo=UTC)).days

        score = distance_km * 0.3 + (sqft_diff / sqft) * 0.4 + (days_since / 365) * 0.3
        scored.append((score, row_listing, distance_m))

    scored.sort(key=lambda x: x[0])
    top = scored[:limit]

    results: list[ComparableProperty] = []
    for _score, prop, _dist in top:
        # Extract lat/lon from the geometry
        prop_point = db.execute(
            select(
                func.ST_Y(prop.location).label("lat"),
                func.ST_X(prop.location).label("lon"),
            )
        ).one()

        full_address = prop.street_address or ""
        if prop.city:
            full_address += f", {prop.city}"
        if prop.state:
            full_address += f", {prop.state}"
        if prop.zip_code:
            full_address += f" {prop.zip_code}"

        results.append(
            ComparableProperty(
                id=prop.id,
                address=full_address,
                sale_price=prop.sold_price,
                sold_date=prop.sold_date.strftime("%Y-%m-%d"),
                beds=prop.num_beds or 0,
                baths=prop.num_baths or 0.0,
                sqft=prop.sqft or 0,
                price_per_sqft=prop.price_per_sqft
                or (round(prop.sold_price / prop.sqft, 2) if prop.sqft else 0.0),
                lat=prop_point.lat,
                lon=prop_point.lon,
            )
        )

    return results

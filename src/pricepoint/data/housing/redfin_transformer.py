"""Transform staging Redfin listings into production property tables.

Pure parsing functions are stateless and side-effect-free for easy testing.
I/O functions handle database interactions and geocoding.
"""

from __future__ import annotations

import contextlib
import hashlib
import logging
import re
import time
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from pricepoint.db.engine import SessionLocal
from pricepoint.db.models import (
    PropertyDetail,
    PropertySchool,
    PropertyValuation,
    School,
    StagingRedfinListing,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Climate risk level -> numeric score mapping
# ---------------------------------------------------------------------------
CLIMATE_SCORE_MAP: dict[str, int] = {
    "extreme": 10,
    "severe": 8,
    "major": 7,
    "moderate": 5,
    "minor": 3,
    "minimal": 1,
}


# ---------------------------------------------------------------------------
# Pure parsing functions
# ---------------------------------------------------------------------------


def compute_staging_hash(record: StagingRedfinListing) -> str:
    """Compute SHA-256 of data columns (excludes id, loaded_at)."""
    cols = [
        record.address,
        record.city,
        record.state,
        record.zip_code,
        record.listing_status,
        record.sold_date,
        record.sold_price,
        record.listing_price,
        str(record.beds),
        str(record.baths),
        str(record.sqft),
        record.description,
        str(record.year_built),
        record.lot_size,
        record.price_per_sqft,
        record.listing_agent,
        record.listing_brokerage,
        record.buying_agent,
        record.buying_brokerage,
        record.redfin_estimate,
        str(record.sale_history),
        str(record.tax_history),
        str(record.property_details),
        str(record.schools),
        record.climate_flood_factor,
        record.climate_fire_factor,
        str(record.photo_s3_paths),
    ]
    data = "|".join(str(c) if c is not None else "" for c in cols)
    return hashlib.sha256(data.encode()).hexdigest()


def parse_price(price_str: str | None) -> float | None:
    """Parse a price string like '$721,000' -> 721000.0."""
    if not price_str:
        return None
    cleaned = re.sub(r"[^\d.]", "", price_str)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_lot_size_sqft(lot_str: str | None) -> float | None:
    """Parse lot size string to square feet.

    Handles 'X.XX Acres' and 'X,XXX Sq. Ft.' formats.
    """
    if not lot_str:
        return None
    text = lot_str.strip().lower()
    # Try acres first
    acres_match = re.search(r"([\d,.]+)\s*acres?", text)
    if acres_match:
        try:
            acres = float(acres_match.group(1).replace(",", ""))
            return acres * 43560.0
        except ValueError:
            return None
    # Try square feet
    sqft_match = re.search(r"([\d,.]+)\s*sq", text)
    if sqft_match:
        try:
            return float(sqft_match.group(1).replace(",", ""))
        except ValueError:
            return None
    return None


def map_climate_score(risk_level: str | None) -> int | None:
    """Map climate risk level string to numeric score (1-10)."""
    if not risk_level:
        return None
    return CLIMATE_SCORE_MAP.get(risk_level.strip().lower())


def extract_interior(prop_details_json: dict[str, Any] | None) -> dict[str, Any]:
    """Extract interior features from flat property_details JSON.

    Reads snake_case keys directly from the flat dict produced by the collector.
    """
    result: dict[str, Any] = {
        "flooring": [],
        "appliances": [],
        "heating": None,
        "cooling": None,
        "fireplace": None,
        "basement": None,
    }
    if not prop_details_json:
        return result

    # Flooring / appliances — comma-split into lists
    for list_key in ("flooring", "appliances"):
        val = prop_details_json.get(list_key)
        if isinstance(val, str):
            result[list_key] = [v.strip() for v in val.split(",")]

    # Heating — multiple alias keys
    for key in ("heating", "heating_information", "heating_type"):
        val = prop_details_json.get(key)
        if val is not None:
            result["heating"] = val if isinstance(val, str) else "Yes"
            break

    # Cooling — multiple alias keys
    for key in ("cooling", "cooling_information", "air_conditioning_type"):
        val = prop_details_json.get(key)
        if val is not None:
            result["cooling"] = val if isinstance(val, str) else "Yes"
            break

    # Fireplace — aliases + boolean
    for key in ("fireplace", "fireplace_features"):
        val = prop_details_json.get(key)
        if val is not None:
            result["fireplace"] = val if isinstance(val, str) else "Yes"
            break
    if result["fireplace"] is None and prop_details_json.get("has_fireplace") is True:
        result["fireplace"] = "Yes"

    # Basement — aliases + boolean
    for key in ("basement", "basement_details", "basement_information", "basement_type"):
        val = prop_details_json.get(key)
        if val is not None:
            result["basement"] = val if isinstance(val, str) else "Yes"
            break
    if result["basement"] is None and prop_details_json.get("has_basement") is True:
        result["basement"] = "Yes"

    return result


def extract_exterior(prop_details_json: dict[str, Any] | None) -> dict[str, Any]:
    """Extract exterior features from flat property_details JSON."""
    result: dict[str, Any] = {
        "roof": None,
        "siding": None,
        "foundation": None,
        "parking": None,
        "garage_spaces": None,
        "pool": None,
        "fence": None,
    }
    if not prop_details_json:
        return result

    # Direct keys
    for key in ("roof", "roof_details"):
        val = prop_details_json.get(key)
        if isinstance(val, str):
            result["roof"] = val
            break

    for key in ("exterior_features", "exterior_wall"):
        val = prop_details_json.get(key)
        if isinstance(val, str):
            result["siding"] = val
            break

    for key in ("foundation_details", "foundation_type"):
        val = prop_details_json.get(key)
        if isinstance(val, str):
            result["foundation"] = val
            break

    for key in ("fencing",):
        val = prop_details_json.get(key)
        if isinstance(val, str):
            result["fence"] = val
            break

    for key in ("pool_features",):
        val = prop_details_json.get(key)
        if isinstance(val, str):
            result["pool"] = val
            break

    # Parking
    val = prop_details_json.get("parking_features")
    if isinstance(val, str):
        result["parking"] = val
    elif (
        prop_details_json.get("attached_garage", "").lower() == "yes"
        if isinstance(prop_details_json.get("attached_garage"), str)
        else False
    ):
        result["parking"] = "Attached Garage"

    # Garage spaces
    gs = prop_details_json.get("garage_spaces")
    if gs is not None:
        with contextlib.suppress(ValueError, TypeError):
            result["garage_spaces"] = int(gs)

    return result


def extract_financial(
    prop_details_json: dict[str, Any] | None,
    tax_history: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Extract financial details from flat property_details and tax_history."""
    result: dict[str, Any] = {
        "hoa_monthly": None,
        "tax_annual": None,
        "tax_year": None,
        "assessed_value": None,
    }

    # Try HOA from flat property details
    if prop_details_json:
        for key in ("hoa_dues", "association_fee"):
            val = prop_details_json.get(key)
            if isinstance(val, str):
                result["hoa_monthly"] = parse_price(val)
                break

    # Get most recent tax data from tax_history
    if tax_history:
        parsed_history = parse_tax_history(tax_history)
        if parsed_history:
            most_recent = parsed_history[0]
            result["tax_annual"] = most_recent.get("tax_amount")
            result["tax_year"] = most_recent.get("year")
            result["assessed_value"] = most_recent.get("assessed_value")

    return result


def parse_school_desc(desc: str | None) -> dict[str, Any] | None:
    """Parse a school description like 'Public, PreK-5 Assigned 0.3mi'.

    Returns dict with school_type, grades, distance_miles or None.
    """
    if not desc:
        return None

    result: dict[str, Any] = {"school_type": None, "grades": None, "distance_miles": None}

    # Extract distance
    dist_match = re.search(r"([\d.]+)\s*mi", desc)
    if dist_match:
        with contextlib.suppress(ValueError):
            result["distance_miles"] = float(dist_match.group(1))

    # Split on comma for type and grades
    parts = [p.strip() for p in desc.split(",")]
    if parts:
        result["school_type"] = parts[0]

    if len(parts) > 1:
        # Second part contains grades info like "PreK-5 Assigned"
        grade_part = parts[1].strip()
        # Remove assignment status words
        grade_part = re.sub(r"\s+(Assigned|Choice|Nearby)\b.*", "", grade_part, flags=re.IGNORECASE)
        # Remove distance suffix
        grade_part = re.sub(r"\s+[\d.]+\s*mi.*", "", grade_part)
        if grade_part.strip():
            result["grades"] = grade_part.strip()

    return result


def _normalize_date(date_str: str | None) -> str | None:
    """Normalize a date string to ISO format (YYYY-MM-DD).

    Handles 'Jun 14, 2024', 'June 14, 2024', and already-ISO strings.
    """
    if not date_str:
        return None
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str


def parse_sale_history(raw: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Parse raw sale history into typed entries with float prices."""
    if not raw:
        return []
    result = []
    for entry in raw:
        parsed: dict[str, Any] = {
            "date": _normalize_date(entry.get("date")),
            "event_type": entry.get("event") or entry.get("event_type"),
            "price": parse_price(str(entry.get("price", ""))) if entry.get("price") else None,
        }
        result.append(parsed)
    return result


def parse_tax_history(raw: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Parse raw tax history into typed entries with float values.

    Returns sorted by year descending (most recent first).
    """
    if not raw:
        return []
    result = []
    for entry in raw:
        year = entry.get("year")
        if isinstance(year, str):
            try:
                year = int(year)
            except ValueError:
                continue
        parsed: dict[str, Any] = {
            "year": year,
            "tax_amount": parse_price(str(entry.get("tax", ""))) if entry.get("tax") else None,
            "assessed_value": (
                parse_price(str(entry.get("assessed_value", "")))
                if entry.get("assessed_value")
                else None
            ),
        }
        result.append(parsed)
    result.sort(key=lambda x: x.get("year") or 0, reverse=True)
    return result


# ---------------------------------------------------------------------------
# I/O functions
# ---------------------------------------------------------------------------


_GEOCODE_MAX_RETRIES = 3
_GEOCODE_BACKOFF_BASE = 2  # seconds


def geocode_address(address: str) -> tuple[float, float] | None:
    """Geocode an address via Nominatim. Returns (lat, lon) or None.

    Retries with exponential backoff on 429/5xx responses to respect
    Nominatim rate limits (max 1 request per second).
    """
    for attempt in range(_GEOCODE_MAX_RETRIES):
        time.sleep(max(1, _GEOCODE_BACKOFF_BASE**attempt))
        try:
            resp = httpx.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": address, "format": "json", "limit": 1},
                headers={"User-Agent": "PricePoint/1.0"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
            return None
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            if code in (429, 503, 509) and attempt < _GEOCODE_MAX_RETRIES - 1:
                logger.info(
                    "Geocoding rate-limited (%d) for %s, retrying (attempt %d/%d)",
                    code,
                    address,
                    attempt + 1,
                    _GEOCODE_MAX_RETRIES,
                )
                continue
            logger.warning("Geocoding failed for %s", address, exc_info=True)
            return None
        except Exception:
            logger.warning("Geocoding failed for %s", address, exc_info=True)
            return None
    return None


def upsert_school(
    session: Session,
    name: str,
    school_type: str | None,
    rating: float | None,
    grades: str | None,
    lat: float | None,
    lon: float | None,
) -> int:
    """Deduplicate school on (name, school_type). Returns school_id."""
    stmt = select(School).where(School.name == name, School.school_type == school_type)
    existing = session.execute(stmt).scalar_one_or_none()
    if existing:
        if rating is not None:
            existing.rating = rating
        if grades is not None:
            existing.grades = grades
        session.flush()
        return existing.id

    from geoalchemy2.shape import from_shape
    from shapely.geometry import Point

    location = None
    if lat is not None and lon is not None:
        location = from_shape(Point(lon, lat), srid=4326)
    school = School(
        name=name,
        school_type=school_type,
        rating=rating,
        grades=grades,
        location=location,
    )
    session.add(school)
    session.flush()
    return school.id


def transform_listing(
    session: Session,
    staging: StagingRedfinListing,
    geocode_fn: Any = None,
    enrich_fn: Any = None,
) -> bool:
    """Transform a single staging record into production tables.

    Returns True if the record was transformed (new or updated), False if skipped.
    """
    if geocode_fn is None:
        geocode_fn = geocode_address

    if not staging.address:
        logger.warning("Skipping staging record %s: no address", staging.id)
        return False

    # 1. Hash check
    new_hash = compute_staging_hash(staging)
    existing = session.execute(
        select(PropertyDetail).where(PropertyDetail.address == staging.address)
    ).scalar_one_or_none()

    if existing and existing.staging_hash == new_hash:
        return False

    # 2. Parse all fields
    sold_price = parse_price(staging.sold_price)
    listing_price = parse_price(staging.listing_price)
    price_per_sqft = parse_price(staging.price_per_sqft)
    lot_size_sqft = parse_lot_size_sqft(staging.lot_size)
    redfin_estimate = parse_price(staging.redfin_estimate)

    interior = extract_interior(staging.property_details)
    exterior = extract_exterior(staging.property_details)
    financial = extract_financial(staging.property_details, staging.tax_history)
    sale_hist = parse_sale_history(staging.sale_history)
    tax_hist = parse_tax_history(staging.tax_history)

    flood_score = map_climate_score(staging.climate_flood_factor)
    fire_score = map_climate_score(staging.climate_fire_factor)

    # Parse sold_date
    sold_date = None
    if staging.sold_date:
        for fmt in ("%B %d, %Y", "%Y-%m-%d", "%m/%d/%Y"):
            try:
                sold_date = datetime.strptime(staging.sold_date, fmt)
                break
            except ValueError:
                continue

    # 3. Geocode if needed
    location = None
    if existing and existing.location is not None:
        location = existing.location
    else:
        # The address field from the collector already contains the full
        # address (e.g. "211 Torrey Pines Dr, Cary, NC 27513").  Only
        # append city/state/zip when they are NOT already present to avoid
        # duplicates like "..., Cary, NC 27513, Cary, NC 27513".
        full_address = staging.address
        if staging.city and staging.city not in full_address:
            full_address += f", {staging.city}"
        if staging.state and staging.state not in full_address:
            full_address += f", {staging.state}"
        if staging.zip_code and staging.zip_code not in full_address:
            full_address += f" {staging.zip_code}"
        coords = geocode_fn(full_address)
        if coords:
            from geoalchemy2.shape import from_shape
            from shapely.geometry import Point

            location = from_shape(Point(coords[1], coords[0]), srid=4326)

    # 4. Upsert property_details
    if existing:
        prop = existing
    else:
        prop = PropertyDetail(address=staging.address)
        session.add(prop)

    prop.city = staging.city
    prop.state = staging.state
    prop.zip_code = staging.zip_code
    prop.location = location
    prop.listing_status = staging.listing_status
    prop.sold_date = sold_date
    prop.sold_price = sold_price
    prop.listing_price = listing_price
    prop.price_per_sqft = price_per_sqft
    prop.beds = staging.beds
    prop.baths = staging.baths
    prop.sqft = staging.sqft
    prop.lot_size_sqft = lot_size_sqft
    prop.year_built = staging.year_built
    prop.property_type = staging.listing_status  # best available
    prop.stories = None
    prop.description = staging.description
    prop.flooring = interior["flooring"]
    prop.appliances = interior["appliances"]
    prop.heating = interior["heating"]
    prop.cooling = interior["cooling"]
    prop.fireplace = interior["fireplace"]
    prop.basement = interior["basement"]
    prop.roof = exterior["roof"]
    prop.siding = exterior["siding"]
    prop.foundation = exterior["foundation"]
    prop.parking = exterior["parking"]
    prop.garage_spaces = exterior["garage_spaces"]
    prop.pool = exterior["pool"]
    prop.fence = exterior["fence"]
    prop.hoa_monthly = financial["hoa_monthly"]
    prop.tax_annual = financial["tax_annual"]
    prop.tax_year = financial["tax_year"]
    prop.assessed_value = financial["assessed_value"]
    prop.listing_agent = staging.listing_agent
    prop.listing_brokerage = staging.listing_brokerage
    prop.buying_agent = staging.buying_agent
    prop.buying_brokerage = staging.buying_brokerage
    prop.flood_risk = staging.climate_flood_factor
    prop.flood_score = flood_score
    prop.fire_risk = staging.climate_fire_factor
    prop.fire_score = fire_score
    prop.sale_history = sale_hist
    prop.tax_history = tax_hist
    prop.photo_s3_paths = staging.photo_s3_paths
    prop.staging_hash = new_hash

    session.flush()

    # 5. Upsert Redfin valuation
    if redfin_estimate is not None:
        existing_val = session.execute(
            select(PropertyValuation).where(
                PropertyValuation.property_id == prop.id,
                PropertyValuation.source == "redfin",
            )
        ).scalar_one_or_none()
        if existing_val:
            existing_val.value = redfin_estimate
        else:
            session.add(
                PropertyValuation(
                    property_id=prop.id,
                    source="redfin",
                    value=redfin_estimate,
                )
            )

    # 6. Parse schools and create linkages
    if staging.schools:
        # Remove existing linkages for this property
        session.execute(
            PropertySchool.__table__.delete().where(PropertySchool.property_id == prop.id)
        )
        session.flush()

        for school_data in staging.schools:
            school_name = school_data.get("name")
            if not school_name:
                continue

            desc_info = parse_school_desc(school_data.get("description"))
            school_type = desc_info.get("school_type") if desc_info else None
            grades = desc_info.get("grades") if desc_info else None
            distance = desc_info.get("distance_miles") if desc_info else None

            rating = school_data.get("rating")
            if isinstance(rating, str):
                try:
                    rating = float(rating)
                except ValueError:
                    rating = None

            school_id = upsert_school(
                session,
                name=school_name,
                school_type=school_type,
                rating=rating,
                grades=grades,
                lat=None,
                lon=None,
            )

            session.add(
                PropertySchool(
                    property_id=prop.id,
                    school_id=school_id,
                    distance_miles=distance,
                )
            )

    # 7. Enrich schools with addresses and travel times
    if location is not None:
        if enrich_fn is None:
            from pricepoint.data.housing.school_enrichment import enrich_property_schools

            enrich_fn = enrich_property_schools

        from geoalchemy2.shape import to_shape

        prop_point = to_shape(location)
        enrich_fn(session, prop.id, prop_point.y, prop_point.x)

    session.flush()
    return True


def transform_all_listings(batch_size: int = 100) -> dict[str, int]:
    """Transform all staging records in batches.

    Returns dict with 'transformed', 'skipped', 'errors' counts.
    """
    session = SessionLocal()
    stats: dict[str, int] = {"transformed": 0, "skipped": 0, "errors": 0}
    try:
        total = (
            session.execute(select(StagingRedfinListing.id).order_by(StagingRedfinListing.id))
            .scalars()
            .all()
        )

        for i in range(0, len(total), batch_size):
            batch_ids = total[i : i + batch_size]
            records = (
                session.execute(
                    select(StagingRedfinListing).where(StagingRedfinListing.id.in_(batch_ids))
                )
                .scalars()
                .all()
            )
            for record in records:
                try:
                    changed = transform_listing(session, record)
                    if changed:
                        stats["transformed"] += 1
                    else:
                        stats["skipped"] += 1
                except Exception:
                    logger.error("Error transforming staging record %s", record.id, exc_info=True)
                    stats["errors"] += 1
                    session.rollback()

            session.commit()
            logger.info(
                "Batch %d-%d complete: %s",
                i,
                i + len(batch_ids),
                stats,
            )

    finally:
        session.close()

    logger.info("Transform complete: %s", stats)
    return stats

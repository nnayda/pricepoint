"""Transform staging Redfin listings into production redfin_listings table.

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
    PropertyValuation,
    RedfinListing,
    RedfinPropertySchool,
    RedfinSchool,
    SaleHistoryRecord,
    StagingRedfinListing,
    TaxHistoryRecord,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Climate risk label <-> score mapping (1-6)
# ---------------------------------------------------------------------------
CLIMATE_LABEL_TO_SCORE: dict[str, int] = {
    "minimal": 1,
    "minor": 2,
    "moderate": 3,
    "major": 4,
    "severe": 5,
    "extreme": 6,
}

CLIMATE_SCORE_TO_LABEL: dict[int, str] = {v: k.title() for k, v in CLIMATE_LABEL_TO_SCORE.items()}

# ---------------------------------------------------------------------------
# Listing status normalization
# ---------------------------------------------------------------------------
LISTING_STATUS_MAP: dict[str, str] = {
    "sold": "SOLD",
    "off market": "SOLD",
    "for sale": "FOR SALE",
    "active": "FOR SALE",
    "contingent": "CONTINGENT",
    "pending": "PENDING",
    "coming soon": "COMING SOON",
    "for rent": "FOR RENT",
    "under contract": "UNDER CONTRACT",
}

# ---------------------------------------------------------------------------
# Num stories text -> float mapping
# ---------------------------------------------------------------------------
STORIES_MAP: dict[str, float] = {
    "one": 1.0,
    "one and one half": 1.5,
    "two": 2.0,
    "three": 3.0,
    "three or more": 3.0,
    "bi-level": 2.0,
    "multi/split": 2.0,
    "tri-level": 3.0,
}


# ---------------------------------------------------------------------------
# Pure parsing helpers
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


def parse_int(val: Any) -> int | None:
    """Safely parse a value to int, returning None on failure."""
    if val is None:
        return None
    with contextlib.suppress(ValueError, TypeError):
        return int(val)
    return None


def parse_float(val: Any) -> float | None:
    """Safely parse a value to float, returning None on failure."""
    if val is None:
        return None
    if isinstance(val, str):
        cleaned = re.sub(r"[^\d.\-]", "", val)
        if not cleaned:
            return None
        val = cleaned
    with contextlib.suppress(ValueError, TypeError):
        return float(val)
    return None


def parse_street_address(address: str | None) -> str | None:
    """Extract street address by stripping city, state, zipcode after first comma."""
    if not address:
        return None
    parts = address.split(",")
    return parts[0].strip() if parts else address


def normalize_listing_status(raw: str | None) -> str | None:
    """Map raw listing status to standardized value."""
    if not raw:
        return None
    return LISTING_STATUS_MAP.get(raw.strip().lower())


def parse_sold_date(raw: str | None) -> datetime | None:
    """Parse sold_date with multiple formats including month-only."""
    if not raw:
        return None
    raw = raw.strip()
    # Full date formats
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    # Month-only format: "JUN 2024" or "June 2024"
    for fmt in ("%b %Y", "%B %Y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def map_climate_score(risk_level: str | None) -> int | None:
    """Map climate risk level string to numeric score (1-6)."""
    if not risk_level:
        return None
    return CLIMATE_LABEL_TO_SCORE.get(risk_level.strip().lower())


def map_climate_label(risk_level: str | None) -> str | None:
    """Normalize climate risk level string to title-case label."""
    if not risk_level:
        return None
    score = CLIMATE_LABEL_TO_SCORE.get(risk_level.strip().lower())
    if score is not None:
        return CLIMATE_SCORE_TO_LABEL[score]
    return None


def _get_str(details: dict[str, Any], key: str) -> str | None:
    """Get a string value from details dict, returning None for non-strings."""
    val = details.get(key)
    return val if isinstance(val, str) else None


def _csv_list(details: dict[str, Any], key: str) -> list[str]:
    """Get a comma-separated value as a list of stripped strings."""
    val = details.get(key)
    if isinstance(val, str):
        return [v.strip() for v in val.split(",") if v.strip()]
    return []


def _contains_any(items: list[str] | str | None, targets: list[str]) -> bool:
    """Check if any target substring appears in any item in the list."""
    if items is None:
        return False
    if isinstance(items, str):
        items = [v.strip() for v in items.split(",")]
    for item in items:
        for target in targets:
            if target.lower() in item.lower():
                return True
    return False


# ---------------------------------------------------------------------------
# Per-field parsing functions (from property_details JSON)
# ---------------------------------------------------------------------------


def parse_has_garage(details: dict[str, Any]) -> bool:
    """True if property_details.garage == 'Yes'."""
    return (_get_str(details, "garage") or "").lower() == "yes"


def parse_num_garage_spaces(details: dict[str, Any]) -> int:
    """Parse property_details.garage_spaces, 0 if missing."""
    return parse_int(details.get("garage_spaces")) or 0


def parse_parking_type(details: dict[str, Any]) -> str | None:
    """Determine parking type from details, in order of precedence."""
    attached = (_get_str(details, "attached_garage") or "").lower()
    parking = (_get_str(details, "parking_features") or "").lower()

    if attached == "yes" or "attached" in parking:
        return "Attached Garage"
    if "detached" in parking:
        return "Detached Garage"
    if "carport" in parking or "covered" in parking:
        return "Carport"
    if "on street" in parking:
        return "Street"
    if (_get_str(details, "garage") or "").lower() == "yes":
        return "Garage"
    return None


def parse_garage_entry(details: dict[str, Any]) -> str | None:
    """Determine garage entry orientation from parking_features."""
    parking = (_get_str(details, "parking_features") or "").lower()
    if "garage faces front" in parking:
        return "Front"
    if "garage faces side" in parking:
        return "Side"
    if "garage faces rear" in parking:
        return "Rear"
    return None


def parse_driveway_surface(details: dict[str, Any]) -> str | None:
    """Determine driveway surface type from parking_features."""
    parking = (_get_str(details, "parking_features") or "").lower()
    paved_keywords = [
        "concrete",
        "parking pad",
        "paved",
        "asphalt",
        "paver block",
        "brick",
        "paver",
    ]
    unpaved_keywords = ["gravel", "unpaved", "dirt", "crushed stone", "stone"]
    if any(kw in parking for kw in paved_keywords):
        return "Paved"
    if any(kw in parking for kw in unpaved_keywords):
        return "Unpaved"
    return None


def parse_has_workshop(details: dict[str, Any]) -> bool:
    """True if parking_features or other_structures contains 'Workshop'."""
    parking = (_get_str(details, "parking_features") or "").lower()
    other = (_get_str(details, "other_structures") or "").lower()
    return "workshop in garage" in parking or "workshop" in other


def parse_has_circular_driveway(details: dict[str, Any]) -> bool:
    """True if parking_features contains 'Circular Driveway'."""
    return "circular driveway" in (_get_str(details, "parking_features") or "").lower()


def parse_has_ev_charging(details: dict[str, Any]) -> bool:
    """True if parking_features contains 'Electric Vehicle Charging Station(s)'."""
    parking = (_get_str(details, "parking_features") or "").lower()
    return "electric vehicle charging station(s)" in parking


def parse_has_fireplace(details: dict[str, Any]) -> bool:
    """True if property_details.fireplace == 'Yes'."""
    return (_get_str(details, "fireplace") or "").lower() == "yes"


def parse_water_heater_energy_source(details: dict[str, Any]) -> str:
    """Determine water heater energy source from appliances."""
    appliances = (_get_str(details, "appliances") or "").lower()
    if "gas water heater" in appliances or "propane water heater" in appliances:
        return "Gas"
    if "electric water heater" in appliances:
        return "Electric"
    if "solar hot water" in appliances:
        return "Solar"
    return "UNKNOWN"


def parse_cooktop_energy_source(details: dict[str, Any]) -> str | None:
    """Determine cooktop energy source from appliances."""
    appliances = (_get_str(details, "appliances") or "").lower()
    gas_keywords = [
        "gas cooktop",
        "gas range",
        "built-in gas range",
        "free-standing gas range",
        "propane cooktop",
    ]
    electric_keywords = [
        "electric range",
        "electric cooktop",
        "free-standing electric range",
        "induction cooktop",
        "built-in electric range",
    ]
    if any(kw in appliances for kw in gas_keywords):
        return "Gas"
    if any(kw in appliances for kw in electric_keywords):
        return "Electric"
    return None


def parse_oven_energy_source(details: dict[str, Any]) -> str:
    """Determine oven energy source from appliances."""
    appliances = (_get_str(details, "appliances") or "").lower()
    gas_keywords = ["gas oven", "free-standing gas oven"]
    electric_keywords = [
        "electric oven",
        "built-in electric oven",
        "built-in gas oven",
        "free-standing electric oven",
    ]
    if any(kw in appliances for kw in gas_keywords):
        return "Gas"
    if any(kw in appliances for kw in electric_keywords):
        return "Electric"
    return "UNKNOWN"


def parse_has_drink_fridge(details: dict[str, Any]) -> bool:
    """True if appliances contains wine/beverage fridge."""
    appliances = (_get_str(details, "appliances") or "").lower()
    return any(kw in appliances for kw in ["bar fridge", "wine refrigerator", "wine cooler"])


def parse_has_stainless_appliances(details: dict[str, Any]) -> bool:
    """True if appliances contains 'Stainless Steel Appliance(s)'."""
    return "stainless steel appliance(s)" in (_get_str(details, "appliances") or "").lower()


def parse_appliances_included_count(details: dict[str, Any]) -> int:
    """Count of included appliances (fridge, washer, dryer) from 0-3."""
    appliances = (_get_str(details, "appliances") or "").lower()
    count = 0
    fridge_keywords = ["refrigerator", "free-standing refrigerator", "built-in refrigerator"]
    washer_keywords = [
        "washer",
        "washer/dryer",
        "washer/dryer stacked",
        "energy star qualified washer",
    ]
    dryer_keywords = [
        "dryer",
        "washer/dryer",
        "washer/dryer stacked",
        "energy star qualified dryer",
    ]
    if any(kw in appliances for kw in fridge_keywords):
        count += 1
    if any(kw in appliances for kw in washer_keywords):
        count += 1
    if any(kw in appliances for kw in dryer_keywords):
        count += 1
    return count


def parse_has_efficient_windows(details: dict[str, Any]) -> bool:
    """True if window_features contains energy-efficient window types."""
    windows = (_get_str(details, "window_features") or "").lower()
    keywords = [
        "insulated windows",
        "double pane windows",
        "low-emissivity windows",
        "energy star qualified windows",
        "triple pane windows",
    ]
    return any(kw in windows for kw in keywords)


def parse_has_skylights(details: dict[str, Any]) -> bool:
    """True if window_features contains 'Skylight'."""
    return "skylight" in (_get_str(details, "window_features") or "").lower()


def parse_has_bay_window(details: dict[str, Any]) -> bool:
    """True if window_features contains 'Bay' or 'Garden'."""
    windows = (_get_str(details, "window_features") or "").lower()
    return "bay" in windows or "garden" in windows


def parse_laundry_location(details: dict[str, Any]) -> str:
    """Determine laundry location from laundry_features, in order of precedence."""
    laundry = (_get_str(details, "laundry_features") or "").lower()
    if "upper" in laundry:
        return "Upper"
    if "main" in laundry:
        return "Main"
    if "lower" in laundry or "basement" in laundry:
        return "Basement"
    if "garage" in laundry or "outside" in laundry:
        return "Garage/Out"
    return "Standard"


def parse_has_laundry_room(details: dict[str, Any]) -> bool:
    """True if laundry_features contains 'Laundry Room'."""
    return "laundry room" in (_get_str(details, "laundry_features") or "").lower()


def parse_has_utility_sink(details: dict[str, Any]) -> bool:
    """True if laundry_features contains 'Sink'."""
    return "sink" in (_get_str(details, "laundry_features") or "").lower()


def parse_countertop_material(details: dict[str, Any]) -> str:
    """Determine countertop material grade from interior_features."""
    interior = (_get_str(details, "interior_features") or "").lower()
    if "quartz counters" in interior:
        return "Ultra"
    if "granite counters" in interior or "stone counters" in interior:
        return "Premium"
    if "tile counters" in interior or "laminate counters" in interior:
        return "Standard"
    return "Unknown"


def parse_is_primary_downstairs(details: dict[str, Any]) -> bool:
    """True if interior_features contains 'Primary Downstairs'."""
    return "primary downstairs" in (_get_str(details, "interior_features") or "").lower()


def parse_has_guest_suite(details: dict[str, Any]) -> bool:
    """True if interior_features contains in-law/guest suite indicators."""
    interior = (_get_str(details, "interior_features") or "").lower()
    return any(
        kw in interior
        for kw in [
            "in-law floorplan",
            "second primary bedroom",
            "apartment/suite, room over garage",
        ]
    )


def parse_has_butler_pantry(details: dict[str, Any]) -> bool:
    """True if interior_features contains \"Butler's Pantry\"."""
    return "butler's pantry" in (_get_str(details, "interior_features") or "").lower()


def parse_has_walkin_closets(details: dict[str, Any]) -> bool:
    """True if interior_features contains 'Walk-In Closet(s)'."""
    return "walk-in closet(s)" in (_get_str(details, "interior_features") or "").lower()


def parse_has_tall_ceilings(details: dict[str, Any]) -> bool:
    """True if interior_features contains high/vaulted/cathedral ceilings."""
    interior = (_get_str(details, "interior_features") or "").lower()
    return any(
        kw in interior for kw in ["high ceilings", "vaulted ceiling(s)", "cathedral ceiling(s)"]
    )


def parse_has_luxury_ceilings(details: dict[str, Any]) -> bool:
    """True if interior_features contains tray/coffered/beamed ceilings."""
    interior = (_get_str(details, "interior_features") or "").lower()
    return any(
        kw in interior for kw in ["tray ceiling(s)", "coffered ceiling(s)", "beamed ceilings"]
    )


def parse_has_sauna(details: dict[str, Any]) -> bool:
    """True if interior_features contains 'Sauna'."""
    return "sauna" in (_get_str(details, "interior_features") or "").lower()


def parse_has_bar(details: dict[str, Any]) -> bool:
    """True if interior_features contains 'Bar'."""
    return "bar" in (_get_str(details, "interior_features") or "").lower()


def parse_has_second_primary(details: dict[str, Any]) -> bool:
    """True if interior_features contains 'Second Primary Bedroom'."""
    return "second primary bedroom" in (_get_str(details, "interior_features") or "").lower()


def parse_has_room_over_garage(details: dict[str, Any]) -> bool:
    """True if interior_features contains 'Room Over Garage'."""
    return "room over garage" in (_get_str(details, "interior_features") or "").lower()


def parse_has_open_floorplan(details: dict[str, Any]) -> bool:
    """True if interior_features contains 'Open Floorplan'."""
    return "open floorplan" in (_get_str(details, "interior_features") or "").lower()


def parse_has_outdoor_fireplace(details: dict[str, Any]) -> bool:
    """True if fireplace_features contains 'Outside' or 'Fire Pit'."""
    features = (_get_str(details, "fireplace_features") or "").lower()
    return "outside" in features or "fire pit" in features


def parse_has_primary_fireplace(details: dict[str, Any]) -> bool:
    """True if fireplace_features contains primary bedroom/bath indicators."""
    features = (_get_str(details, "fireplace_features") or "").lower()
    return any(kw in features for kw in ["primary bedroom", "bedroom", "bath"])


def parse_has_architectural_fireplace(details: dict[str, Any]) -> bool:
    """True if fireplace_features contains 'Double Sided' or 'See Through'."""
    features = (_get_str(details, "fireplace_features") or "").lower()
    return "double sided" in features or "see through" in features


def parse_fireplace_fuel_source(details: dict[str, Any]) -> str:
    """Determine fireplace fuel source from fireplace_features."""
    features = (_get_str(details, "fireplace_features") or "").lower()
    gas_keywords = ["gas log", "gas", "sealed combustion", "propane"]
    wood_keywords = ["wood burning", "masonry", "wood burning stove"]
    # Check gas first (in precedence order)
    if any(kw in features for kw in gas_keywords):
        return "Gas"
    if any(kw in features for kw in wood_keywords):
        return "Wood"
    if "electric" in features:
        return "Electric"
    return "Unknown"


def parse_num_fireplaces(details: dict[str, Any]) -> int:
    """Parse property_details.fireplaces_total, 0 if missing."""
    return parse_int(details.get("fireplaces_total")) or 0


def parse_is_carpet_free(details: dict[str, Any]) -> bool:
    """True if flooring does not contain 'Carpet'."""
    flooring = (_get_str(details, "flooring") or "").lower()
    return "carpet" not in flooring


def parse_has_premium_stone(details: dict[str, Any]) -> bool:
    """True if flooring contains premium stone types."""
    flooring = (_get_str(details, "flooring") or "").lower()
    return any(kw in flooring for kw in ["marble", "slate", "granite", "stone"])


def parse_has_hardwood(details: dict[str, Any]) -> bool:
    """True if flooring contains hardwood types."""
    flooring = (_get_str(details, "flooring") or "").lower()
    keywords = ["wood", "bamboo", "parquet", "cork", "fsc or sfi certified source hardwood"]
    return any(kw in flooring for kw in keywords)


def parse_has_crawl_space(details: dict[str, Any]) -> bool:
    """True if property_details.crawl_space == 'Yes'."""
    return (_get_str(details, "crawl_space") or "").lower() == "yes"


def parse_facade_type(details: dict[str, Any]) -> str | None:
    """Determine facade type from construction_materials, in order of precedence."""
    materials = (_get_str(details, "construction_materials") or "").lower()
    masonry = ["brick", "stone", "stucco", "block", "plaster"]
    fiber_cement = ["fiber cement", "hardiplank", "cement"]
    synthetic = ["vinyl", "metal", "aluminum"]
    wood = [
        "masonite",
        "wood",
        "cedar",
        "shake",
        "log",
        "board & batten siding",
        "lap siding",
    ]
    if any(kw in materials for kw in masonry):
        return "Masonry"
    if any(kw in materials for kw in fiber_cement):
        return "Fiber Cement"
    if any(kw in materials for kw in synthetic):
        return "Synthetic"
    if any(kw in materials for kw in wood):
        return "Wood"
    return None


def parse_building_area(details: dict[str, Any]) -> float | None:
    """Parse property_details.building_area_total."""
    return parse_float(details.get("building_area_total"))


def parse_above_grade_finished_area(details: dict[str, Any]) -> float | None:
    """Parse property_details.above_grade_finished_area."""
    return parse_float(details.get("above_grade_finished_area"))


def parse_below_grade_finished_area(details: dict[str, Any]) -> float | None:
    """Parse property_details.below_grade_finished_area."""
    return parse_float(details.get("below_grade_finished_area"))


def parse_num_stories(details: dict[str, Any]) -> float | None:
    """Parse num_stories from stories or levels fields.

    Tries numeric parse first, then maps text values.
    """
    # Try stories first
    val = details.get("stories")
    if val is not None:
        result = parse_float(val)
        if result is not None:
            return result
        # Try text mapping
        if isinstance(val, str):
            mapped = STORIES_MAP.get(val.strip().lower())
            if mapped is not None:
                return mapped

    # Fall back to levels
    val = details.get("levels")
    if val is not None:
        result = parse_float(val)
        if result is not None:
            return result
        if isinstance(val, str):
            mapped = STORIES_MAP.get(val.strip().lower())
            if mapped is not None:
                return mapped
    return None


def parse_lot_size_acres(details: dict[str, Any]) -> float | None:
    """Parse lot size in acres from multiple fallback fields."""
    # 1. lot_size_acres
    val = parse_float(details.get("lot_size_acres"))
    if val is not None:
        return val

    # 2. lot_size (may be in various formats)
    lot_str = _get_str(details, "lot_size")
    if lot_str:
        text = lot_str.strip().lower()
        acres_match = re.search(r"([\d,.]+)\s*acres?", text)
        if acres_match:
            result = parse_float(acres_match.group(1).replace(",", ""))
            if result is not None:
                return result
        sqft_match = re.search(r"([\d,.]+)\s*sq", text)
        if sqft_match:
            result = parse_float(sqft_match.group(1).replace(",", ""))
            if result is not None:
                return result / 43560.0

    # 3. lot_size_square_feet
    val = parse_float(details.get("lot_size_square_feet"))
    if val is not None:
        return val / 43560.0

    # 4. lot_size_area + lot_size_units
    area = parse_float(details.get("lot_size_area"))
    if area is not None:
        units = (_get_str(details, "lot_size_units") or "").lower()
        if "sq" in units or "feet" in units:
            return area / 43560.0
        # Default to acres
        return area

    return None


def parse_lot_size_from_staging(lot_str: str | None) -> float | None:
    """Parse staging lot_size string to acres.

    Handles 'X.XX Acres' and 'X,XXX Sq. Ft.' formats.
    """
    if not lot_str:
        return None
    text = lot_str.strip().lower()
    acres_match = re.search(r"([\d,.]+)\s*acres?", text)
    if acres_match:
        with contextlib.suppress(ValueError):
            return float(acres_match.group(1).replace(",", ""))
    sqft_match = re.search(r"([\d,.]+)\s*sq", text)
    if sqft_match:
        with contextlib.suppress(ValueError):
            sqft = float(sqft_match.group(1).replace(",", ""))
            return sqft / 43560.0
    return None


def parse_is_waterfront(details: dict[str, Any]) -> bool:
    """True if waterfront property."""
    if (_get_str(details, "waterfront") or "").lower() == "yes":
        return True
    features = (_get_str(details, "features") or "").lower()
    return "waterfront" in features


def parse_is_septic(details: dict[str, Any]) -> bool:
    """True if sewer contains 'Septic' or 'Private Sewer'."""
    sewer = (_get_str(details, "sewer") or "").lower()
    return "septic" in sewer or "private sewer" in sewer


def parse_is_well_water(details: dict[str, Any]) -> bool:
    """True if water_source contains 'Well' or 'Private'."""
    water = (_get_str(details, "water_source") or "").lower()
    return "well" in water or "private" in water


def parse_no_heating(details: dict[str, Any]) -> bool:
    """True if heating is explicitly 'No'."""
    return (_get_str(details, "heating") or "").lower() == "no"


def parse_no_cooling(details: dict[str, Any]) -> bool:
    """True if cooling is explicitly 'No'."""
    return (_get_str(details, "cooling") or "").lower() == "no"


def parse_has_hoa(details: dict[str, Any]) -> bool:
    """True if association == 'Yes'."""
    return (_get_str(details, "association") or "").lower() == "yes"


def parse_has_enclosed_porch(details: dict[str, Any]) -> bool:
    """True if patio_and_porch_features contains 'Screened' or 'Enclosed'."""
    patio = (_get_str(details, "patio_and_porch_features") or "").lower()
    return "screened" in patio or "enclosed" in patio


def parse_has_front_porch(details: dict[str, Any]) -> bool:
    """True if patio_and_porch_features contains 'Front Porch' or 'Wrap Around'."""
    patio = (_get_str(details, "patio_and_porch_features") or "").lower()
    return "front porch" in patio or "wrap around" in patio


def parse_has_fenced_yard(details: dict[str, Any]) -> bool:
    """True if property has a fenced yard (not invisible/partial/electric fence)."""
    fencing = _get_str(details, "fencing")
    if fencing:
        fencing_lower = fencing.lower()
        excluded = ["none", "invisible", "partial", "electric"]
        if not any(ex in fencing_lower for ex in excluded):
            return True
    exterior = (_get_str(details, "exterior_features") or "").lower()
    return any(kw in exterior for kw in ["fence", "private yard", "dog run"])


def parse_has_outdoor_kitchen(details: dict[str, Any]) -> bool:
    """True if property has an outdoor kitchen."""
    exterior = (_get_str(details, "exterior_features") or "").lower()
    other = (_get_str(details, "other_structures") or "").lower()
    return (
        any(kw in exterior for kw in ["kitchen", "built-in barbecue", "gas grill"])
        or "outdoor kitchen" in other
    )


def parse_has_sport_court(details: dict[str, Any]) -> bool:
    """True if property has a sport court."""
    exterior = (_get_str(details, "exterior_features") or "").lower()
    return any(kw in exterior for kw in ["tennis court(s)", "basketball court", "arena"])


def parse_has_private_pool(details: dict[str, Any]) -> bool:
    """True if property has a private pool."""
    exterior = (_get_str(details, "exterior_features") or "").lower()
    features = (_get_str(details, "features") or "").lower()
    pool = (_get_str(details, "pool_features") or "").lower()

    if "pool" in exterior:
        return True
    if "pool" in features:
        return True
    if pool:
        community_keywords = ["swimming pool com/fee", "community", "association", "none"]
        if not any(kw in pool for kw in community_keywords):
            return True
    return False


def parse_has_community_pool(details: dict[str, Any]) -> bool:
    """True if property has access to a community pool."""
    community = (_get_str(details, "community_features") or "").lower()
    pool = (_get_str(details, "pool_features") or "").lower()
    assoc = (_get_str(details, "association_amenities") or "").lower()

    if "pool" in community:
        return True
    if any(kw in pool for kw in ["swimming pool com/fee", "community", "association"]):
        return True
    return "pool" in assoc


def parse_has_clubhouse(details: dict[str, Any]) -> bool:
    """True if property has a community clubhouse."""
    community = (_get_str(details, "community_features") or "").lower()
    assoc = (_get_str(details, "association_amenities") or "").lower()

    if "clubhouse" in community:
        return True
    return any(kw in assoc for kw in ["clubhouse", "recreation facilities", "fitness center"])


def parse_has_exterior_storage(details: dict[str, Any]) -> bool:
    """True if property has exterior storage buildings."""
    other = (_get_str(details, "other_structures") or "").lower()
    exterior = (_get_str(details, "exterior_features") or "").lower()

    storage_other = ["shed", "storage", "workshop", "outbuilding", "barn", "second garage"]
    storage_ext = ["storage", "barn", "equestrian facilities", "outbuilding", "shed", "stable"]

    return any(kw in other for kw in storage_other) or any(kw in exterior for kw in storage_ext)


def parse_has_garden(details: dict[str, Any]) -> bool:
    """True if property has a garden or greenhouse."""
    exterior = (_get_str(details, "exterior_features") or "").lower()
    other = (_get_str(details, "other_structures") or "").lower()
    return "garden" in exterior or "greenhouse" in exterior or "greenhouse" in other


def parse_association_fee_yearly(details: dict[str, Any]) -> float | None:
    """Parse and sum association fees, converting to yearly amount."""
    total = 0.0
    has_fee = False

    # Fee 1
    fee1 = parse_price(_get_str(details, "association_fee"))
    if fee1 is not None:
        freq1 = (_get_str(details, "association_fee_frequency") or "Monthly").strip()
        total += _fee_to_yearly(fee1, freq1)
        has_fee = True

    # Fee 2
    fee2 = parse_price(_get_str(details, "association_fee_2"))
    if fee2 is not None:
        freq2 = (_get_str(details, "association_fee_2_frequency") or "Monthly").strip()
        total += _fee_to_yearly(fee2, freq2)
        has_fee = True

    # HOA dues fallback
    if not has_fee:
        hoa = parse_price(_get_str(details, "hoa_dues"))
        if hoa is not None:
            total += _fee_to_yearly(hoa, "Monthly")
            has_fee = True

    return total if has_fee else None


def _fee_to_yearly(amount: float, frequency: str) -> float:
    """Convert a fee amount to yearly based on frequency."""
    freq_lower = frequency.lower()
    if "semi" in freq_lower:
        return amount * 2
    if "annual" in freq_lower or "year" in freq_lower:
        return amount
    if "quarter" in freq_lower:
        return amount * 4
    # Default: monthly
    return amount * 12


def parse_apn(details: dict[str, Any]) -> str | None:
    """Parse APN, returning None for non-APN values like 'See Plat'."""
    val = _get_str(details, "apn")
    if not val:
        return None
    # Filter out non-APN placeholder values
    lower = val.strip().lower()
    non_apn = ["see plat", "see map", "n/a", "na", "none", "tbd", "pending"]
    if lower in non_apn:
        return None
    return val.strip()


def parse_contract_date(details: dict[str, Any]) -> datetime | None:
    """Parse contract status change date."""
    val = _get_str(details, "contract_status_change_date")
    return parse_sold_date(val)  # Same date parsing logic


def parse_num_parking_spaces(details: dict[str, Any]) -> int | None:
    """Parse total parking spaces."""
    val = parse_int(details.get("parking_total"))
    if val is not None:
        return val
    return parse_int(details.get("parking_spaces"))


def parse_year_built(staging: StagingRedfinListing, details: dict[str, Any]) -> int | None:
    """Parse year_built with staging fallback to property_details."""
    if staging.year_built is not None:
        return staging.year_built
    return parse_int(details.get("year_built"))


def parse_num_beds(staging: StagingRedfinListing, details: dict[str, Any]) -> int | None:
    """Parse beds with multiple fallbacks."""
    if staging.beds is not None:
        return staging.beds
    val = parse_int(details.get("beds"))
    if val is not None:
        return val
    return parse_int(details.get("num_of_bedrooms"))


def parse_num_baths(staging: StagingRedfinListing, details: dict[str, Any]) -> float | None:
    """Parse baths with multiple fallbacks."""
    if staging.baths is not None:
        return staging.baths
    val = parse_float(details.get("baths"))
    if val is not None:
        return val
    full = parse_float(details.get("num_of_full_bathrooms"))
    half = parse_float(details.get("num_of_half_bathrooms"))
    if full is not None or half is not None:
        return (full or 0) + (half or 0)
    return None


def parse_sqft(staging: StagingRedfinListing, details: dict[str, Any]) -> int | None:
    """Parse sqft with multiple fallbacks."""
    if staging.sqft is not None:
        return staging.sqft
    val = parse_int(details.get("building_area_total"))
    if val is not None:
        return val
    val = parse_int(details.get("living_area"))
    if val is not None:
        return val
    return None


def parse_price_per_sqft(
    staging: StagingRedfinListing,
    listing_price: float | None,
    sqft: int | None,
) -> float | None:
    """Parse price_per_sqft with calculated fallback."""
    val = parse_price(staging.price_per_sqft)
    if val is not None:
        return val
    if listing_price is not None and sqft is not None and sqft > 0:
        return round(listing_price / sqft, 2)
    return None


def parse_location_from_details(details: dict[str, Any]) -> tuple[float, float] | None:
    """Try to extract lat/lon from property_details JSON."""
    lat = parse_float(details.get("latitude"))
    lon = parse_float(details.get("longitude"))
    if lat is not None and lon is not None:
        return (lat, lon)
    return None


# ---------------------------------------------------------------------------
# Sale / tax history parsing
# ---------------------------------------------------------------------------


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


def parse_sale_date(date_str: str | None) -> datetime | None:
    """Parse a sale history date to datetime."""
    if not date_str:
        return None
    normalized = _normalize_date(date_str)
    if normalized:
        try:
            return datetime.strptime(normalized, "%Y-%m-%d")
        except ValueError:
            return None
    return None


def parse_tax_date(year: Any) -> datetime | None:
    """Parse a tax year to Jan 1 of that year."""
    yr = parse_int(year)
    if yr is not None:
        return datetime(yr, 1, 1)
    return None


def parse_school_desc(desc: str | None) -> dict[str, Any] | None:
    """Parse a school description like 'Public, PreK-5 Assigned 0.3mi'.

    Returns dict with school_type, grades or None.
    """
    if not desc:
        return None

    result: dict[str, Any] = {"school_type": None, "grades": None}

    parts = [p.strip() for p in desc.split(",")]
    if parts:
        result["school_type"] = parts[0]

    if len(parts) > 1:
        grade_part = parts[1].strip()
        grade_part = re.sub(r"\s+(Assigned|Choice|Nearby)\b.*", "", grade_part, flags=re.IGNORECASE)
        grade_part = re.sub(r"\s+[\d.]+\s*mi.*", "", grade_part)
        if grade_part.strip():
            result["grades"] = grade_part.strip()

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
) -> int:
    """Deduplicate school on (name, school_type). Returns school_id."""
    stmt = select(RedfinSchool).where(
        RedfinSchool.name == name, RedfinSchool.school_type == school_type
    )
    existing = session.execute(stmt).scalar_one_or_none()
    if existing:
        if rating is not None:
            existing.rating = rating
        if grades is not None:
            existing.grades = grades
        session.flush()
        return existing.id

    school = RedfinSchool(
        name=name,
        school_type=school_type,
        rating=rating,
        grades=grades,
    )
    session.add(school)
    session.flush()
    return school.id


def transform_listing(
    session: Session,
    staging: StagingRedfinListing,
    geocode_fn: Any = None,
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
    street_address = parse_street_address(staging.address)

    existing = session.execute(
        select(RedfinListing).where(
            RedfinListing.street_address == street_address,
            RedfinListing.city == staging.city,
            RedfinListing.state == staging.state,
            RedfinListing.zip_code == staging.zip_code,
        )
    ).scalar_one_or_none()

    if existing and existing.staging_hash == new_hash:
        return False

    # 2. Parse property_details JSON
    details: dict[str, Any] = staging.property_details or {}

    # Parse scalar fields from staging
    sold_price = parse_price(staging.sold_price)
    listing_price = parse_price(staging.listing_price)
    redfin_estimate = parse_price(staging.redfin_estimate)
    sold_date = parse_sold_date(staging.sold_date)

    # Parse stats with fallbacks
    year_built = parse_year_built(staging, details)
    num_beds = parse_num_beds(staging, details)
    num_baths = parse_num_baths(staging, details)
    sqft = parse_sqft(staging, details)
    price_per_sqft = parse_price_per_sqft(staging, listing_price, sqft)

    # Lot size: try property_details first, then staging lot_size
    lot_size = parse_lot_size_acres(details)
    if lot_size is None:
        lot_size = parse_lot_size_from_staging(staging.lot_size)

    # Climate scores
    flood_score = map_climate_score(staging.climate_flood_factor)
    fire_score = map_climate_score(staging.climate_fire_factor)
    flood_factor = map_climate_label(staging.climate_flood_factor)
    fire_factor = map_climate_label(staging.climate_fire_factor)

    # 3. Resolve location
    location: Any = None
    if existing and existing.location is not None:
        location = existing.location
    else:
        # Try property_details lat/lon first
        coords = parse_location_from_details(details)
        if coords is None:
            # Geocode the full address
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

    # 4. Upsert redfin_listings
    if existing:
        prop = existing
    else:
        prop = RedfinListing(
            street_address=street_address or "",
            city=staging.city,
            state=staging.state,
            zip_code=staging.zip_code,
        )
        session.add(prop)

    # Location
    prop.location = location
    prop.listing_status = normalize_listing_status(staging.listing_status)
    prop.sold_date = sold_date
    prop.sold_price = sold_price
    prop.listing_price = listing_price
    prop.description = staging.description

    # Climate
    prop.flood_factor = flood_factor
    prop.fire_factor = fire_factor
    prop.flood_score = flood_score
    prop.fire_score = fire_score

    # Parking
    prop.has_garage = parse_has_garage(details)
    prop.num_garage_spaces = parse_num_garage_spaces(details)
    prop.parking_type = parse_parking_type(details)
    prop.garage_entry = parse_garage_entry(details)
    prop.driveway_surface = parse_driveway_surface(details)
    prop.has_workshop = parse_has_workshop(details)
    prop.has_circular_driveway = parse_has_circular_driveway(details)
    prop.has_ev_charging = parse_has_ev_charging(details)
    prop.num_parking_spaces = parse_num_parking_spaces(details)

    # Fireplace
    prop.has_fireplace = parse_has_fireplace(details)
    prop.has_outdoor_fireplace = parse_has_outdoor_fireplace(details)
    prop.has_primary_fireplace = parse_has_primary_fireplace(details)
    prop.has_architectural_fireplace = parse_has_architectural_fireplace(details)
    prop.fireplace_fuel_source = parse_fireplace_fuel_source(details)
    prop.num_fireplaces = parse_num_fireplaces(details)

    # Appliances / energy
    prop.water_heater_energy_source = parse_water_heater_energy_source(details)
    prop.cooktop_energy_source = parse_cooktop_energy_source(details)
    prop.oven_energy_source = parse_oven_energy_source(details)
    prop.has_drink_fridge = parse_has_drink_fridge(details)
    prop.has_stainless_appliances = parse_has_stainless_appliances(details)
    prop.appliances_included_count = parse_appliances_included_count(details)

    # Windows
    prop.has_efficient_windows = parse_has_efficient_windows(details)
    prop.has_skylights = parse_has_skylights(details)
    prop.has_bay_window = parse_has_bay_window(details)

    # Laundry
    prop.laundry_location = parse_laundry_location(details)
    prop.has_laundry_room = parse_has_laundry_room(details)
    prop.has_utility_sink = parse_has_utility_sink(details)

    # Interior features
    prop.countertop_material = parse_countertop_material(details)
    prop.is_primary_downstairs = parse_is_primary_downstairs(details)
    prop.has_guest_suite = parse_has_guest_suite(details)
    prop.has_butler_pantry = parse_has_butler_pantry(details)
    prop.has_walkin_closets = parse_has_walkin_closets(details)
    prop.has_tall_ceilings = parse_has_tall_ceilings(details)
    prop.has_luxury_ceilings = parse_has_luxury_ceilings(details)
    prop.has_sauna = parse_has_sauna(details)
    prop.has_bar = parse_has_bar(details)
    prop.has_second_primary = parse_has_second_primary(details)
    prop.has_room_over_garage = parse_has_room_over_garage(details)
    prop.has_open_floorplan = parse_has_open_floorplan(details)

    # Flooring
    prop.is_carpet_free = parse_is_carpet_free(details)
    prop.has_premium_stone = parse_has_premium_stone(details)
    prop.has_hardwood = parse_has_hardwood(details)
    prop.has_crawl_space = parse_has_crawl_space(details)

    # Exterior / structure
    prop.facade_type = parse_facade_type(details)
    prop.building_area = parse_building_area(details)
    prop.above_grade_finished_area = parse_above_grade_finished_area(details)
    prop.below_grade_finished_area = parse_below_grade_finished_area(details)
    prop.num_stories = parse_num_stories(details)
    prop.lot_size = lot_size
    prop.is_waterfront = parse_is_waterfront(details)
    prop.buyer_financing = _get_str(details, "buyer_financing")

    # Utilities
    prop.is_septic = parse_is_septic(details)
    prop.is_well_water = parse_is_well_water(details)
    prop.no_heating = parse_no_heating(details)
    prop.no_cooling = parse_no_cooling(details)

    # HOA / community
    prop.has_hoa = parse_has_hoa(details)
    prop.association_fee = parse_association_fee_yearly(details)
    prop.hoa_name = _get_str(details, "association_name")

    # Porch / outdoor
    prop.has_enclosed_porch = parse_has_enclosed_porch(details)
    prop.has_front_porch = parse_has_front_porch(details)
    prop.has_fenced_yard = parse_has_fenced_yard(details)
    prop.has_outdoor_kitchen = parse_has_outdoor_kitchen(details)
    prop.has_sport_court = parse_has_sport_court(details)
    prop.has_private_pool = parse_has_private_pool(details)
    prop.has_community_pool = parse_has_community_pool(details)
    prop.has_clubhouse = parse_has_clubhouse(details)
    prop.has_exterior_storage = parse_has_exterior_storage(details)
    prop.has_garden = parse_has_garden(details)

    # Core stats
    prop.year_built = year_built
    prop.year_renovated = parse_int(details.get("year_renovated"))
    prop.num_beds = num_beds
    prop.num_baths = num_baths
    prop.sqft = sqft
    prop.price_per_sqft = price_per_sqft

    # Agents
    prop.listing_agent = staging.listing_agent
    prop.listing_brokerage = staging.listing_brokerage
    prop.buying_agent = staging.buying_agent
    prop.buying_brokerage = staging.buying_brokerage

    # Identifiers
    prop.apn = parse_apn(details)
    prop.contract_date = parse_contract_date(details)

    # Raw data for UI
    prop.property_details = staging.property_details

    # Photos and source
    prop.property_photos = staging.photo_s3_paths
    prop.source_file = staging.source_file
    prop.redfin_url = staging.redfin_url

    # Change detection
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
            existing_val.estimated_at = staging.loaded_at
        else:
            session.add(
                PropertyValuation(
                    property_id=prop.id,
                    source="redfin",
                    value=redfin_estimate,
                    estimated_at=staging.loaded_at,
                )
            )

    # 6. Write sale history records
    session.execute(
        SaleHistoryRecord.__table__.delete().where(  # type: ignore[attr-defined]
            SaleHistoryRecord.property_id == prop.id
        )
    )
    session.flush()
    if staging.sale_history:
        for entry in staging.sale_history:  # type: ignore[attr-defined]
            date_val = parse_sale_date(entry.get("date"))
            price_val = parse_price(str(entry.get("price", ""))) if entry.get("price") else None
            event_type = entry.get("event") or entry.get("event_type")
            session.add(
                SaleHistoryRecord(
                    property_id=prop.id,
                    date=date_val,
                    event=(event_type.upper() if event_type else None),
                    price=price_val,
                    source="Redfin",
                )
            )

    # 7. Write tax history records
    session.execute(
        TaxHistoryRecord.__table__.delete().where(  # type: ignore[attr-defined]
            TaxHistoryRecord.property_id == prop.id
        )
    )
    session.flush()
    if staging.tax_history:
        for entry in staging.tax_history:  # type: ignore[attr-defined]
            date_val = parse_tax_date(entry.get("year"))
            session.add(
                TaxHistoryRecord(
                    property_id=prop.id,
                    date=date_val,
                    property_tax=(
                        parse_price(str(entry.get("tax", ""))) if entry.get("tax") else None
                    ),
                    assessment_value_land=(
                        parse_price(str(entry.get("land", ""))) if entry.get("land") else None
                    ),
                    assessment_value_additions=(
                        parse_price(str(entry.get("additions", "")))
                        if entry.get("additions")
                        else None
                    ),
                    assessment_value=(
                        parse_price(str(entry.get("assessed_value", "")))
                        if entry.get("assessed_value")
                        else None
                    ),
                    source="Redfin",
                )
            )

    # 8. Parse schools and create linkages (bronze layer)
    if staging.schools:
        session.execute(
            RedfinPropertySchool.__table__.delete().where(  # type: ignore[attr-defined]
                RedfinPropertySchool.property_id == prop.id
            )
        )
        session.flush()

        for school_data in staging.schools:  # type: ignore[attr-defined]
            school_name = school_data.get("name")
            if not school_name:
                continue

            desc_info = parse_school_desc(school_data.get("description"))
            school_type = desc_info.get("school_type") if desc_info else None
            grades = desc_info.get("grades") if desc_info else None

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
            )

            session.add(
                RedfinPropertySchool(
                    property_id=prop.id,
                    redfin_school_id=school_id,
                )
            )

    session.flush()
    return True


def transform_all_listings(
    batch_size: int = 100,
    *,
    force_rebuild: bool = False,
) -> dict[str, int]:
    """Transform staging records in batches.

    By default only processes unprocessed staging records.  Pass
    ``force_rebuild=True`` to reprocess every staging row regardless
    of its ``is_processed`` flag.

    Returns dict with 'transformed', 'skipped', 'errors' counts.
    """
    session = SessionLocal()
    stats: dict[str, int] = {"transformed": 0, "skipped": 0, "errors": 0}
    try:
        stmt = select(StagingRedfinListing.id).order_by(StagingRedfinListing.id)
        if not force_rebuild:
            stmt = stmt.where(StagingRedfinListing.is_processed.is_(False))

        total = session.execute(stmt).scalars().all()

        if not total:
            logger.info("No staging records to process")
            return stats

        logger.info(
            "Processing %d staging records (force_rebuild=%s)",
            len(total),
            force_rebuild,
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
                    record.is_processed = True
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

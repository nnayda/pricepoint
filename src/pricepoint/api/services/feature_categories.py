"""Feature category grouping for comparable property display.

Maps the ~70 feature columns from the assembled feature matrix to 17
human-readable categories based on FEATURE_CATALOG.md.
"""

from __future__ import annotations

FEATURE_CATEGORIES: dict[str, list[str]] = {
    "Core Stats": [
        "property_age",
        "is_renovated",
        "years_since_renovation",
        "bed_bath_ratio",
        "sqft_per_bedroom",
        "lot_to_building_ratio",
    ],
    "Climate Risk": [
        "flood_score",
        "fire_score",
    ],
    "Parking": [
        "has_garage",
        "num_garage_spaces",
        "parking_type",
        "garage_entry",
        "driveway_surface",
        "has_workshop",
        "has_circular_driveway",
        "has_ev_charging",
        "num_parking_spaces",
    ],
    "Fireplace": [
        "has_fireplace",
        "has_outdoor_fireplace",
        "has_primary_fireplace",
        "has_architectural_fireplace",
        "fireplace_fuel_source",
        "num_fireplaces",
    ],
    "Appliances & Energy": [
        "water_heater_energy_source",
        "cooktop_energy_source",
        "oven_energy_source",
        "has_drink_fridge",
        "has_stainless_appliances",
        "appliances_included_count",
    ],
    "Windows": [
        "has_efficient_windows",
        "has_skylights",
        "has_bay_window",
    ],
    "Laundry": [
        "laundry_location",
        "has_laundry_room",
        "has_utility_sink",
    ],
    "Interior Features": [
        "countertop_material",
        "is_primary_downstairs",
        "has_guest_suite",
        "has_butler_pantry",
        "has_walkin_closets",
        "has_tall_ceilings",
        "has_luxury_ceilings",
        "has_sauna",
        "has_bar",
        "has_second_primary",
        "has_room_over_garage",
        "has_open_floorplan",
    ],
    "Flooring": [
        "is_carpet_free",
        "has_premium_stone",
        "has_hardwood",
        "has_crawl_space",
    ],
    "Exterior & Structure": [
        "facade_type",
        "is_waterfront",
    ],
    "Utilities": [
        "is_septic",
        "is_well_water",
        "no_heating",
        "no_cooling",
    ],
    "HOA & Community": [
        "has_hoa",
        "association_fee",
    ],
    "Porch & Outdoor": [
        "has_enclosed_porch",
        "has_front_porch",
        "has_fenced_yard",
        "has_outdoor_kitchen",
        "has_sport_court",
        "has_private_pool",
        "has_community_pool",
        "has_clubhouse",
        "has_exterior_storage",
        "has_garden",
    ],
    "Luxury & Amenity Scores": [
        "luxury_feature_count",
        "amenity_score",
    ],
    "Sale History": [
        "years_since_last_sale",
        "decayed_sale_signal",
    ],
}

# Reverse lookup: feature column → category name
_FEATURE_TO_CATEGORY: dict[str, str] = {}
for _cat, _cols in FEATURE_CATEGORIES.items():
    for _col in _cols:
        _FEATURE_TO_CATEGORY[_col] = _cat


def group_features(feature_row: dict[str, object]) -> dict[str, dict[str, object]]:
    """Group a flat feature dict into category → {feature: value} buckets.

    Features not in any known category are collected under "Other".
    """
    groups: dict[str, dict[str, object]] = {}
    for col, val in feature_row.items():
        cat = _FEATURE_TO_CATEGORY.get(col, "Other")
        groups.setdefault(cat, {})[col] = val
    return groups

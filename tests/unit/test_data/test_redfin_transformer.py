"""Tests for the Redfin staging-to-production transformer."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from pricepoint.data.housing.redfin_transformer import (
    _fee_to_yearly,
    _normalize_date,
    compute_staging_hash,
    map_climate_label,
    map_climate_score,
    normalize_listing_status,
    parse_above_grade_finished_area,
    parse_apn,
    parse_appliances_included_count,
    parse_association_fee_yearly,
    parse_below_grade_finished_area,
    parse_building_area,
    parse_contract_date,
    parse_cooktop_energy_source,
    parse_countertop_material,
    parse_driveway_surface,
    parse_facade_type,
    parse_fireplace_fuel_source,
    parse_float,
    parse_garage_entry,
    parse_has_architectural_fireplace,
    parse_has_bar,
    parse_has_bay_window,
    parse_has_butler_pantry,
    parse_has_circular_driveway,
    parse_has_clubhouse,
    parse_has_community_pool,
    parse_has_crawl_space,
    parse_has_drink_fridge,
    parse_has_efficient_windows,
    parse_has_enclosed_porch,
    parse_has_ev_charging,
    parse_has_exterior_storage,
    parse_has_fenced_yard,
    parse_has_fireplace,
    parse_has_front_porch,
    parse_has_garage,
    parse_has_garden,
    parse_has_guest_suite,
    parse_has_hardwood,
    parse_has_hoa,
    parse_has_laundry_room,
    parse_has_luxury_ceilings,
    parse_has_open_floorplan,
    parse_has_outdoor_fireplace,
    parse_has_outdoor_kitchen,
    parse_has_premium_stone,
    parse_has_primary_fireplace,
    parse_has_private_pool,
    parse_has_room_over_garage,
    parse_has_sauna,
    parse_has_second_primary,
    parse_has_skylights,
    parse_has_sport_court,
    parse_has_stainless_appliances,
    parse_has_tall_ceilings,
    parse_has_utility_sink,
    parse_has_walkin_closets,
    parse_has_workshop,
    parse_int,
    parse_is_carpet_free,
    parse_is_primary_downstairs,
    parse_is_septic,
    parse_is_waterfront,
    parse_is_well_water,
    parse_laundry_location,
    parse_location_from_details,
    parse_lot_size_acres,
    parse_lot_size_from_staging,
    parse_no_cooling,
    parse_no_heating,
    parse_num_baths,
    parse_num_beds,
    parse_num_fireplaces,
    parse_num_garage_spaces,
    parse_num_parking_spaces,
    parse_num_stories,
    parse_oven_energy_source,
    parse_parking_type,
    parse_price,
    parse_price_per_sqft,
    parse_sale_date,
    parse_school_desc,
    parse_sold_date,
    parse_sqft,
    parse_street_address,
    parse_tax_date,
    parse_water_heater_energy_source,
    parse_year_built,
    transform_all_listings,
    transform_listing,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_staging(**kwargs):
    """Create a mock StagingRedfinListing."""
    mock = MagicMock()
    mock.id = kwargs.get("id", 1)
    mock.address = kwargs.get("address", "123 Main St, Cary, NC 27513")
    mock.city = kwargs.get("city", "Cary")
    mock.state = kwargs.get("state", "NC")
    mock.zip_code = kwargs.get("zip_code", "27513")
    mock.listing_status = kwargs.get("listing_status", "Sold")
    mock.sold_date = kwargs.get("sold_date", "January 15, 2024")
    mock.sold_price = kwargs.get("sold_price", "$500,000")
    mock.listing_price = kwargs.get("listing_price", "$510,000")
    mock.beds = kwargs.get("beds", 3)
    mock.baths = kwargs.get("baths", 2.5)
    mock.sqft = kwargs.get("sqft", 2000)
    mock.description = kwargs.get("description", "Nice home")
    mock.year_built = kwargs.get("year_built", 2005)
    mock.lot_size = kwargs.get("lot_size", "0.25 Acres")
    mock.price_per_sqft = kwargs.get("price_per_sqft", "$250")
    mock.listing_agent = kwargs.get("listing_agent", "Agent A")
    mock.listing_brokerage = kwargs.get("listing_brokerage", "Broker A")
    mock.buying_agent = kwargs.get("buying_agent", "Agent B")
    mock.buying_brokerage = kwargs.get("buying_brokerage", "Broker B")
    mock.redfin_estimate = kwargs.get("redfin_estimate", "$490,000")
    mock.sale_history = kwargs.get("sale_history", [])
    mock.tax_history = kwargs.get("tax_history", [])
    mock.property_details = kwargs.get("property_details", {})
    mock.schools = kwargs.get("schools", [])
    mock.climate_flood_factor = kwargs.get("climate_flood_factor", "Minor")
    mock.climate_fire_factor = kwargs.get("climate_fire_factor", "Minimal")
    mock.photo_s3_paths = kwargs.get("photo_s3_paths", [])
    mock.source_file = kwargs.get("source_file", "test.html")
    mock.loaded_at = kwargs.get("loaded_at")
    return mock


# ---------------------------------------------------------------------------
# TestParsePrice
# ---------------------------------------------------------------------------
class TestParsePrice:
    def test_valid_price(self):
        assert parse_price("$721,000") == 721000.0

    def test_none_input(self):
        assert parse_price(None) is None

    def test_empty_string(self):
        assert parse_price("") is None

    def test_no_dollar_sign(self):
        assert parse_price("500000") == 500000.0

    def test_with_cents(self):
        assert parse_price("$1,234.56") == 1234.56

    def test_non_numeric(self):
        assert parse_price("N/A") is None


# ---------------------------------------------------------------------------
# TestParseIntFloat
# ---------------------------------------------------------------------------
class TestParseIntFloat:
    def test_int_from_string(self):
        assert parse_int("42") == 42

    def test_int_none(self):
        assert parse_int(None) is None

    def test_int_invalid(self):
        assert parse_int("abc") is None

    def test_float_from_string(self):
        assert parse_float("3.14") == pytest.approx(3.14)

    def test_float_with_dollar(self):
        assert parse_float("$100") == 100.0

    def test_float_none(self):
        assert parse_float(None) is None


# ---------------------------------------------------------------------------
# TestParseStreetAddress
# ---------------------------------------------------------------------------
class TestParseStreetAddress:
    def test_full_address(self):
        assert parse_street_address("123 Main St, Cary, NC 27513") == "123 Main St"

    def test_no_comma(self):
        assert parse_street_address("123 Main St") == "123 Main St"

    def test_none(self):
        assert parse_street_address(None) is None


# ---------------------------------------------------------------------------
# TestNormalizeListingStatus
# ---------------------------------------------------------------------------
class TestNormalizeListingStatus:
    def test_sold(self):
        assert normalize_listing_status("Sold") == "SOLD"

    def test_off_market(self):
        assert normalize_listing_status("OFF MARKET") == "SOLD"

    def test_for_sale(self):
        assert normalize_listing_status("For sale") == "FOR SALE"

    def test_active(self):
        assert normalize_listing_status("Active") == "FOR SALE"

    def test_contingent(self):
        assert normalize_listing_status("Contingent") == "CONTINGENT"

    def test_pending(self):
        assert normalize_listing_status("Pending") == "PENDING"

    def test_coming_soon(self):
        assert normalize_listing_status("Coming Soon") == "COMING SOON"

    def test_none(self):
        assert normalize_listing_status(None) is None

    def test_unknown(self):
        assert normalize_listing_status("Something Else") is None


# ---------------------------------------------------------------------------
# TestParseSoldDate
# ---------------------------------------------------------------------------
class TestParseSoldDate:
    def test_full_date(self):
        result = parse_sold_date("January 15, 2024")
        assert result == datetime(2024, 1, 15)

    def test_abbreviated_month(self):
        result = parse_sold_date("Jun 1, 2024")
        assert result == datetime(2024, 6, 1)

    def test_iso_format(self):
        result = parse_sold_date("2024-01-15")
        assert result == datetime(2024, 1, 15)

    def test_month_only(self):
        result = parse_sold_date("JUN 2024")
        assert result == datetime(2024, 6, 1)

    def test_month_only_full(self):
        result = parse_sold_date("June 2024")
        assert result == datetime(2024, 6, 1)

    def test_none(self):
        assert parse_sold_date(None) is None

    def test_empty(self):
        assert parse_sold_date("") is None


# ---------------------------------------------------------------------------
# TestClimateScore
# ---------------------------------------------------------------------------
class TestClimateScore:
    def test_minimal(self):
        assert map_climate_score("Minimal") == 1

    def test_minor(self):
        assert map_climate_score("Minor") == 2

    def test_moderate(self):
        assert map_climate_score("Moderate") == 3

    def test_major(self):
        assert map_climate_score("Major") == 4

    def test_severe(self):
        assert map_climate_score("Severe") == 5

    def test_extreme(self):
        assert map_climate_score("Extreme") == 6

    def test_none(self):
        assert map_climate_score(None) is None

    def test_unknown(self):
        assert map_climate_score("Unknown") is None

    def test_case_insensitive(self):
        assert map_climate_score("MAJOR") == 4


class TestClimateLabel:
    def test_normalizes_case(self):
        assert map_climate_label("minor") == "Minor"

    def test_none(self):
        assert map_climate_label(None) is None

    def test_unknown_returns_none(self):
        assert map_climate_label("Unknown") is None


# ---------------------------------------------------------------------------
# Parking tests
# ---------------------------------------------------------------------------
class TestParking:
    def test_has_garage_yes(self):
        assert parse_has_garage({"garage": "Yes"}) is True

    def test_has_garage_no(self):
        assert parse_has_garage({"garage": "No"}) is False

    def test_has_garage_missing(self):
        assert parse_has_garage({}) is False

    def test_num_garage_spaces(self):
        assert parse_num_garage_spaces({"garage_spaces": "2"}) == 2

    def test_num_garage_spaces_missing(self):
        assert parse_num_garage_spaces({}) == 0

    def test_parking_type_attached(self):
        assert parse_parking_type({"attached_garage": "Yes"}) == "Attached Garage"

    def test_parking_type_attached_in_features(self):
        assert parse_parking_type({"parking_features": "Attached"}) == "Attached Garage"

    def test_parking_type_detached(self):
        assert parse_parking_type({"parking_features": "Detached"}) == "Detached Garage"

    def test_parking_type_carport(self):
        assert parse_parking_type({"parking_features": "Carport"}) == "Carport"

    def test_parking_type_street(self):
        assert parse_parking_type({"parking_features": "On Street"}) == "Street"

    def test_parking_type_garage_fallback(self):
        assert parse_parking_type({"garage": "Yes"}) == "Garage"

    def test_parking_type_none(self):
        assert parse_parking_type({}) is None

    def test_garage_entry_front(self):
        assert parse_garage_entry({"parking_features": "Garage Faces Front"}) == "Front"

    def test_garage_entry_side(self):
        assert parse_garage_entry({"parking_features": "Garage Faces Side"}) == "Side"

    def test_garage_entry_none(self):
        assert parse_garage_entry({}) is None

    def test_driveway_paved(self):
        assert parse_driveway_surface({"parking_features": "Concrete"}) == "Paved"

    def test_driveway_unpaved(self):
        assert parse_driveway_surface({"parking_features": "Gravel"}) == "Unpaved"

    def test_driveway_none(self):
        assert parse_driveway_surface({}) is None

    def test_has_workshop_in_garage(self):
        assert parse_has_workshop({"parking_features": "Workshop in Garage"}) is True

    def test_has_workshop_other(self):
        assert parse_has_workshop({"other_structures": "Workshop"}) is True

    def test_no_workshop(self):
        assert parse_has_workshop({}) is False

    def test_circular_driveway(self):
        assert parse_has_circular_driveway({"parking_features": "Circular Driveway"}) is True

    def test_ev_charging(self):
        details = {"parking_features": "Electric Vehicle Charging Station(s)"}
        assert parse_has_ev_charging(details) is True

    def test_num_parking_spaces(self):
        assert parse_num_parking_spaces({"parking_total": "4"}) == 4

    def test_num_parking_spaces_fallback(self):
        assert parse_num_parking_spaces({"parking_spaces": "2"}) == 2


# ---------------------------------------------------------------------------
# Fireplace tests
# ---------------------------------------------------------------------------
class TestFireplace:
    def test_has_fireplace(self):
        assert parse_has_fireplace({"fireplace": "Yes"}) is True

    def test_no_fireplace(self):
        assert parse_has_fireplace({}) is False

    def test_outdoor_fireplace(self):
        assert parse_has_outdoor_fireplace({"fireplace_features": "Outside"}) is True

    def test_fire_pit(self):
        assert parse_has_outdoor_fireplace({"fireplace_features": "Fire Pit"}) is True

    def test_primary_fireplace(self):
        assert parse_has_primary_fireplace({"fireplace_features": "Primary Bedroom"}) is True

    def test_architectural_fireplace(self):
        assert parse_has_architectural_fireplace({"fireplace_features": "Double Sided"}) is True

    def test_fuel_gas(self):
        assert parse_fireplace_fuel_source({"fireplace_features": "Gas Log"}) == "Gas"

    def test_fuel_wood(self):
        assert parse_fireplace_fuel_source({"fireplace_features": "Wood Burning"}) == "Wood"

    def test_fuel_electric(self):
        assert parse_fireplace_fuel_source({"fireplace_features": "Electric"}) == "Electric"

    def test_fuel_unknown(self):
        assert parse_fireplace_fuel_source({}) == "Unknown"

    def test_num_fireplaces(self):
        assert parse_num_fireplaces({"fireplaces_total": "2"}) == 2

    def test_num_fireplaces_missing(self):
        assert parse_num_fireplaces({}) == 0


# ---------------------------------------------------------------------------
# Appliance / energy tests
# ---------------------------------------------------------------------------
class TestAppliances:
    def test_water_heater_gas(self):
        assert parse_water_heater_energy_source({"appliances": "Gas Water Heater"}) == "Gas"

    def test_water_heater_electric(self):
        result = parse_water_heater_energy_source({"appliances": "Electric Water Heater"})
        assert result == "Electric"

    def test_water_heater_solar(self):
        assert parse_water_heater_energy_source({"appliances": "Solar Hot Water"}) == "Solar"

    def test_water_heater_unknown(self):
        assert parse_water_heater_energy_source({}) == "UNKNOWN"

    def test_cooktop_gas(self):
        assert parse_cooktop_energy_source({"appliances": "Gas Range"}) == "Gas"

    def test_cooktop_electric(self):
        assert parse_cooktop_energy_source({"appliances": "Electric Range"}) == "Electric"

    def test_cooktop_none(self):
        assert parse_cooktop_energy_source({}) is None

    def test_oven_gas(self):
        assert parse_oven_energy_source({"appliances": "Gas Oven"}) == "Gas"

    def test_oven_electric(self):
        assert parse_oven_energy_source({"appliances": "Electric Oven"}) == "Electric"

    def test_oven_unknown(self):
        assert parse_oven_energy_source({}) == "UNKNOWN"

    def test_drink_fridge(self):
        assert parse_has_drink_fridge({"appliances": "Wine Refrigerator"}) is True

    def test_stainless(self):
        details = {"appliances": "Stainless Steel Appliance(s)"}
        assert parse_has_stainless_appliances(details) is True

    def test_appliances_count_all(self):
        assert parse_appliances_included_count({"appliances": "Refrigerator, Washer, Dryer"}) == 3

    def test_appliances_count_none(self):
        assert parse_appliances_included_count({}) == 0

    def test_appliances_count_washer_dryer_combo(self):
        assert parse_appliances_included_count({"appliances": "Washer/Dryer"}) == 2


# ---------------------------------------------------------------------------
# Windows tests
# ---------------------------------------------------------------------------
class TestWindows:
    def test_efficient_windows(self):
        assert parse_has_efficient_windows({"window_features": "Double Pane Windows"}) is True

    def test_skylights(self):
        assert parse_has_skylights({"window_features": "Skylight"}) is True

    def test_bay_window(self):
        assert parse_has_bay_window({"window_features": "Bay"}) is True

    def test_no_windows(self):
        assert parse_has_efficient_windows({}) is False


# ---------------------------------------------------------------------------
# Laundry tests
# ---------------------------------------------------------------------------
class TestLaundry:
    def test_upper(self):
        assert parse_laundry_location({"laundry_features": "Upper Level"}) == "Upper"

    def test_main(self):
        assert parse_laundry_location({"laundry_features": "Main Level"}) == "Main"

    def test_basement(self):
        assert parse_laundry_location({"laundry_features": "Lower Level"}) == "Basement"

    def test_garage(self):
        assert parse_laundry_location({"laundry_features": "Garage"}) == "Garage/Out"

    def test_standard(self):
        assert parse_laundry_location({}) == "Standard"

    def test_laundry_room(self):
        assert parse_has_laundry_room({"laundry_features": "Laundry Room"}) is True

    def test_utility_sink(self):
        assert parse_has_utility_sink({"laundry_features": "Sink"}) is True


# ---------------------------------------------------------------------------
# Interior feature tests
# ---------------------------------------------------------------------------
class TestInteriorFeatures:
    def test_countertop_ultra(self):
        assert parse_countertop_material({"interior_features": "Quartz Counters"}) == "Ultra"

    def test_countertop_premium(self):
        assert parse_countertop_material({"interior_features": "Granite Counters"}) == "Premium"

    def test_countertop_standard(self):
        assert parse_countertop_material({"interior_features": "Tile Counters"}) == "Standard"

    def test_countertop_unknown(self):
        assert parse_countertop_material({}) == "Unknown"

    def test_primary_downstairs(self):
        assert parse_is_primary_downstairs({"interior_features": "Primary Downstairs"}) is True

    def test_guest_suite(self):
        assert parse_has_guest_suite({"interior_features": "In-Law Floorplan"}) is True

    def test_butler_pantry(self):
        assert parse_has_butler_pantry({"interior_features": "Butler's Pantry"}) is True

    def test_walkin_closets(self):
        assert parse_has_walkin_closets({"interior_features": "Walk-In Closet(s)"}) is True

    def test_tall_ceilings(self):
        assert parse_has_tall_ceilings({"interior_features": "High Ceilings"}) is True

    def test_luxury_ceilings(self):
        assert parse_has_luxury_ceilings({"interior_features": "Tray Ceiling(s)"}) is True

    def test_sauna(self):
        assert parse_has_sauna({"interior_features": "Sauna"}) is True

    def test_bar(self):
        assert parse_has_bar({"interior_features": "Bar"}) is True

    def test_second_primary(self):
        assert parse_has_second_primary({"interior_features": "Second Primary Bedroom"}) is True

    def test_room_over_garage(self):
        assert parse_has_room_over_garage({"interior_features": "Room Over Garage"}) is True

    def test_open_floorplan(self):
        assert parse_has_open_floorplan({"interior_features": "Open Floorplan"}) is True

    def test_open_floorplan_typo_not_matched(self):
        """Bug fix: 'Floorplane' alone (typo) should NOT match."""
        assert parse_has_open_floorplan({"interior_features": "Floorplane Layout"}) is False


# ---------------------------------------------------------------------------
# Flooring tests
# ---------------------------------------------------------------------------
class TestFlooring:
    def test_carpet_free(self):
        assert parse_is_carpet_free({"flooring": "Hardwood, Tile"}) is True

    def test_not_carpet_free(self):
        assert parse_is_carpet_free({"flooring": "Carpet, Tile"}) is False

    def test_premium_stone(self):
        assert parse_has_premium_stone({"flooring": "Marble"}) is True

    def test_hardwood(self):
        assert parse_has_hardwood({"flooring": "Wood"}) is True

    def test_crawl_space(self):
        assert parse_has_crawl_space({"crawl_space": "Yes"}) is True


# ---------------------------------------------------------------------------
# Exterior / structure tests
# ---------------------------------------------------------------------------
class TestExterior:
    def test_facade_masonry(self):
        assert parse_facade_type({"construction_materials": "Brick, Stone"}) == "Masonry"

    def test_facade_fiber_cement(self):
        assert parse_facade_type({"construction_materials": "HardiPlank"}) == "Fiber Cement"

    def test_facade_synthetic(self):
        assert parse_facade_type({"construction_materials": "Vinyl"}) == "Synthetic"

    def test_facade_wood(self):
        assert parse_facade_type({"construction_materials": "Cedar"}) == "Wood"

    def test_facade_none(self):
        assert parse_facade_type({}) is None

    def test_building_area(self):
        assert parse_building_area({"building_area_total": "2500"}) == 2500.0

    def test_above_grade(self):
        assert parse_above_grade_finished_area({"above_grade_finished_area": "1800"}) == 1800.0

    def test_below_grade(self):
        assert parse_below_grade_finished_area({"below_grade_finished_area": "700"}) == 700.0

    def test_waterfront_yes(self):
        assert parse_is_waterfront({"waterfront": "Yes"}) is True

    def test_waterfront_features(self):
        assert parse_is_waterfront({"features": "Waterfront"}) is True

    def test_not_waterfront(self):
        assert parse_is_waterfront({}) is False


# ---------------------------------------------------------------------------
# Num stories tests
# ---------------------------------------------------------------------------
class TestNumStories:
    def test_numeric(self):
        assert parse_num_stories({"stories": "2"}) == 2.0

    def test_text_one(self):
        assert parse_num_stories({"levels": "One"}) == 1.0

    def test_text_one_and_half(self):
        assert parse_num_stories({"levels": "One and One Half"}) == 1.5

    def test_text_two(self):
        assert parse_num_stories({"levels": "Two"}) == 2.0

    def test_text_three(self):
        assert parse_num_stories({"levels": "Three"}) == 3.0

    def test_text_three_or_more(self):
        assert parse_num_stories({"levels": "Three Or More"}) == 3.0

    def test_text_bi_level(self):
        assert parse_num_stories({"levels": "Bi-Level"}) == 2.0

    def test_text_multi_split(self):
        assert parse_num_stories({"levels": "Multi/Split"}) == 2.0

    def test_text_tri_level(self):
        assert parse_num_stories({"levels": "Tri-Level"}) == 3.0

    def test_stories_takes_precedence(self):
        assert parse_num_stories({"stories": "3", "levels": "Two"}) == 3.0

    def test_none(self):
        assert parse_num_stories({}) is None


# ---------------------------------------------------------------------------
# Lot size tests
# ---------------------------------------------------------------------------
class TestLotSize:
    def test_acres_from_details(self):
        assert parse_lot_size_acres({"lot_size_acres": "0.5"}) == pytest.approx(0.5)

    def test_lot_size_string_acres(self):
        assert parse_lot_size_acres({"lot_size": "0.25 Acres"}) == pytest.approx(0.25)

    def test_lot_size_string_sqft(self):
        result = parse_lot_size_acres({"lot_size": "10890 Sq. Ft."})
        assert result == pytest.approx(0.25, abs=0.01)

    def test_lot_size_square_feet(self):
        result = parse_lot_size_acres({"lot_size_square_feet": "43560"})
        assert result == pytest.approx(1.0)

    def test_lot_size_area_sqft(self):
        result = parse_lot_size_acres({"lot_size_area": "43560", "lot_size_units": "Square Feet"})
        assert result == pytest.approx(1.0)

    def test_lot_size_area_acres(self):
        result = parse_lot_size_acres({"lot_size_area": "2.0"})
        assert result == pytest.approx(2.0)

    def test_none(self):
        assert parse_lot_size_acres({}) is None

    def test_staging_acres(self):
        assert parse_lot_size_from_staging("0.25 Acres") == pytest.approx(0.25)

    def test_staging_sqft(self):
        result = parse_lot_size_from_staging("8,500 Sq. Ft.")
        assert result == pytest.approx(8500 / 43560.0)

    def test_staging_none(self):
        assert parse_lot_size_from_staging(None) is None


# ---------------------------------------------------------------------------
# Utilities tests
# ---------------------------------------------------------------------------
class TestUtilities:
    def test_septic(self):
        assert parse_is_septic({"sewer": "Septic Tank"}) is True

    def test_well_water(self):
        assert parse_is_well_water({"water_source": "Well"}) is True

    def test_no_heating(self):
        assert parse_no_heating({"heating": "No"}) is True

    def test_has_heating(self):
        assert parse_no_heating({"heating": "Forced Air"}) is False

    def test_no_cooling(self):
        assert parse_no_cooling({"cooling": "No"}) is True


# ---------------------------------------------------------------------------
# HOA / community tests
# ---------------------------------------------------------------------------
class TestCommunity:
    def test_has_hoa(self):
        assert parse_has_hoa({"association": "Yes"}) is True

    def test_enclosed_porch(self):
        assert parse_has_enclosed_porch({"patio_and_porch_features": "Screened Porch"}) is True

    def test_front_porch(self):
        assert parse_has_front_porch({"patio_and_porch_features": "Front Porch"}) is True

    def test_fenced_yard_wood(self):
        assert parse_has_fenced_yard({"fencing": "Wood"}) is True

    def test_fenced_yard_invisible_excluded(self):
        assert parse_has_fenced_yard({"fencing": "Invisible"}) is False

    def test_fenced_yard_exterior(self):
        assert parse_has_fenced_yard({"exterior_features": "Private Yard"}) is True

    def test_outdoor_kitchen_exterior(self):
        assert parse_has_outdoor_kitchen({"exterior_features": "Built-in Barbecue"}) is True

    def test_outdoor_kitchen_structure(self):
        assert parse_has_outdoor_kitchen({"other_structures": "Outdoor Kitchen"}) is True

    def test_sport_court(self):
        assert parse_has_sport_court({"exterior_features": "Tennis Court(s)"}) is True

    def test_private_pool_exterior(self):
        assert parse_has_private_pool({"exterior_features": "Pool"}) is True

    def test_private_pool_features(self):
        assert parse_has_private_pool({"pool_features": "In Ground"}) is True

    def test_community_pool_excluded(self):
        assert parse_has_private_pool({"pool_features": "Community"}) is False

    def test_community_pool(self):
        assert parse_has_community_pool({"community_features": "Pool"}) is True

    def test_community_pool_assoc(self):
        assert parse_has_community_pool({"pool_features": "Swimming Pool Com/Fee"}) is True

    def test_clubhouse(self):
        assert parse_has_clubhouse({"community_features": "Clubhouse"}) is True

    def test_exterior_storage(self):
        assert parse_has_exterior_storage({"other_structures": "Shed"}) is True

    def test_garden(self):
        assert parse_has_garden({"exterior_features": "Garden"}) is True


# ---------------------------------------------------------------------------
# Association fee tests
# ---------------------------------------------------------------------------
class TestAssociationFee:
    def test_monthly_fee(self):
        d = {"association_fee": "$100", "association_fee_frequency": "Monthly"}
        assert parse_association_fee_yearly(d) == pytest.approx(1200.0)

    def test_quarterly_fee(self):
        d = {"association_fee": "$300", "association_fee_frequency": "Quarterly"}
        assert parse_association_fee_yearly(d) == pytest.approx(1200.0)

    def test_annual_fee(self):
        d = {"association_fee": "$1200", "association_fee_frequency": "Annually"}
        assert parse_association_fee_yearly(d) == pytest.approx(1200.0)

    def test_semi_annual_fee(self):
        d = {"association_fee": "$600", "association_fee_frequency": "Semi-Annually"}
        assert parse_association_fee_yearly(d) == pytest.approx(1200.0)

    def test_default_monthly(self):
        result = parse_association_fee_yearly({"association_fee": "$100"})
        assert result == pytest.approx(1200.0)

    def test_two_fees(self):
        result = parse_association_fee_yearly(
            {
                "association_fee": "$100",
                "association_fee_frequency": "Monthly",
                "association_fee_2": "$50",
                "association_fee_2_frequency": "Monthly",
            }
        )
        assert result == pytest.approx(1800.0)

    def test_hoa_dues_fallback(self):
        result = parse_association_fee_yearly({"hoa_dues": "$150"})
        assert result == pytest.approx(1800.0)

    def test_none(self):
        assert parse_association_fee_yearly({}) is None


class TestFeeToYearly:
    def test_monthly(self):
        assert _fee_to_yearly(100, "Monthly") == 1200

    def test_quarterly(self):
        assert _fee_to_yearly(300, "Quarterly") == 1200

    def test_annually(self):
        assert _fee_to_yearly(1200, "Annually") == 1200

    def test_semi_annually(self):
        assert _fee_to_yearly(600, "Semi-Annually") == 1200


# ---------------------------------------------------------------------------
# APN tests
# ---------------------------------------------------------------------------
class TestApn:
    def test_valid_apn(self):
        assert parse_apn({"apn": "0761.03 34 2215 000"}) == "0761.03 34 2215 000"

    def test_see_plat(self):
        assert parse_apn({"apn": "See Plat"}) is None

    def test_none(self):
        assert parse_apn({}) is None

    def test_numeric_apn(self):
        assert parse_apn({"apn": "0763593132"}) == "0763593132"


# ---------------------------------------------------------------------------
# Fallback field tests (year_built, beds, baths, sqft, price_per_sqft)
# ---------------------------------------------------------------------------
class TestFallbackFields:
    def test_year_built_staging(self):
        staging = _make_staging(year_built=2010)
        assert parse_year_built(staging, {}) == 2010

    def test_year_built_details_fallback(self):
        staging = _make_staging(year_built=None)
        assert parse_year_built(staging, {"year_built": "2005"}) == 2005

    def test_num_beds_staging(self):
        staging = _make_staging(beds=4)
        assert parse_num_beds(staging, {}) == 4

    def test_num_beds_details_fallback(self):
        staging = _make_staging(beds=None)
        assert parse_num_beds(staging, {"num_of_bedrooms": "3"}) == 3

    def test_num_baths_staging(self):
        staging = _make_staging(baths=2.5)
        assert parse_num_baths(staging, {}) == 2.5

    def test_num_baths_combined(self):
        staging = _make_staging(baths=None)
        details = {"num_of_full_bathrooms": "2", "num_of_half_bathrooms": "1"}
        assert parse_num_baths(staging, details) == 3.0

    def test_sqft_staging(self):
        staging = _make_staging(sqft=2000)
        assert parse_sqft(staging, {}) == 2000

    def test_sqft_building_area_fallback(self):
        staging = _make_staging(sqft=None)
        assert parse_sqft(staging, {"building_area_total": "2500"}) == 2500

    def test_sqft_living_area_fallback(self):
        staging = _make_staging(sqft=None)
        assert parse_sqft(staging, {"living_area": "1800"}) == 1800

    def test_price_per_sqft_staging(self):
        staging = _make_staging(price_per_sqft="$250")
        assert parse_price_per_sqft(staging, 500000, 2000) == 250.0

    def test_price_per_sqft_calculated(self):
        staging = _make_staging(price_per_sqft=None)
        assert parse_price_per_sqft(staging, 500000, 2000) == 250.0


# ---------------------------------------------------------------------------
# Location tests
# ---------------------------------------------------------------------------
class TestLocation:
    def test_from_details(self):
        result = parse_location_from_details({"latitude": "35.79", "longitude": "-78.78"})
        assert result == (pytest.approx(35.79), pytest.approx(-78.78))

    def test_missing(self):
        assert parse_location_from_details({}) is None


# ---------------------------------------------------------------------------
# Date / history tests
# ---------------------------------------------------------------------------
class TestNormalizeDate:
    def test_abbreviated_month(self):
        assert _normalize_date("Jun 14, 2024") == "2024-06-14"

    def test_full_month(self):
        assert _normalize_date("January 15, 2024") == "2024-01-15"

    def test_iso_passthrough(self):
        assert _normalize_date("2024-06-14") == "2024-06-14"

    def test_none(self):
        assert _normalize_date(None) is None


class TestParseSaleDate:
    def test_valid(self):
        result = parse_sale_date("Jun 14, 2024")
        assert result == datetime(2024, 6, 14)

    def test_none(self):
        assert parse_sale_date(None) is None


class TestParseTaxDate:
    def test_valid(self):
        result = parse_tax_date(2023)
        assert result == datetime(2023, 1, 1)

    def test_string(self):
        result = parse_tax_date("2024")
        assert result == datetime(2024, 1, 1)

    def test_none(self):
        assert parse_tax_date(None) is None


class TestContractDate:
    def test_parse(self):
        result = parse_contract_date({"contract_status_change_date": "January 15, 2024"})
        assert result == datetime(2024, 1, 15)


# ---------------------------------------------------------------------------
# School description tests
# ---------------------------------------------------------------------------
class TestParseSchoolDesc:
    def test_public_elementary(self):
        result = parse_school_desc("Public, PreK-5 Assigned 0.3mi")
        assert result["school_type"] == "Public"
        assert result["grades"] == "PreK-5"
        assert result["distance_miles"] == pytest.approx(0.3)

    def test_private_school(self):
        result = parse_school_desc("Private, 9-12 Nearby 2.1mi")
        assert result["school_type"] == "Private"
        assert result["grades"] == "9-12"

    def test_none_input(self):
        assert parse_school_desc(None) is None


# ---------------------------------------------------------------------------
# Case-insensitive matching tests
# ---------------------------------------------------------------------------
class TestCaseInsensitive:
    """Verify that parsing functions handle mixed-case input correctly."""

    # Equality checks (Yes/No)
    def test_garage_lowercase(self):
        assert parse_has_garage({"garage": "yes"}) is True

    def test_garage_uppercase(self):
        assert parse_has_garage({"garage": "YES"}) is True

    def test_fireplace_lowercase(self):
        assert parse_has_fireplace({"fireplace": "yes"}) is True

    def test_crawl_space_mixed_case(self):
        assert parse_has_crawl_space({"crawl_space": "YES"}) is True

    def test_no_heating_lowercase(self):
        assert parse_no_heating({"heating": "no"}) is True

    def test_no_cooling_uppercase(self):
        assert parse_no_cooling({"cooling": "NO"}) is True

    def test_hoa_mixed_case(self):
        assert parse_has_hoa({"association": "yEs"}) is True

    # Keyword checks in strings
    def test_facade_uppercase_brick(self):
        assert parse_facade_type({"construction_materials": "BRICK"}) == "Masonry"

    def test_facade_mixed_case(self):
        assert parse_facade_type({"construction_materials": "vinyl Siding"}) == "Synthetic"

    def test_parking_type_lowercase(self):
        assert parse_parking_type({"parking_features": "attached"}) == "Attached Garage"

    def test_parking_type_uppercase(self):
        assert parse_parking_type({"parking_features": "DETACHED"}) == "Detached Garage"

    def test_driveway_mixed_case(self):
        assert parse_driveway_surface({"parking_features": "CONCRETE"}) == "Paved"

    def test_water_heater_mixed_case(self):
        assert parse_water_heater_energy_source({"appliances": "gas water heater"}) == "Gas"

    def test_cooktop_uppercase(self):
        assert parse_cooktop_energy_source({"appliances": "GAS COOKTOP"}) == "Gas"

    def test_oven_mixed_case(self):
        assert parse_oven_energy_source({"appliances": "Electric Oven"}) == "Electric"

    def test_countertop_uppercase(self):
        assert parse_countertop_material({"interior_features": "QUARTZ COUNTERS"}) == "Ultra"

    def test_laundry_location_uppercase(self):
        assert parse_laundry_location({"laundry_features": "UPPER Level"}) == "Upper"

    def test_fireplace_fuel_mixed_case(self):
        assert parse_fireplace_fuel_source({"fireplace_features": "gas log"}) == "Gas"

    # Boolean keyword checks
    def test_has_skylight_uppercase(self):
        assert parse_has_skylights({"window_features": "SKYLIGHT"}) is True

    def test_has_sauna_lowercase(self):
        assert parse_has_sauna({"interior_features": "sauna, Bar"}) is True

    def test_has_open_floorplan_uppercase(self):
        assert parse_has_open_floorplan({"interior_features": "OPEN FLOORPLAN"}) is True

    def test_is_waterfront_lowercase(self):
        assert parse_is_waterfront({"waterfront": "yes"}) is True

    def test_septic_uppercase(self):
        assert parse_is_septic({"sewer": "SEPTIC TANK"}) is True

    def test_well_water_mixed_case(self):
        assert parse_is_well_water({"water_source": "well"}) is True

    def test_enclosed_porch_uppercase(self):
        assert parse_has_enclosed_porch({"patio_and_porch_features": "SCREENED"}) is True

    def test_fenced_yard_uppercase(self):
        assert parse_has_fenced_yard({"fencing": "WOOD"}) is True

    def test_garden_mixed_case(self):
        assert parse_has_garden({"exterior_features": "garden"}) is True

    def test_carpet_free_uppercase(self):
        assert parse_is_carpet_free({"flooring": "CARPET, Tile"}) is False

    def test_hardwood_mixed_case(self):
        assert parse_has_hardwood({"flooring": "WOOD"}) is True


# ---------------------------------------------------------------------------
# Hash tests
# ---------------------------------------------------------------------------
class TestComputeHash:
    def test_deterministic(self):
        s1 = _make_staging()
        s2 = _make_staging()
        assert compute_staging_hash(s1) == compute_staging_hash(s2)

    def test_different_input(self):
        s1 = _make_staging(address="123 Main St, Cary, NC 27513")
        s2 = _make_staging(address="456 Oak Ave, Cary, NC 27513")
        assert compute_staging_hash(s1) != compute_staging_hash(s2)

    def test_excludes_id_and_loaded_at(self):
        s1 = _make_staging(id=1, loaded_at="2024-01-01")
        s2 = _make_staging(id=999, loaded_at="2025-12-31")
        assert compute_staging_hash(s1) == compute_staging_hash(s2)


# ---------------------------------------------------------------------------
# Transform integration tests
# ---------------------------------------------------------------------------
class TestTransformListing:
    def test_skips_no_address(self):
        session = MagicMock()
        staging = _make_staging(address=None)
        result = transform_listing(session, staging)
        assert result is False

    def test_skips_unchanged_hash(self):
        staging = _make_staging()
        existing = MagicMock()
        existing.staging_hash = compute_staging_hash(staging)
        existing.location = "some_location"

        session = MagicMock()
        session.execute.return_value.scalar_one_or_none.return_value = existing

        result = transform_listing(session, staging, geocode_fn=lambda _: None)
        assert result is False

    def test_transforms_new_listing(self):
        staging = _make_staging()

        session = MagicMock()
        # First call: RedfinListing lookup returns None (new property)
        # Subsequent calls: PropertyValuation lookup returns None
        session.execute.return_value.scalar_one_or_none.return_value = None

        geocode_fn = MagicMock(return_value=(35.79, -78.78))
        enrich_fn = MagicMock(return_value=0)

        with (
            patch("geoalchemy2.shape.from_shape", return_value="mocked_geom"),
            patch("geoalchemy2.shape.to_shape") as mock_to_shape,
        ):
            mock_point = MagicMock()
            mock_point.y = 35.79
            mock_point.x = -78.78
            mock_to_shape.return_value = mock_point
            result = transform_listing(session, staging, geocode_fn=geocode_fn, enrich_fn=enrich_fn)

        assert result is True
        session.add.assert_called()
        geocode_fn.assert_called_once()


# ---------------------------------------------------------------------------
# Transform all listings
# ---------------------------------------------------------------------------
class TestTransformAllListings:
    @patch("pricepoint.data.housing.redfin_transformer.SessionLocal")
    @patch("pricepoint.data.housing.redfin_transformer.transform_listing")
    def test_batch_processing(self, mock_transform, mock_session_cls):
        session = MagicMock()
        mock_session_cls.return_value = session

        session.execute.return_value.scalars.return_value.all.return_value = [1, 2]

        staging1 = MagicMock()
        staging1.id = 1
        staging2 = MagicMock()
        staging2.id = 2
        session.execute.return_value.scalars.return_value.all.side_effect = [
            [1, 2],
            [staging1, staging2],
        ]

        mock_transform.side_effect = [True, False]

        result = transform_all_listings(batch_size=100)
        assert result["transformed"] == 1
        assert result["skipped"] == 1
        assert result["errors"] == 0

    @patch("pricepoint.data.housing.redfin_transformer.SessionLocal")
    @patch("pricepoint.data.housing.redfin_transformer.transform_listing")
    def test_error_counting(self, mock_transform, mock_session_cls):
        session = MagicMock()
        mock_session_cls.return_value = session

        staging1 = MagicMock()
        staging1.id = 1
        session.execute.return_value.scalars.return_value.all.side_effect = [
            [1],
            [staging1],
        ]

        mock_transform.side_effect = ValueError("parse error")

        result = transform_all_listings(batch_size=100)
        assert result["errors"] == 1
        assert result["transformed"] == 0

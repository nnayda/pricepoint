"""SQLAlchemy ORM models with PostGIS geometry columns."""

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Property(Base):
    """Residential property record with location and assessed value."""

    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, autoincrement=True)
    parcel_id = Column(String, unique=True, nullable=False, index=True)
    address = Column(String, nullable=False)
    city = Column(String)
    state = Column(String(2))
    zip_code = Column(String(10))
    assessed_value = Column(Float)
    location = Column(Geometry("POINT", srid=4326))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PoliceIncident(Base):
    """Police incident report with geolocation."""

    __tablename__ = "police_incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(String, unique=True, nullable=False)
    incident_type = Column(String)
    occurred_at = Column(DateTime(timezone=True))
    location = Column(Geometry("POINT", srid=4326))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class StagingCaryPoliceIncident(Base):
    """Raw police incident records from the Town of Cary Open Data Portal.

    All fields stored as-is from the API. Weekly full refresh (truncate + reload).
    """

    __tablename__ = "staging_cary_police_incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    api_id = Column(String, index=True)
    incident_number = Column(String, index=True)
    crime_category = Column(String, nullable=True)
    crime_type = Column(String, nullable=True)
    ucr = Column(String, nullable=True)
    map_reference = Column(String, nullable=True)
    date_from = Column(DateTime(timezone=True), nullable=True)
    from_time = Column(String, nullable=True)
    date_to = Column(DateTime(timezone=True), nullable=True)
    to_time = Column(String, nullable=True)
    crimeday = Column(String, nullable=True)
    geocode = Column(String, nullable=True)
    location_category = Column(String, nullable=True)
    district = Column(String, nullable=True)
    beat_number = Column(String, nullable=True)
    neighborhd_id = Column(String, nullable=True)
    apartment_complex = Column(String, nullable=True)
    residential_subdivision = Column(String, nullable=True)
    subdivisn_id = Column(String, nullable=True)
    activity_date = Column(String, nullable=True)
    phxrecordstatus = Column(String, nullable=True)
    phxcommunity = Column(String, nullable=True)
    phxstatus = Column(String, nullable=True)
    record = Column(String, nullable=True)
    offensecategory = Column(String, nullable=True)
    violentproperty = Column(String, nullable=True)
    timeframe = Column(String, nullable=True)
    domestic = Column(String, nullable=True)
    total_incidents = Column(String, nullable=True)
    year = Column(String, nullable=True)
    older_than_five_years_from_now = Column(String, nullable=True)
    chrgcnt = Column(String, nullable=True)
    lon = Column(Float, nullable=True)
    lat = Column(Float, nullable=True)
    location = Column(Geometry("POINT", srid=4326), nullable=True)
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class StagingRaleighPoliceIncident(Base):
    """Raw police incident records from the City of Raleigh ArcGIS Feature Service.

    Historical (NIBRS) data loaded via full refresh; daily incremental via
    the Daily_Police_Incidents endpoint.
    """

    __tablename__ = "staging_raleigh_police_incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    objectid = Column(String, nullable=True)
    global_id = Column(String, nullable=True)
    case_number = Column(String, nullable=True, index=True)
    crime_category = Column(String, nullable=True)
    crime_code = Column(String, nullable=True)
    crime_description = Column(String, nullable=True)
    crime_type = Column(String, nullable=True)
    reported_block_address = Column(String, nullable=True)
    city_of_incident = Column(String, nullable=True)
    city = Column(String, nullable=True)
    district = Column(String, nullable=True)
    reported_date = Column(DateTime(timezone=True), nullable=True)
    reported_year = Column(Integer, nullable=True)
    reported_month = Column(Integer, nullable=True)
    reported_day = Column(Integer, nullable=True)
    reported_hour = Column(Integer, nullable=True)
    reported_dayofwk = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    agency = Column(String, nullable=True)
    updated_date = Column(DateTime(timezone=True), nullable=True)
    location = Column(Geometry("POINT", srid=4326), nullable=True)
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class StagingMorrisvillePoliceIncident(Base):
    """Raw police incident records from the Town of Morrisville Open Data Portal.

    All fields stored as-is from the API. Weekly full refresh (truncate + reload).
    """

    __tablename__ = "staging_morrisville_police_incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inci_id = Column(String, nullable=True, index=True)
    offense = Column(String, nullable=True)
    date_rept = Column(String, nullable=True)
    date_occu = Column(String, nullable=True)
    dow1 = Column(String, nullable=True)
    monthstamp = Column(String, nullable=True)
    yearstamp = Column(String, nullable=True)
    street = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip = Column(String, nullable=True)
    neighborhd = Column(String, nullable=True)
    subdivisn = Column(String, nullable=True)
    tract = Column(String, nullable=True)
    zone = Column(String, nullable=True)
    district = Column(String, nullable=True)
    asst_offcr = Column(String, nullable=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    location = Column(Geometry("POINT", srid=4326), nullable=True)
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class RedfinSchool(Base):
    """Raw school data extracted from Redfin listings (bronze layer)."""

    __tablename__ = "redfin_schools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    school_type = Column(String)
    rating = Column(Float)
    grades = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TigerCensusBlock(Base):
    """US Census TIGER/Line census block boundaries (TABBLOCK20)."""

    __tablename__ = "tiger_census_blocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    statefp20 = Column(String(2))
    countyfp20 = Column(String(3))
    tractce20 = Column(String(6))
    blockce20 = Column(String(4))
    geoid20 = Column(String(15), index=True)
    name20 = Column(String)
    aland20 = Column(BigInteger)
    awater20 = Column(BigInteger)
    intptlat20 = Column(String(11))
    intptlon20 = Column(String(12))
    funcstat20 = Column(String(1))
    mtfcc20 = Column(String(5))
    ur20 = Column(String(1))
    uace20 = Column(String(5))
    uatype20 = Column(String(1))
    housing20 = Column(Integer)
    pop20 = Column(Integer)
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class TigerBlockGroup(Base):
    """US Census TIGER/Line block group boundaries (BG)."""

    __tablename__ = "tiger_block_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    statefp = Column(String(2))
    countyfp = Column(String(3))
    tractce = Column(String(6))
    blkgrpce = Column(String(1))
    geoid = Column(String(12), index=True)
    namelsad = Column(String(100))
    aland = Column(BigInteger)
    awater = Column(BigInteger)
    intptlat = Column(String(11))
    intptlon = Column(String(12))
    funcstat = Column(String(1))
    mtfcc = Column(String(5))
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class TigerTract(Base):
    """US Census TIGER/Line census tract boundaries (TRACT)."""

    __tablename__ = "tiger_tracts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    statefp = Column(String(2))
    countyfp = Column(String(3))
    tractce = Column(String(6))
    geoid = Column(String(11), index=True)
    name = Column(String)
    namelsad = Column(String(100))
    aland = Column(BigInteger)
    awater = Column(BigInteger)
    intptlat = Column(String(11))
    intptlon = Column(String(12))
    funcstat = Column(String(1))
    mtfcc = Column(String(5))
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class TigerSchoolDistrict(Base):
    """US Census TIGER/Line school district boundaries (ELSD/SCSD/UNSD combined)."""

    __tablename__ = "tiger_school_districts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    district_type = Column(String(10), index=True)
    statefp = Column(String(2))
    geoid = Column(String(7), index=True)
    name = Column(String)
    lsad = Column(String(2))
    lograde = Column(String(2))
    higrade = Column(String(2))
    aland = Column(BigInteger)
    awater = Column(BigInteger)
    intptlat = Column(String(11))
    intptlon = Column(String(12))
    funcstat = Column(String(1))
    mtfcc = Column(String(5))
    sdtyp = Column(String(1))
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("idx_tiger_school_districts_geom", "geom", postgresql_using="gist"),)


class TigerCounty(Base):
    """US Census TIGER/Line county boundaries (COUNTY)."""

    __tablename__ = "tiger_counties"

    id = Column(Integer, primary_key=True, autoincrement=True)
    statefp = Column(String(2))
    countyfp = Column(String(3))
    countyns = Column(String(8))
    geoid = Column(String(5), index=True)
    name = Column(String)
    namelsad = Column(String(100))
    lsad = Column(String(2))
    classfp = Column(String(2))
    aland = Column(BigInteger)
    awater = Column(BigInteger)
    intptlat = Column(String(11))
    intptlon = Column(String(12))
    funcstat = Column(String(1))
    mtfcc = Column(String(5))
    csafp = Column(String(3))
    cbsafp = Column(String(5))
    metdivfp = Column(String(5))
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class TigerCountySubdivision(Base):
    """US Census TIGER/Line county subdivision boundaries (COUSUB)."""

    __tablename__ = "tiger_county_subdivisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    statefp = Column(String(2))
    countyfp = Column(String(3))
    cousubfp = Column(String(5))
    cousubns = Column(String(8))
    geoid = Column(String(10), index=True)
    name = Column(String)
    namelsad = Column(String(100))
    lsad = Column(String(2))
    classfp = Column(String(2))
    aland = Column(BigInteger)
    awater = Column(BigInteger)
    intptlat = Column(String(11))
    intptlon = Column(String(12))
    funcstat = Column(String(1))
    mtfcc = Column(String(5))
    cnectafp = Column(String(3))
    nectafp = Column(String(5))
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class StagingWakeCountyPropertyData(Base):
    """Wake County property assessment data staging table.

    Contains all 94 columns from the county's daily extract in fixed-width format.
    Truncate-and-reload pattern (no historical tracking). Raw coded values only.
    """

    __tablename__ = "staging_wake_county_property_data"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Ownership and mailing address
    owner_1 = Column(String(35), nullable=True)
    owner_2 = Column(String(35), nullable=True)
    address_1 = Column(String(35), nullable=True)
    address_2 = Column(String(35), nullable=True)
    address_3 = Column(String(35), nullable=True)

    # Property identification
    reid = Column(String(7), nullable=True, index=True)
    card_num = Column(String(3), nullable=True)
    num_cards = Column(String(3), nullable=True)

    # Physical address components
    street_num = Column(String(6), nullable=True)
    street_prefix = Column(String(2), nullable=True)
    street_name = Column(String(25), nullable=True)
    street_type = Column(String(4), nullable=True)
    street_suffix = Column(String(2), nullable=True)
    street_misc = Column(String(2), nullable=True)

    # Location and jurisdiction
    planning_jurisdiction = Column(String(2), nullable=True)
    township = Column(String(2), nullable=True)
    fire_district = Column(String(2), nullable=True)
    physical_city = Column(String(50), nullable=True)
    physical_zip_code = Column(String(5), nullable=True)
    city = Column(String(3), nullable=True)

    # Parcel details
    parcel_identification = Column(String(19), nullable=True)
    billing_class = Column(String(1), nullable=True)
    land_classification = Column(String(1), nullable=True)
    zoning = Column(String(5), nullable=True)
    deeded_acreage = Column(Float, nullable=True)

    # Special districts
    special_district_1 = Column(String(3), nullable=True)
    special_district_2 = Column(String(3), nullable=True)
    special_district_3 = Column(String(3), nullable=True)

    # Land sales
    land_sale_price = Column(Float, nullable=True)
    land_sale_date = Column(String(10), nullable=True)

    # Total sales
    total_sale_price = Column(Float, nullable=True)
    total_sale_date = Column(String(10), nullable=True)

    # Assessed values
    assessed_building_value = Column(Float, nullable=True)
    assessed_land_value = Column(Float, nullable=True)

    # Deed information
    deed_book = Column(String(6), nullable=True)
    deed_page = Column(String(6), nullable=True)
    deed_date = Column(String(10), nullable=True)

    # Property description and indexing
    property_description = Column(String(40), nullable=True)
    vcs = Column(String(7), nullable=True)
    property_index = Column(String(40), nullable=True)
    type_use = Column(String(3), nullable=True)

    # Building characteristics
    year_built = Column(Integer, nullable=True)
    num_rooms = Column(Integer, nullable=True)
    units = Column(Integer, nullable=True)
    heated_area = Column(Float, nullable=True)

    # Utilities and site features
    utilities = Column(String(3), nullable=True)
    street_pavement = Column(String(1), nullable=True)
    topography = Column(String(1), nullable=True)

    # Building years and modifications
    year_of_addition = Column(Integer, nullable=True)
    effective_year = Column(Integer, nullable=True)
    remodeled_year = Column(Integer, nullable=True)
    unused = Column(String(2), nullable=True)
    special_write_in = Column(String(8), nullable=True)

    # Building structure
    story_height = Column(String(1), nullable=True)
    design_style = Column(String(1), nullable=True)
    foundation_basement = Column(String(1), nullable=True)
    foundation_basement_pct = Column(String(2), nullable=True)
    exterior_wall = Column(String(1), nullable=True)
    common_wall = Column(String(1), nullable=True)
    roof = Column(String(1), nullable=True)
    roof_floor_system = Column(String(1), nullable=True)

    # Interior finishes
    floor_finish = Column(String(1), nullable=True)
    interior_finish = Column(String(1), nullable=True)
    interior_finish_1 = Column(String(1), nullable=True)
    interior_finish_1_pct = Column(String(2), nullable=True)
    interior_finish_2 = Column(String(1), nullable=True)
    interior_finish_2_pct = Column(String(2), nullable=True)

    # HVAC systems
    heat = Column(String(1), nullable=True)
    heat_pct = Column(String(2), nullable=True)
    air = Column(String(1), nullable=True)
    air_pct = Column(String(2), nullable=True)

    # Bathrooms
    bath = Column(String(1), nullable=True)
    bath_fixtures = Column(String(3), nullable=True)

    # Built-in features
    builtin_1_description = Column(String(15), nullable=True)
    builtin_2_description = Column(String(15), nullable=True)
    builtin_3_description = Column(String(15), nullable=True)
    builtin_4_description = Column(String(15), nullable=True)
    builtin_5_description = Column(String(15), nullable=True)

    # Quality and condition
    grade = Column(String(5), nullable=True)
    assessed_grade_difference = Column(String(3), nullable=True)
    accrued_assessed_condition_pct = Column(String(3), nullable=True)

    # Deferred values
    land_deferred_code = Column(String(1), nullable=True)
    land_deferred_amount = Column(Float, nullable=True)
    historic_deferred_code = Column(String(1), nullable=True)
    historic_deferred_amount = Column(Float, nullable=True)

    # Additional flags
    recycled_units = Column(Integer, nullable=True)
    disqualifying_qualifying_flags = Column(String(1), nullable=True)
    land_disqualify_qualify_flag = Column(String(1), nullable=True)

    # Metadata
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class StagingRedfinListing(Base):
    """Redfin listing data parsed from SingleFile HTML snapshots.

    Upsert pattern keyed on address. Photos stored in S3, HTML archived after parsing.
    """

    __tablename__ = "staging_redfin_listings"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Address
    address = Column(String, nullable=True, index=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)

    # Status
    listing_status = Column(String, nullable=True)
    sold_date = Column(String, nullable=True)
    sold_price = Column(String, nullable=True)

    # Key stats
    listing_price = Column(String, nullable=True)
    beds = Column(Integer, nullable=True)
    baths = Column(Float, nullable=True)
    sqft = Column(Integer, nullable=True)

    # Description
    description = Column(Text, nullable=True)

    # Key details
    year_built = Column(Integer, nullable=True)
    lot_size = Column(String, nullable=True)
    price_per_sqft = Column(String, nullable=True)

    # Agent info
    listing_agent = Column(String, nullable=True)
    listing_brokerage = Column(String, nullable=True)
    buying_agent = Column(String, nullable=True)
    buying_brokerage = Column(String, nullable=True)

    # Redfin estimate
    redfin_estimate = Column(String, nullable=True)

    # JSON fields
    sale_history = Column(JSON, nullable=True)
    tax_history = Column(JSON, nullable=True)
    property_details = Column(JSON, nullable=True)
    schools = Column(JSON, nullable=True)

    # Climate risk
    climate_flood_factor = Column(String, nullable=True)
    climate_fire_factor = Column(String, nullable=True)

    # Photos and source
    photo_s3_paths = Column(JSON, nullable=True)
    source_file = Column(String, nullable=True)

    # Metadata
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class RedfinListing(Base):
    """Production property record transformed from staging Redfin data (silver layer)."""

    __tablename__ = "redfin_listings"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Location
    street_address = Column(String, nullable=False, index=True)
    city = Column(String, nullable=True)
    state = Column(String(2), nullable=True)
    zip_code = Column(String(10), nullable=True)
    location = Column(Geometry("POINT", srid=4326), nullable=True)

    # Listing
    listing_status = Column(String, nullable=True)
    sold_date = Column(DateTime, nullable=True)
    sold_price = Column(Float, nullable=True)
    listing_price = Column(Float, nullable=True)
    description = Column(Text, nullable=True)

    # Climate risk
    flood_factor = Column(String, nullable=True)
    fire_factor = Column(String, nullable=True)
    flood_score = Column(Integer, nullable=True)
    fire_score = Column(Integer, nullable=True)

    # Parking
    has_garage = Column(Boolean, default=False, server_default=text("false"))
    num_garage_spaces = Column(Integer, nullable=True)
    parking_type = Column(String, nullable=True)
    garage_entry = Column(String, nullable=True)
    driveway_surface = Column(String, nullable=True)
    has_workshop = Column(Boolean, default=False, server_default=text("false"))
    has_circular_driveway = Column(Boolean, default=False, server_default=text("false"))
    has_ev_charging = Column(Boolean, default=False, server_default=text("false"))
    num_parking_spaces = Column(Integer, nullable=True)

    # Fireplace
    has_fireplace = Column(Boolean, default=False, server_default=text("false"))
    has_outdoor_fireplace = Column(Boolean, default=False, server_default=text("false"))
    has_primary_fireplace = Column(Boolean, default=False, server_default=text("false"))
    has_architectural_fireplace = Column(Boolean, default=False, server_default=text("false"))
    fireplace_fuel_source = Column(String, nullable=True)
    num_fireplaces = Column(Integer, nullable=True)

    # Appliances / energy
    water_heater_energy_source = Column(String, nullable=True)
    cooktop_energy_source = Column(String, nullable=True)
    oven_energy_source = Column(String, nullable=True)
    has_drink_fridge = Column(Boolean, default=False, server_default=text("false"))
    has_stainless_appliances = Column(Boolean, default=False, server_default=text("false"))
    appliances_included_count = Column(Integer, nullable=True)

    # Windows
    has_efficient_windows = Column(Boolean, default=False, server_default=text("false"))
    has_skylights = Column(Boolean, default=False, server_default=text("false"))
    has_bay_window = Column(Boolean, default=False, server_default=text("false"))

    # Laundry
    laundry_location = Column(String, nullable=True)
    has_laundry_room = Column(Boolean, default=False, server_default=text("false"))
    has_utility_sink = Column(Boolean, default=False, server_default=text("false"))

    # Interior features
    countertop_material = Column(String, nullable=True)
    is_primary_downstairs = Column(Boolean, default=False, server_default=text("false"))
    has_guest_suite = Column(Boolean, default=False, server_default=text("false"))
    has_butler_pantry = Column(Boolean, default=False, server_default=text("false"))
    has_walkin_closets = Column(Boolean, default=False, server_default=text("false"))
    has_tall_ceilings = Column(Boolean, default=False, server_default=text("false"))
    has_luxury_ceilings = Column(Boolean, default=False, server_default=text("false"))
    has_sauna = Column(Boolean, default=False, server_default=text("false"))
    has_bar = Column(Boolean, default=False, server_default=text("false"))
    has_second_primary = Column(Boolean, default=False, server_default=text("false"))
    has_room_over_garage = Column(Boolean, default=False, server_default=text("false"))
    has_open_floorplan = Column(Boolean, default=False, server_default=text("false"))

    # Flooring
    is_carpet_free = Column(Boolean, default=False, server_default=text("false"))
    has_premium_stone = Column(Boolean, default=False, server_default=text("false"))
    has_hardwood = Column(Boolean, default=False, server_default=text("false"))
    has_crawl_space = Column(Boolean, default=False, server_default=text("false"))

    # Exterior / structure
    facade_type = Column(String, nullable=True)
    building_area = Column(Float, nullable=True)
    above_grade_finished_area = Column(Float, nullable=True)
    below_grade_finished_area = Column(Float, nullable=True)
    num_stories = Column(Float, nullable=True)
    lot_size = Column(Float, nullable=True)
    is_waterfront = Column(Boolean, default=False, server_default=text("false"))
    buyer_financing = Column(String, nullable=True)

    # Utilities
    is_septic = Column(Boolean, default=False, server_default=text("false"))
    is_well_water = Column(Boolean, default=False, server_default=text("false"))
    no_heating = Column(Boolean, default=False, server_default=text("false"))
    no_cooling = Column(Boolean, default=False, server_default=text("false"))

    # HOA / community
    has_hoa = Column(Boolean, default=False, server_default=text("false"))
    association_fee = Column(Float, nullable=True)
    hoa_name = Column(String, nullable=True)

    # Porch / outdoor
    has_enclosed_porch = Column(Boolean, default=False, server_default=text("false"))
    has_front_porch = Column(Boolean, default=False, server_default=text("false"))
    has_fenced_yard = Column(Boolean, default=False, server_default=text("false"))
    has_outdoor_kitchen = Column(Boolean, default=False, server_default=text("false"))
    has_sport_court = Column(Boolean, default=False, server_default=text("false"))
    has_private_pool = Column(Boolean, default=False, server_default=text("false"))
    has_community_pool = Column(Boolean, default=False, server_default=text("false"))
    has_clubhouse = Column(Boolean, default=False, server_default=text("false"))
    has_exterior_storage = Column(Boolean, default=False, server_default=text("false"))
    has_garden = Column(Boolean, default=False, server_default=text("false"))

    # Core stats
    year_built = Column(Integer, nullable=True)
    year_renovated = Column(Integer, nullable=True)
    num_beds = Column(Integer, nullable=True)
    num_baths = Column(Float, nullable=True)
    sqft = Column(Integer, nullable=True)
    price_per_sqft = Column(Float, nullable=True)

    # Agents
    listing_agent = Column(String, nullable=True)
    listing_brokerage = Column(String, nullable=True)
    buying_agent = Column(String, nullable=True)
    buying_brokerage = Column(String, nullable=True)

    # Identifiers
    apn = Column(String, nullable=True)
    contract_date = Column(DateTime, nullable=True)

    # Raw data for UI
    property_details = Column(JSON, nullable=True)

    # Photos and source
    property_photos = Column(JSON, nullable=True)
    source_file = Column(String, nullable=True)

    # Change detection
    staging_hash = Column(String(64), nullable=True)

    # Metadata
    processed_at = Column(DateTime(timezone=True), server_default=func.now())
    schools_built_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_redfin_listings_location", "location", postgresql_using="gist"),
        Index(
            "uq_redfin_listings_address",
            "street_address",
            "city",
            "state",
            "zip_code",
            unique=True,
        ),
    )


class SaleHistoryRecord(Base):
    """Individual sale event linked to a Redfin listing."""

    __tablename__ = "sale_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(Integer, nullable=False, index=True)
    date = Column(DateTime, nullable=True)
    event = Column(String, nullable=True)
    price = Column(Float, nullable=True)
    source = Column(String, nullable=True)


class TaxHistoryRecord(Base):
    """Individual tax assessment linked to a Redfin listing."""

    __tablename__ = "tax_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(Integer, nullable=False, index=True)
    date = Column(DateTime, nullable=True)
    property_tax = Column(Float, nullable=True)
    assessment_value_land = Column(Float, nullable=True)
    assessment_value_additions = Column(Float, nullable=True)
    assessment_value = Column(Float, nullable=True)
    source = Column(String, nullable=True)


class PropertyValuation(Base):
    """Property valuation from various sources (Redfin, ML model, etc.)."""

    __tablename__ = "property_valuations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(Integer, nullable=False, index=True)
    source = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    model_version = Column(String, nullable=True)
    confidence_low = Column(Float, nullable=True)
    confidence_high = Column(Float, nullable=True)
    estimated_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("idx_property_valuations_property_source", "property_id", "source"),)


class RedfinPropertySchool(Base):
    """Raw linkage between properties and Redfin-extracted schools (bronze layer)."""

    __tablename__ = "redfin_property_schools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(Integer, nullable=False, index=True)
    redfin_school_id = Column(Integer, nullable=False, index=True)

    __table_args__ = (
        Index(
            "uq_redfin_property_school",
            "property_id",
            "redfin_school_id",
            unique=True,
        ),
    )


class School(Base):
    """Master school record built from NCES + Redfin data (gold layer)."""

    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nces_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    street = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String(2), nullable=True)
    zip_code = Column(String(10), nullable=True)
    school_type = Column(String, nullable=True)
    school_level = Column(String, nullable=True)
    grades = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    location = Column(Geometry("POINT", srid=4326), nullable=True)
    enrollment = Column(Integer, nullable=True)
    teachers = Column(Float, nullable=True)
    student_teacher_ratio = Column(Float, nullable=True)
    free_lunch_eligible = Column(Integer, nullable=True)
    reduced_lunch_eligible = Column(Integer, nullable=True)
    total_frl_eligible = Column(Integer, nullable=True)
    pct_frl_eligible = Column(Float, nullable=True)
    district_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("idx_schools_location", "location", postgresql_using="gist"),)


class PropertySchool(Base):
    """Linkage between properties and gold schools."""

    __tablename__ = "property_schools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(Integer, nullable=False, index=True)
    school_id = Column(Integer, nullable=False, index=True)
    assigned = Column(Boolean, default=False, server_default=text("false"))
    distance_miles = Column(Float, nullable=True)
    drive_minutes = Column(Integer, nullable=True)
    walk_minutes = Column(Integer, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index(
            "uq_property_school",
            "property_id",
            "school_id",
            unique=True,
        ),
    )


class NcesSchool(Base):
    """NCES school directory reference data."""

    __tablename__ = "nces_schools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nces_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    street = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String(2), nullable=True)
    zip_code = Column(String(10), nullable=True)
    school_type = Column(String, nullable=True)
    school_level = Column(String, nullable=True)
    grades_low = Column(String, nullable=True)
    grades_high = Column(String, nullable=True)
    location = Column(Geometry("POINT", srid=4326), nullable=True)
    extras = Column(JSON, nullable=True)
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class WakeSubdivision(Base):
    """Wake County subdivision boundary from ArcGIS MapServer."""

    __tablename__ = "wake_subdivisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    objectid = Column(Integer, index=True)
    name = Column(String(40))
    snumber = Column(String(10), index=True)
    access_rd = Column(String(30))
    jurisdiction = Column(String(25))
    status = Column(String(20))
    acres = Column(Float)
    lots = Column(Integer)
    density = Column(Float)
    mapclass = Column(Integer)
    iscluster = Column(String(5))
    approvdate = Column(DateTime(timezone=True))
    appldate = Column(DateTime(timezone=True))
    last_edited_date = Column(DateTime(timezone=True))
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class WakeFarmersMarket(Base):
    """Wake County farmers market location from ArcGIS."""

    __tablename__ = "wake_farmers_markets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    objectid = Column(Integer, index=True)
    name = Column(String, index=True)
    location_desc = Column(String)
    organization = Column(String)
    active_day = Column(String)
    months = Column(String)
    hours = Column(String)
    website = Column(String)
    phone = Column(String)
    geom = Column(Geometry("POINT", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class WakeLibrary(Base):
    """Wake County library location from ArcGIS."""

    __tablename__ = "wake_libraries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    objectid = Column(Integer, index=True)
    name = Column(String, index=True)
    address = Column(String)
    city = Column(String)
    code = Column(String)
    label = Column(String)
    status = Column(String)
    facility_type = Column(String)
    hours_mt = Column(String)
    hours_fri = Column(String)
    hours_sat = Column(String)
    hours_sun = Column(String)
    geom = Column(Geometry("POINT", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class WakeHospital(Base):
    """Wake County hospital location from ArcGIS."""

    __tablename__ = "wake_hospitals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    objectid = Column(Integer, index=True)
    facility = Column(String, index=True)
    address = Column(String)
    city = Column(String)
    acute_care = Column(String)
    url = Column(String)
    telephone = Column(String)
    gis_edit_date = Column(DateTime(timezone=True))
    geom = Column(Geometry("POINT", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class WakePark(Base):
    """Wake County open space / park from ArcGIS MapServer."""

    __tablename__ = "wake_parks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    objectid = Column(Integer, index=True)
    name = Column(String, index=True)
    acres = Column(Float)
    owner = Column(String)
    jurisdiction = Column(String)
    park_type = Column(String)
    manager = Column(String)
    comments = Column(String)
    corridor = Column(String)
    os_number = Column(String)
    created_date = Column(DateTime(timezone=True))
    last_edited_date = Column(DateTime(timezone=True))
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class RaleighPark(Base):
    """City of Raleigh park from ArcGIS FeatureServer."""

    __tablename__ = "raleigh_parks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    objectid = Column(Integer, index=True)
    name = Column(String, index=True)
    park_type = Column(String)
    developed = Column(String)
    map_acres = Column(Float)
    address = Column(String)
    zip_code = Column(String)
    park_id = Column(String)
    initial_acquisition_date = Column(DateTime(timezone=True))
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class CaryPark(Base):
    """Town of Cary park with amenity details from ArcGIS FeatureServer."""

    __tablename__ = "cary_parks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    objectid = Column(Integer, index=True)
    name = Column(String, index=True)
    facility_id = Column(String)
    address = Column(String)
    park_area = Column(Float)
    park_url = Column(String)
    num_parking = Column(Integer)
    restroom = Column(String)
    ada_compliant = Column(String)
    camping = Column(String)
    swimming = Column(String)
    hiking = Column(String)
    fishing = Column(String)
    picnic = Column(String)
    boating = Column(String)
    road_cycle = Column(String)
    mtb_cycle = Column(String)
    playground = Column(String)
    golf = Column(String)
    soccer = Column(String)
    baseball = Column(String)
    basketball = Column(String)
    skatepark = Column(String)
    tennis_court = Column(String)
    volleyball = Column(String)
    fitness_trail = Column(String)
    nature_trail = Column(String)
    trailhead = Column(String)
    open_space = Column(String)
    lake = Column(String)
    amphitheater = Column(String)
    dog_park = Column(String)
    disc_golf = Column(String)
    climbing_rocks = Column(String)
    climbing_ropes = Column(String)
    batting_cages = Column(String)
    geom = Column(Geometry("POINT", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class WakeGreenway(Base):
    """Wake County greenway trail from ArcGIS MapServer."""

    __tablename__ = "wake_greenways"

    id = Column(Integer, primary_key=True, autoincrement=True)
    objectid = Column(Integer, index=True)
    trail_name = Column(String, index=True)
    corridor_name = Column(String)
    owner = Column(String)
    trail_status = Column(String)
    trail_surface = Column(String)
    trail_class = Column(String)
    length = Column(Float)
    width = Column(Float)
    open_date = Column(DateTime(timezone=True))
    public_access = Column(String)
    accessibility_status = Column(String)
    geom = Column(Geometry("MULTILINESTRING", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class RaleighGreenway(Base):
    """City of Raleigh greenway trail from ArcGIS FeatureServer."""

    __tablename__ = "raleigh_greenways"

    id = Column(Integer, primary_key=True, autoincrement=True)
    objectid = Column(Integer, index=True)
    trail_name = Column(String, index=True)
    greenway_type = Column(String)
    location_desc = Column(String)
    status = Column(String)
    material = Column(String)
    map_miles = Column(Float)
    width_ft = Column(Float)
    owner = Column(String)
    ada = Column(String)
    gw_status = Column(String)
    geom = Column(Geometry("MULTILINESTRING", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class CaryGreenway(Base):
    """Town of Cary greenway trail from ArcGIS FeatureServer."""

    __tablename__ = "cary_greenways"

    id = Column(Integer, primary_key=True, autoincrement=True)
    objectid = Column(Integer, index=True)
    name = Column(String, index=True)
    segment = Column(String)
    length = Column(Float)
    width = Column(Float)
    trail_type = Column(String)
    surface_type = Column(String)
    status = Column(String)
    install_date = Column(DateTime(timezone=True))
    open_to_public = Column(String)
    geom = Column(Geometry("MULTILINESTRING", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class WakeRailroad(Base):
    """Wake County railroad from ArcGIS FeatureServer."""

    __tablename__ = "wake_railroads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    objectid = Column(Integer, index=True)
    branch_or = Column(String)
    track_type = Column(String)
    track_owner = Column(String)
    shape_length = Column(Float)
    geom = Column(Geometry("MULTILINESTRING", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class WakeMajorRoad(Base):
    """Wake County major road from ArcGIS FeatureServer."""

    __tablename__ = "wake_major_roads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    objectid = Column(Integer, index=True)
    street_name = Column(String, index=True)
    street_type = Column(String)
    dir_prefix = Column(String)
    dir_suffix = Column(String)
    state_road = Column(String)
    carto_name = Column(String)
    corporation = Column(String)
    class_name = Column(String)
    label_name = Column(String)
    geom = Column(Geometry("MULTILINESTRING", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class WakeHighway(Base):
    """Wake County highway from ArcGIS FeatureServer."""

    __tablename__ = "wake_highways"

    id = Column(Integer, primary_key=True, autoincrement=True)
    objectid = Column(Integer, index=True)
    street_name = Column(String, index=True)
    street_type = Column(String)
    dir_prefix = Column(String)
    dir_suffix = Column(String)
    from_left = Column(Integer)
    to_left = Column(Integer)
    from_right = Column(Integer)
    to_right = Column(Integer)
    state_road = Column(String)
    carto_name = Column(String)
    corporation = Column(String)
    class_name = Column(String)
    label_name = Column(String)
    geom = Column(Geometry("MULTILINESTRING", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class WakeUtilityEasement(Base):
    """Wake County utility easement from ArcGIS MapServer."""

    __tablename__ = "wake_utility_easements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    objectid = Column(Integer, index=True)
    length = Column(Float)
    ftr_code = Column(String)
    status = Column(String)
    geom = Column(Geometry("MULTILINESTRING", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class LlmQualityScore(Base):
    """LLM-generated property quality score from listing description analysis.

    Versioned by (listing_id, model_name, model_version) so multiple model
    versions can coexist for comparison and gold-layer promotion.
    """

    __tablename__ = "llm_quality_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, nullable=False, index=True)
    model_name = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    description_hash = Column(String(64), nullable=False)
    quality_score = Column(Integer, nullable=True)
    quality_reasoning = Column(Text, nullable=True)
    positive_factors = Column(JSON, nullable=True)
    negative_factors = Column(JSON, nullable=True)
    raw_response = Column(JSON, nullable=False)
    extracted_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "listing_id",
            "model_name",
            "model_version",
            name="uq_llm_score_listing_model",
        ),
    )


class LlmPhotoScore(Base):
    """LLM-based photo quality scores for property listings."""

    __tablename__ = "llm_photo_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, nullable=False, index=True)
    model_name = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    photos_hash = Column(String(64), nullable=False)
    visual_quality_score = Column(Integer, nullable=True)
    visual_reasoning = Column(Text, nullable=True)
    detected_features = Column(JSON, nullable=True)
    renovation_level = Column(String, nullable=True)
    raw_response = Column(JSON, nullable=False)
    extracted_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "listing_id",
            "model_name",
            "model_version",
            name="uq_llm_photo_score_listing_model",
        ),
    )


class AcsTractDemographic(Base):
    """ACS 5-Year demographic estimates at census tract level.

    No geometry; join to tiger_tracts via geoid.
    """

    __tablename__ = "acs_tract_demographics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    geoid = Column(String(11), nullable=False, index=True)
    name = Column(String, nullable=True)
    acs_year = Column(Integer, nullable=False, index=True)

    # Population (B01001)
    total_population = Column(Integer, nullable=True)
    male_population = Column(Integer, nullable=True)
    female_population = Column(Integer, nullable=True)

    # Age (aggregated from B01001 sub-vars)
    pop_under_18 = Column(Integer, nullable=True)
    pop_18_to_34 = Column(Integer, nullable=True)
    pop_35_to_54 = Column(Integer, nullable=True)
    pop_55_to_64 = Column(Integer, nullable=True)
    pop_65_plus = Column(Integer, nullable=True)
    median_age = Column(Float, nullable=True)

    # Race (B02001)
    race_white = Column(Integer, nullable=True)
    race_black = Column(Integer, nullable=True)
    race_american_indian = Column(Integer, nullable=True)
    race_asian = Column(Integer, nullable=True)
    race_pacific_islander = Column(Integer, nullable=True)
    race_other = Column(Integer, nullable=True)
    race_two_or_more = Column(Integer, nullable=True)

    # Hispanic (B03003)
    hispanic_total = Column(Integer, nullable=True)
    not_hispanic = Column(Integer, nullable=True)
    hispanic = Column(Integer, nullable=True)

    # Income brackets (B19001)
    total_households = Column(Integer, nullable=True)
    hh_income_under_10k = Column(Integer, nullable=True)
    hh_income_10k_to_15k = Column(Integer, nullable=True)
    hh_income_15k_to_20k = Column(Integer, nullable=True)
    hh_income_20k_to_25k = Column(Integer, nullable=True)
    hh_income_25k_to_30k = Column(Integer, nullable=True)
    hh_income_30k_to_35k = Column(Integer, nullable=True)
    hh_income_35k_to_40k = Column(Integer, nullable=True)
    hh_income_40k_to_45k = Column(Integer, nullable=True)
    hh_income_45k_to_50k = Column(Integer, nullable=True)
    hh_income_50k_to_60k = Column(Integer, nullable=True)
    hh_income_60k_to_75k = Column(Integer, nullable=True)
    hh_income_75k_to_100k = Column(Integer, nullable=True)
    hh_income_100k_to_125k = Column(Integer, nullable=True)
    hh_income_125k_to_150k = Column(Integer, nullable=True)
    hh_income_150k_to_200k = Column(Integer, nullable=True)
    hh_income_200k_plus = Column(Integer, nullable=True)

    # Median income (B19013)
    median_household_income = Column(Integer, nullable=True)

    # Education (B15003, aggregated into 5 buckets, pop 25+)
    edu_total = Column(Integer, nullable=True)
    edu_less_than_hs = Column(Integer, nullable=True)
    edu_high_school = Column(Integer, nullable=True)
    edu_some_college = Column(Integer, nullable=True)
    edu_bachelors = Column(Integer, nullable=True)
    edu_graduate_plus = Column(Integer, nullable=True)

    # Home ownership (B25003)
    housing_total_occupied = Column(Integer, nullable=True)
    housing_owner_occupied = Column(Integer, nullable=True)
    housing_renter_occupied = Column(Integer, nullable=True)

    # Home value (B25077)
    median_home_value = Column(Integer, nullable=True)

    loaded_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("geoid", "acs_year", name="uq_acs_tract_geoid_year"),
    )


class AcsBlockGroupDemographic(Base):
    """ACS 5-Year demographic estimates at block group level.

    No geometry; join to tiger_block_groups via geoid.
    """

    __tablename__ = "acs_block_group_demographics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    geoid = Column(String(12), nullable=False, index=True)
    name = Column(String, nullable=True)
    acs_year = Column(Integer, nullable=False, index=True)

    # Population (B01001)
    total_population = Column(Integer, nullable=True)
    male_population = Column(Integer, nullable=True)
    female_population = Column(Integer, nullable=True)

    # Age (aggregated from B01001 sub-vars)
    pop_under_18 = Column(Integer, nullable=True)
    pop_18_to_34 = Column(Integer, nullable=True)
    pop_35_to_54 = Column(Integer, nullable=True)
    pop_55_to_64 = Column(Integer, nullable=True)
    pop_65_plus = Column(Integer, nullable=True)
    median_age = Column(Float, nullable=True)

    # Race (B02001)
    race_white = Column(Integer, nullable=True)
    race_black = Column(Integer, nullable=True)
    race_american_indian = Column(Integer, nullable=True)
    race_asian = Column(Integer, nullable=True)
    race_pacific_islander = Column(Integer, nullable=True)
    race_other = Column(Integer, nullable=True)
    race_two_or_more = Column(Integer, nullable=True)

    # Hispanic (B03003)
    hispanic_total = Column(Integer, nullable=True)
    not_hispanic = Column(Integer, nullable=True)
    hispanic = Column(Integer, nullable=True)

    # Income brackets (B19001)
    total_households = Column(Integer, nullable=True)
    hh_income_under_10k = Column(Integer, nullable=True)
    hh_income_10k_to_15k = Column(Integer, nullable=True)
    hh_income_15k_to_20k = Column(Integer, nullable=True)
    hh_income_20k_to_25k = Column(Integer, nullable=True)
    hh_income_25k_to_30k = Column(Integer, nullable=True)
    hh_income_30k_to_35k = Column(Integer, nullable=True)
    hh_income_35k_to_40k = Column(Integer, nullable=True)
    hh_income_40k_to_45k = Column(Integer, nullable=True)
    hh_income_45k_to_50k = Column(Integer, nullable=True)
    hh_income_50k_to_60k = Column(Integer, nullable=True)
    hh_income_60k_to_75k = Column(Integer, nullable=True)
    hh_income_75k_to_100k = Column(Integer, nullable=True)
    hh_income_100k_to_125k = Column(Integer, nullable=True)
    hh_income_125k_to_150k = Column(Integer, nullable=True)
    hh_income_150k_to_200k = Column(Integer, nullable=True)
    hh_income_200k_plus = Column(Integer, nullable=True)

    # Median income (B19013)
    median_household_income = Column(Integer, nullable=True)

    # Education (B15003, aggregated into 5 buckets, pop 25+)
    edu_total = Column(Integer, nullable=True)
    edu_less_than_hs = Column(Integer, nullable=True)
    edu_high_school = Column(Integer, nullable=True)
    edu_some_college = Column(Integer, nullable=True)
    edu_bachelors = Column(Integer, nullable=True)
    edu_graduate_plus = Column(Integer, nullable=True)

    # Home ownership (B25003)
    housing_total_occupied = Column(Integer, nullable=True)
    housing_owner_occupied = Column(Integer, nullable=True)
    housing_renter_occupied = Column(Integer, nullable=True)

    # Home value (B25077)
    median_home_value = Column(Integer, nullable=True)

    loaded_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("geoid", "acs_year", name="uq_acs_block_group_geoid_year"),
    )


class EconomicIndicator(Base):
    """Macroeconomic time-series observation from FRED."""

    __tablename__ = "economic_indicators"

    id = Column(Integer, primary_key=True, autoincrement=True)
    series_id = Column(String, nullable=False)
    observation_date = Column(Date, nullable=False)
    value = Column(Float, nullable=False)
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("series_id", "observation_date", name="uq_economic_series_date"),
        Index("idx_economic_series_date", "series_id", "observation_date"),
    )


class User(Base):
    """Application user account."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, server_default=text("true"))
    is_admin = Column(Boolean, default=False, server_default=text("false"))
    oauth_provider = Column(String, nullable=True)
    oauth_id = Column(String, nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SavedProperty(Base):
    """Property saved/bookmarked by a user."""

    __tablename__ = "saved_properties"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    listing_id = Column(
        Integer,
        ForeignKey("redfin_listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "listing_id", name="uq_saved_property_user_listing"),
    )


class DataRequest(Base):
    """User request to populate data for a property not yet in the database."""

    __tablename__ = "data_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    address = Column(String, nullable=False, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    status = Column(String, nullable=False, server_default=text("'pending'"))
    requested_by_email = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ApiKey(Base):
    """API key for programmatic access."""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key_hash = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, server_default=text("true"))

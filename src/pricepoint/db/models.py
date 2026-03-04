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


class Block(Base):
    """US Census TIGER/Line census block boundaries (TABBLOCK20)."""

    __tablename__ = "blocks"

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


class BlockGroup(Base):
    """US Census TIGER/Line block group boundaries (BG)."""

    __tablename__ = "block_groups"

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


class Tract(Base):
    """US Census TIGER/Line census tract boundaries (TRACT)."""

    __tablename__ = "tracts"

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


class SchoolDistrict(Base):
    """US Census TIGER/Line school district boundaries (ELSD/SCSD/UNSD combined)."""

    __tablename__ = "school_districts"

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

    __table_args__ = (Index("idx_school_districts_geom", "geom", postgresql_using="gist"),)


class County(Base):
    """US Census TIGER/Line county boundaries (COUNTY)."""

    __tablename__ = "counties"

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


class Township(Base):
    """US Census TIGER/Line county subdivision boundaries (COUSUB)."""

    __tablename__ = "townships"

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


class Road(Base):
    """TIGER/Line primary and secondary road centerlines (PRISECROADS).

    Combines S1100 (primary) and S1200 (secondary) MTFCC classes from
    state-level PRISECROADS shapefiles into a single table.
    """

    __tablename__ = "roads"
    __table_args__ = (Index("ix_roads_geom", "geom", postgresql_using="gist"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    linearid = Column(String(22), unique=True, index=True)
    fullname = Column(String(100))
    rttyp = Column(String(1))
    mtfcc = Column(String(5))
    geom = Column(Geometry("MULTILINESTRING", srid=4326))
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


class PropertyGeoLookup(Base):
    """Precomputed geographic containment lookups for properties (gold layer).

    Maps each property to its containing census tract, block group, county
    subdivision, noise zone, risk zone, and school district.  Eliminates
    repeated ST_Contains spatial queries at API request time.
    """

    __tablename__ = "property_geo_lookups"
    __table_args__ = (
        Index("ix_property_geo_lookups_tract", "census_tract_geoid"),
        Index("ix_property_geo_lookups_bg", "census_block_group_geoid"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(
        Integer,
        ForeignKey("redfin_listings.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    census_tract_geoid = Column(String(11), nullable=True)
    census_block_group_geoid = Column(String(12), nullable=True)
    county_subdivision_geoid = Column(String(10), nullable=True)
    county_geoid = Column(String(5), nullable=True)
    subdivision_id = Column(Integer, nullable=True)
    subdivision_name = Column(String, nullable=True)
    in_noise_zone = Column(Boolean, default=False, server_default=text("false"))
    noise_max_db = Column(Integer, nullable=True)
    noise_source_layers = Column(JSON, nullable=True)
    in_risk_zone = Column(Boolean, default=False, server_default=text("false"))
    risk_max_severity = Column(String, nullable=True)
    risk_types = Column(JSON, nullable=True)
    school_district_geoid = Column(String(7), nullable=True)
    dist_nearest_school_m = Column(Float, nullable=True)
    dist_nearest_elementary_m = Column(Float, nullable=True)
    dist_nearest_middle_m = Column(Float, nullable=True)
    dist_nearest_high_m = Column(Float, nullable=True)
    dist_nearest_park_m = Column(Float, nullable=True)
    dist_nearest_greenway_m = Column(Float, nullable=True)
    dist_nearest_hospital_m = Column(Float, nullable=True)
    avg_school_rating = Column(Float, nullable=True)
    avg_school_drive = Column(Float, nullable=True)
    in_critical_risk_zone = Column(Boolean, default=False, server_default=text("false"))
    built_at = Column(DateTime(timezone=True), server_default=func.now())


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


class Subdivision(Base):
    """Gold subdivision boundary — all counties, keyed by (county_fips, source_id)."""

    __tablename__ = "subdivisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    county_fips = Column(String(5), nullable=False)
    source_id = Column(String(50), nullable=False)
    name = Column(String, nullable=True)
    acres = Column(Float, nullable=True)
    lots = Column(Integer, nullable=True)
    density = Column(Float, nullable=True)
    geom = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    built_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("county_fips", "source_id", name="uq_subdivisions_county_source"),
        Index("ix_subdivisions_geom", "geom", postgresql_using="gist"),
        Index("ix_subdivisions_name", "name"),
        Index("ix_subdivisions_county_fips", "county_fips"),
    )


class Hospital(Base):
    """Hospital location from HIFLD."""

    __tablename__ = "hospitals"
    __table_args__ = (Index("ix_hospitals_geom", "geom", postgresql_using="gist"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    objectid = Column(Integer, index=True)
    hifld_id = Column(String, index=True)
    name = Column(String, index=True)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    telephone = Column(String)
    hospital_type = Column(String)
    status = Column(String)
    population = Column(Integer)
    county = Column(String)
    countyfips = Column(String)
    owner = Column(String)
    beds = Column(Integer)
    trauma = Column(String)
    helipad = Column(String)
    website = Column(String)
    naics_code = Column(String)
    naics_desc = Column(String)
    ttl_staff = Column(Integer)
    geom = Column(Geometry("POINT", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class Greenspace(Base):
    """Protected area / greenspace from PAD-US (Fee layer)."""

    __tablename__ = "greenspaces"
    __table_args__ = (Index("ix_greenspaces_geom", "geom", postgresql_using="gist"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String, index=True)
    gis_acres = Column(Float)
    manager_type = Column(String(10))
    manager_name = Column(String)
    designation_type = Column(String(20))
    pub_access = Column(String(2))
    gap_sts = Column(Integer)
    state_name = Column(String)
    category = Column(String)
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class Trail(Base):
    """Trail from USGS National Digital Trails dataset."""

    __tablename__ = "trails"
    __table_args__ = (Index("ix_trails_geom", "geom", postgresql_using="gist"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    permanentidentifier = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, index=True)
    trail_type = Column(String)
    length_miles = Column(Float)
    maintainer = Column(String)
    national_designation = Column(String)
    hiker_pedestrian = Column(String)
    bicycle = Column(String)
    pack_saddle = Column(String)
    atv = Column(String)
    motorcycle = Column(String)
    ohv_over_50_inches = Column(String)
    snowshoe = Column(String)
    cross_country_ski = Column(String)
    dogsled = Column(String)
    snowmobile = Column(String)
    non_motorized_watercraft = Column(String)
    motorized_watercraft = Column(String)
    geom = Column(Geometry("MULTILINESTRING", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class CellTower(Base):
    """Cell tower location from HIFLD ArcGIS FeatureServer."""

    __tablename__ = "cell_towers"
    __table_args__ = (Index("ix_cell_towers_geom", "geom", postgresql_using="gist"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    objectid = Column(Integer, index=True)
    licensee = Column(String)
    callsign = Column(String)
    city = Column(String)
    state = Column(String)
    county = Column(String)
    structure_type = Column(String)
    height_ft = Column(Float)
    geom = Column(Geometry("POINT", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class TransmissionLine(Base):
    """Electric power transmission line from HIFLD ArcGIS FeatureServer."""

    __tablename__ = "transmission_lines"
    __table_args__ = (Index("ix_transmission_lines_geom", "geom", postgresql_using="gist"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    objectid = Column(Integer, index=True)
    line_type = Column(String)
    status = Column(String)
    owner = Column(String)
    voltage = Column(Float)
    volt_class = Column(String)
    sub_1 = Column(String)
    sub_2 = Column(String)
    geom = Column(Geometry("MULTILINESTRING", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class PowerPlant(Base):
    """Power plant location from HIFLD ArcGIS FeatureServer."""

    __tablename__ = "power_plants"
    __table_args__ = (Index("ix_power_plants_geom", "geom", postgresql_using="gist"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    objectid = Column(Integer, index=True)
    plant_code = Column(Integer)
    name = Column(String, index=True)
    utility_name = Column(String)
    state = Column(String)
    county = Column(String)
    primary_source = Column(String)
    install_mw = Column(Float)
    total_mw = Column(Float)
    geom = Column(Geometry("POINT", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class NatGasPipeline(Base):
    """Natural gas pipeline from HIFLD ArcGIS FeatureServer."""

    __tablename__ = "nat_gas_pipelines"
    __table_args__ = (Index("ix_nat_gas_pipelines_geom", "geom", postgresql_using="gist"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    objectid = Column(Integer, index=True)
    pipe_type = Column(String)
    operator = Column(String)
    status = Column(String)
    geom = Column(Geometry("MULTILINESTRING", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class PetroleumPipeline(Base):
    """Petroleum products pipeline from HIFLD ArcGIS FeatureServer."""

    __tablename__ = "petroleum_pipelines"
    __table_args__ = (Index("ix_petroleum_pipelines_geom", "geom", postgresql_using="gist"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    objectid = Column(Integer, index=True)
    operator = Column(String)
    pipe_name = Column(String)
    geom = Column(Geometry("MULTILINESTRING", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class RiskBoundary(Base):
    """Pre-computed risk buffer polygon around infrastructure."""

    __tablename__ = "risk_boundaries"
    __table_args__ = (
        Index("ix_risk_boundaries_geom", "geom", postgresql_using="gist"),
        Index("ix_risk_boundaries_infra", "infrastructure_type", "infrastructure_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    infrastructure_type = Column(String, nullable=False)
    infrastructure_id = Column(Integer, nullable=False)
    severity = Column(String, nullable=False)
    geom = Column(Geometry("GEOMETRY", srid=4326))
    built_at = Column(DateTime(timezone=True), server_default=func.now())


class Railroad(Base):
    """HIFLD North American Rail Network lines (entire US)."""

    __tablename__ = "railroads"
    __table_args__ = (Index("ix_railroads_geom", "geom", postgresql_using="gist"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    fraarcid = Column(Integer, unique=True, index=True)
    rrowner1 = Column(String)
    rrowner2 = Column(String)
    rrowner3 = Column(String)
    stateab = Column(String(2))
    cntyfips = Column(String(5))
    subdivision = Column(String)
    branch = Column(String)
    passngr = Column(String)
    tracks = Column(Integer)
    miles = Column(Float)
    net = Column(String)
    geom = Column(Geometry("MULTILINESTRING", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class Airport(Base):
    """Airport location from OurAirports."""

    __tablename__ = "airports"
    __table_args__ = (
        Index("ix_airports_geom", "geom", postgresql_using="gist"),
        UniqueConstraint("ident", name="uq_airports_ident"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    ident = Column(String, nullable=False, index=True)
    airport_type = Column(String)
    name = Column(String, index=True)
    elevation_ft = Column(Integer)
    iso_region = Column(String)
    municipality = Column(String)
    scheduled_service = Column(Boolean)
    iata_code = Column(String)
    home_link = Column(String)
    wikipedia_link = Column(String)
    geom = Column(Geometry("POINT", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class TransportationNoise(Base):
    """Transportation noise polygon from BTS National Noise Map (aviation+road+rail)."""

    __tablename__ = "noises"
    __table_args__ = (
        Index("ix_noises_geom", "geom", postgresql_using="gist"),
        Index("ix_noises_noise_min_db", "noise_min_db"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    noise_min_db = Column(Integer, nullable=False)
    noise_max_db = Column(Integer, nullable=True)
    noise_band = Column(String, nullable=False)
    source_layer = Column(String, nullable=False)
    area_sq_m = Column(Float, nullable=True)
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class StagingTransportationNoise(Base):
    """Staging table for raw BTS noise polygons (pre-smoothing).

    Holds jagged per-batch polygons before PostGIS clustering, merging,
    and Chaikin smoothing promote them to the production ``noises`` table.
    """

    __tablename__ = "staging_noises"

    id = Column(Integer, primary_key=True, autoincrement=True)
    noise_min_db = Column(Integer, nullable=False)
    noise_max_db = Column(Integer, nullable=True)
    noise_band = Column(String, nullable=False)
    source_layer = Column(String, nullable=False)
    area_sq_m = Column(Float, nullable=True)
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class StagingPlace(Base):
    """Staging table for Overture Maps places (bronze).

    Raw data loaded from S3 GeoParquet. Truncated on each run.
    No unique constraints or spatial indexes — optimized for fast bulk writes.
    """

    __tablename__ = "staging_places"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String, nullable=False)
    name = Column(String)
    category = Column(String)
    alternate_categories = Column(JSON)
    confidence = Column(Float)
    operating_status = Column(String)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    postcode = Column(String)
    country = Column(String)
    brand_name = Column(String)
    brand_wikidata = Column(String)
    website = Column(String)
    phone = Column(String)
    email = Column(String)
    social = Column(String)
    source_dataset = Column(String)
    source_record_id = Column(String)
    geom = Column(Geometry("POINT", srid=4326))
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())


class Place(Base):
    """Commercial point of interest / place (production).

    FK-referenced by user preference tables — PKs must be preserved across
    reloads.  Use staging + upsert swap pattern (never truncate swap).
    """

    __tablename__ = "places"
    __table_args__ = (
        Index("ix_places_geom", "geom", postgresql_using="gist"),
        Index("ix_places_name", "name"),
        Index("ix_places_category", "category"),
        Index("ix_places_state", "state"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String)
    category = Column(String)
    alternate_categories = Column(JSON)
    confidence = Column(Float)
    operating_status = Column(String)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    postcode = Column(String)
    country = Column(String)
    brand_name = Column(String)
    brand_wikidata = Column(String)
    website = Column(String)
    phone = Column(String)
    email = Column(String)
    social = Column(String)
    source_dataset = Column(String)
    source_record_id = Column(String)
    geom = Column(Geometry("POINT", srid=4326))
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


class AcsDemographic(Base):
    """ACS 5-Year demographic estimates at multiple geographic levels.

    Stores demographics for: us, state, county, county_subdivision,
    tract, block_group, and subdivision (area-weighted from block groups).
    No geometry; join to appropriate TIGER table via geoid.
    """

    __tablename__ = "acs_demographics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    geography_level = Column(String(25), nullable=False, index=True)
    geoid = Column(String(15), nullable=False, index=True)
    name = Column(String, nullable=True)
    acs_year = Column(Integer, nullable=False, index=True)

    # Population (B01001)
    total_population = Column(Integer, nullable=True)
    male_population = Column(Integer, nullable=True)
    female_population = Column(Integer, nullable=True)

    # Age (aggregated from B01001 sub-vars)
    pop_under_18 = Column(Integer, nullable=True)
    pop_18_to_22 = Column(Integer, nullable=True)
    pop_23_to_29 = Column(Integer, nullable=True)
    pop_30_to_39 = Column(Integer, nullable=True)
    pop_40_to_49 = Column(Integer, nullable=True)
    pop_50_to_64 = Column(Integer, nullable=True)
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
        UniqueConstraint(
            "geography_level",
            "geoid",
            "acs_year",
            name="uq_acs_demo_level_geoid_year",
        ),
    )


class GreenspaceRegionMetric(Base):
    """Precomputed greenspace metrics at TIGER geographic levels.

    Stores park/trail counts, area ratios, and z-scores relative to
    peer regions for block_group, tract, county_subdivision, and county.
    """

    __tablename__ = "greenspace_region_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    geo_level = Column(String(25), nullable=False, index=True)
    geoid = Column(String(15), nullable=False, index=True)
    name = Column(String, nullable=True)

    # Raw counts
    park_count = Column(Integer, nullable=False, default=0)
    trail_count = Column(Integer, nullable=False, default=0)

    # Area / length
    total_park_acres = Column(Float, nullable=False, default=0.0)
    total_trail_miles = Column(Float, nullable=False, default=0.0)
    greenspace_area_sqm = Column(Float, nullable=False, default=0.0)
    region_land_area_sqm = Column(Float, nullable=False, default=0.0)
    greenspace_ratio = Column(Float, nullable=True)

    # Population-normalized
    population = Column(Integer, nullable=True)
    parks_per_1k_residents = Column(Float, nullable=True)
    greenspace_acres_per_1k_residents = Column(Float, nullable=True)

    # Z-scores (relative to peer regions)
    greenspace_ratio_zscore = Column(Float, nullable=True)
    park_count_zscore = Column(Float, nullable=True)
    trail_count_zscore = Column(Float, nullable=True)
    total_park_acres_zscore = Column(Float, nullable=True)
    total_trail_miles_zscore = Column(Float, nullable=True)
    parks_per_1k_zscore = Column(Float, nullable=True)
    greenspace_acres_per_1k_zscore = Column(Float, nullable=True)

    loaded_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("geo_level", "geoid", name="uq_greenspace_region_level_geoid"),
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


class SavedPoi(Base):
    """A POI (brand or name) saved by a user for proximity tracking."""

    __tablename__ = "saved_pois"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    match_type = Column(String, nullable=False)  # "brand" or "name"
    match_value = Column(String, nullable=False)  # exact value to match
    display_name = Column(String, nullable=False)  # UI label
    category = Column(String, nullable=True)  # informational, from Overture
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "match_type", "match_value", name="uq_saved_poi_user_match"),
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


class PropertyFeature(Base):
    """Persisted feature matrix row for a single property.

    Stores the assembled feature vector as JSONB so downstream consumers
    (model training, SHAP API, batch scoring) can read features without
    re-running the full feature engineering pipeline.
    """

    __tablename__ = "property_features"
    __table_args__ = (Index("ix_property_features_computed_at", "computed_at"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(
        Integer,
        ForeignKey("redfin_listings.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    features = Column(JSON, nullable=False)
    feature_hash = Column(String, nullable=False)
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PropertyShapValue(Base):
    """Precomputed SHAP feature attributions for a property prediction.

    Stores per-feature SHAP values (dollar contributions) computed during
    batch scoring.  The API reads from this table instead of computing
    SHAP on-the-fly, falling back to on-demand computation when no
    precomputed values exist for the requested property.
    """

    __tablename__ = "property_shap_values"
    __table_args__ = (
        UniqueConstraint("property_id", "model_version", name="uq_property_shap_prop_version"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(
        Integer,
        ForeignKey("redfin_listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_version = Column(String, nullable=False)
    shap_values = Column(JSON, nullable=False)
    base_value = Column(Float, nullable=True)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())


class PropertyHistoryMetric(Base):
    """Rolling market metrics aggregated by township and month.

    Computes avg days on market, median sale price, and sample counts
    at 1-month, 3-month, and 1-year rolling windows.  Township is
    identified by county_subdivision_geoid from property_geo_lookups.
    """

    __tablename__ = "property_history_metrics"
    __table_args__ = (
        UniqueConstraint("township_geoid", "metric_month", name="uq_phm_township_month"),
        Index("ix_phm_township", "township_geoid"),
        Index("ix_phm_month", "metric_month"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    township_geoid = Column(String(10), nullable=False)
    metric_month = Column(Date, nullable=False)
    avg_days_on_market_1m = Column(Float, nullable=True)
    avg_days_on_market_3m = Column(Float, nullable=True)
    avg_days_on_market_1y = Column(Float, nullable=True)
    median_sale_price_1m = Column(Float, nullable=True)
    median_sale_price_3m = Column(Float, nullable=True)
    median_sale_price_1y = Column(Float, nullable=True)
    sample_count_1m = Column(Integer, nullable=True)
    sample_count_3m = Column(Integer, nullable=True)
    sample_count_1y = Column(Integer, nullable=True)
    built_at = Column(DateTime(timezone=True), server_default=func.now())


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

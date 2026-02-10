"""SQLAlchemy ORM models with PostGIS geometry columns."""

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, Column, DateTime, Float, Index, Integer, String, Text, func
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


class School(Base):
    """School location and rating data."""

    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    school_type = Column(String)
    rating = Column(Float)
    grades = Column(String, nullable=True)
    location = Column(Geometry("POINT", srid=4326))
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


class PropertyDetail(Base):
    """Production property record transformed from staging data."""

    __tablename__ = "property_details"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Location
    address = Column(String, nullable=False, unique=True, index=True)
    city = Column(String, nullable=True)
    state = Column(String(2), nullable=True)
    zip_code = Column(String(10), nullable=True)
    location = Column(Geometry("POINT", srid=4326), nullable=True)

    # Listing
    listing_status = Column(String, nullable=True)
    sold_date = Column(DateTime, nullable=True)
    sold_price = Column(Float, nullable=True)
    listing_price = Column(Float, nullable=True)
    price_per_sqft = Column(Float, nullable=True)

    # Stats
    beds = Column(Integer, nullable=True)
    baths = Column(Float, nullable=True)
    sqft = Column(Integer, nullable=True)
    lot_size_sqft = Column(Float, nullable=True)
    year_built = Column(Integer, nullable=True)
    property_type = Column(String, nullable=True)
    stories = Column(Integer, nullable=True)

    # Description
    description = Column(Text, nullable=True)

    # Interior (extracted from JSON)
    flooring = Column(JSON, nullable=True)
    appliances = Column(JSON, nullable=True)
    heating = Column(String, nullable=True)
    cooling = Column(String, nullable=True)
    fireplace = Column(String, nullable=True)
    basement = Column(String, nullable=True)

    # Exterior (extracted from JSON)
    roof = Column(String, nullable=True)
    siding = Column(String, nullable=True)
    foundation = Column(String, nullable=True)
    parking = Column(String, nullable=True)
    garage_spaces = Column(Integer, nullable=True)
    pool = Column(String, nullable=True)
    fence = Column(String, nullable=True)

    # Financial
    hoa_monthly = Column(Float, nullable=True)
    tax_annual = Column(Float, nullable=True)
    tax_year = Column(Integer, nullable=True)
    assessed_value = Column(Float, nullable=True)

    # Agents
    listing_agent = Column(String, nullable=True)
    listing_brokerage = Column(String, nullable=True)
    buying_agent = Column(String, nullable=True)
    buying_brokerage = Column(String, nullable=True)

    # Climate
    flood_risk = Column(String, nullable=True)
    flood_score = Column(Integer, nullable=True)
    fire_risk = Column(String, nullable=True)
    fire_score = Column(Integer, nullable=True)

    # History
    sale_history = Column(JSON, nullable=True)
    tax_history = Column(JSON, nullable=True)

    # Photos
    photo_s3_paths = Column(JSON, nullable=True)

    # Change detection
    staging_hash = Column(String(64), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (Index("idx_property_details_location", "location", postgresql_using="gist"),)


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


class PropertySchool(Base):
    """Linkage between properties and nearby schools."""

    __tablename__ = "property_schools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(Integer, nullable=False, index=True)
    school_id = Column(Integer, nullable=False, index=True)
    distance_miles = Column(Float, nullable=True)
    drive_minutes = Column(Integer, nullable=True)
    walk_minutes = Column(Integer, nullable=True)

    __table_args__ = (
        Index(
            "uq_property_school",
            "property_id",
            "school_id",
            unique=True,
        ),
    )

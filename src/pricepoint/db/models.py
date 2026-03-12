"""SQLAlchemy ORM models with PostGIS geometry columns."""

from datetime import date, datetime
from typing import Any

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
from sqlalchemy.dialects.postgresql import ARRAY, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Property(Base):
    """Residential property record with location and assessed value."""

    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parcel_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    address: Mapped[str] = mapped_column(String, nullable=False)
    city: Mapped[str | None] = mapped_column(String)
    state: Mapped[str | None] = mapped_column(String(2))
    zip_code: Mapped[str | None] = mapped_column(String(10))
    assessed_value: Mapped[float | None] = mapped_column(Float)
    location = Column(Geometry("POINT", srid=4326))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )


class PoliceIncident(Base):
    """Gold-layer police incident record consolidated from all staging sources."""

    __tablename__ = "police_incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    crime_code: Mapped[str | None] = mapped_column(String, nullable=True)
    crime_group: Mapped[str | None] = mapped_column(String, nullable=True)
    crime_category: Mapped[str | None] = mapped_column(String, nullable=True)
    offense_class: Mapped[str | None] = mapped_column(String, nullable=True)
    crime_description: Mapped[str | None] = mapped_column(String, nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    date_of_incident: Mapped[date | None] = mapped_column(Date, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location = Column(Geometry("POINT", srid=4326))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_police_incidents_location", location, postgresql_using="gist"),
        Index("ix_police_incidents_crime_category", crime_category),
        Index("ix_police_incidents_offense_class", offense_class),
        Index("ix_police_incidents_date_of_incident", date_of_incident),
    )


class StagingCaryPoliceIncident(Base):
    """Raw police incident records from the Town of Cary Open Data Portal.

    All fields stored as-is from the API. Weekly full refresh (truncate + reload).
    """

    __tablename__ = "staging_cary_police_incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_id: Mapped[str | None] = mapped_column(String, index=True)
    incident_number: Mapped[str | None] = mapped_column(String, index=True)
    crime_category: Mapped[str | None] = mapped_column(String, nullable=True)
    crime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    ucr: Mapped[str | None] = mapped_column(String, nullable=True)
    map_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    date_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    from_time: Mapped[str | None] = mapped_column(String, nullable=True)
    date_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    to_time: Mapped[str | None] = mapped_column(String, nullable=True)
    crimeday: Mapped[str | None] = mapped_column(String, nullable=True)
    geocode: Mapped[str | None] = mapped_column(String, nullable=True)
    location_category: Mapped[str | None] = mapped_column(String, nullable=True)
    district: Mapped[str | None] = mapped_column(String, nullable=True)
    beat_number: Mapped[str | None] = mapped_column(String, nullable=True)
    neighborhd_id: Mapped[str | None] = mapped_column(String, nullable=True)
    apartment_complex: Mapped[str | None] = mapped_column(String, nullable=True)
    residential_subdivision: Mapped[str | None] = mapped_column(String, nullable=True)
    subdivisn_id: Mapped[str | None] = mapped_column(String, nullable=True)
    activity_date: Mapped[str | None] = mapped_column(String, nullable=True)
    phxrecordstatus: Mapped[str | None] = mapped_column(String, nullable=True)
    phxcommunity: Mapped[str | None] = mapped_column(String, nullable=True)
    phxstatus: Mapped[str | None] = mapped_column(String, nullable=True)
    record: Mapped[str | None] = mapped_column(String, nullable=True)
    offensecategory: Mapped[str | None] = mapped_column(String, nullable=True)
    violentproperty: Mapped[str | None] = mapped_column(String, nullable=True)
    timeframe: Mapped[str | None] = mapped_column(String, nullable=True)
    domestic: Mapped[str | None] = mapped_column(String, nullable=True)
    total_incidents: Mapped[str | None] = mapped_column(String, nullable=True)
    year: Mapped[str | None] = mapped_column(String, nullable=True)
    older_than_five_years_from_now: Mapped[str | None] = mapped_column(String, nullable=True)
    chrgcnt: Mapped[str | None] = mapped_column(String, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    location = Column(Geometry("POINT", srid=4326), nullable=True)
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class StagingRaleighPoliceIncident(Base):
    """Raw police incident records from the City of Raleigh ArcGIS Feature Service.

    Historical (NIBRS) data loaded via full refresh; daily incremental via
    the Daily_Police_Incidents endpoint.
    """

    __tablename__ = "staging_raleigh_police_incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    objectid: Mapped[str | None] = mapped_column(String, nullable=True)
    global_id: Mapped[str | None] = mapped_column(String, nullable=True)
    case_number: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    crime_category: Mapped[str | None] = mapped_column(String, nullable=True)
    crime_code: Mapped[str | None] = mapped_column(String, nullable=True)
    crime_description: Mapped[str | None] = mapped_column(String, nullable=True)
    crime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    reported_block_address: Mapped[str | None] = mapped_column(String, nullable=True)
    city_of_incident: Mapped[str | None] = mapped_column(String, nullable=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    district: Mapped[str | None] = mapped_column(String, nullable=True)
    reported_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reported_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reported_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reported_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reported_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reported_dayofwk: Mapped[str | None] = mapped_column(String, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    agency: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location = Column(Geometry("POINT", srid=4326), nullable=True)
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class StagingMorrisvillePoliceIncident(Base):
    """Raw police incident records from the Town of Morrisville Open Data Portal.

    All fields stored as-is from the API. Weekly full refresh (truncate + reload).
    """

    __tablename__ = "staging_morrisville_police_incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inci_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    offense: Mapped[str | None] = mapped_column(String, nullable=True)
    date_rept: Mapped[str | None] = mapped_column(String, nullable=True)
    date_occu: Mapped[str | None] = mapped_column(String, nullable=True)
    dow1: Mapped[str | None] = mapped_column(String, nullable=True)
    monthstamp: Mapped[str | None] = mapped_column(String, nullable=True)
    yearstamp: Mapped[str | None] = mapped_column(String, nullable=True)
    street: Mapped[str | None] = mapped_column(String, nullable=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str | None] = mapped_column(String, nullable=True)
    zip: Mapped[str | None] = mapped_column(String, nullable=True)
    neighborhd: Mapped[str | None] = mapped_column(String, nullable=True)
    subdivisn: Mapped[str | None] = mapped_column(String, nullable=True)
    tract: Mapped[str | None] = mapped_column(String, nullable=True)
    zone: Mapped[str | None] = mapped_column(String, nullable=True)
    district: Mapped[str | None] = mapped_column(String, nullable=True)
    asst_offcr: Mapped[str | None] = mapped_column(String, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    location = Column(Geometry("POINT", srid=4326), nullable=True)
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class RedfinSchool(Base):
    """Raw school data extracted from Redfin listings (bronze layer)."""

    __tablename__ = "redfin_schools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    school_type: Mapped[str | None] = mapped_column(String)
    rating: Mapped[float | None] = mapped_column(Float)
    grades: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Block(Base):
    """US Census TIGER/Line census block boundaries (TABBLOCK20)."""

    __tablename__ = "blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    statefp20: Mapped[str | None] = mapped_column(String(2))
    countyfp20: Mapped[str | None] = mapped_column(String(3))
    tractce20: Mapped[str | None] = mapped_column(String(6))
    blockce20: Mapped[str | None] = mapped_column(String(4))
    geoid20: Mapped[str | None] = mapped_column(String(15), index=True)
    name20: Mapped[str | None] = mapped_column(String)
    aland20: Mapped[int | None] = mapped_column(BigInteger)
    awater20: Mapped[int | None] = mapped_column(BigInteger)
    intptlat20: Mapped[str | None] = mapped_column(String(11))
    intptlon20: Mapped[str | None] = mapped_column(String(12))
    funcstat20: Mapped[str | None] = mapped_column(String(1))
    mtfcc20: Mapped[str | None] = mapped_column(String(5))
    ur20: Mapped[str | None] = mapped_column(String(1))
    uace20: Mapped[str | None] = mapped_column(String(5))
    uatype20: Mapped[str | None] = mapped_column(String(1))
    housing20: Mapped[int | None] = mapped_column(Integer)
    pop20: Mapped[int | None] = mapped_column(Integer)
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class BlockGroup(Base):
    """US Census TIGER/Line block group boundaries (BG)."""

    __tablename__ = "block_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    statefp: Mapped[str | None] = mapped_column(String(2))
    countyfp: Mapped[str | None] = mapped_column(String(3))
    tractce: Mapped[str | None] = mapped_column(String(6))
    blkgrpce: Mapped[str | None] = mapped_column(String(1))
    geoid: Mapped[str | None] = mapped_column(String(12), index=True)
    namelsad: Mapped[str | None] = mapped_column(String(100))
    aland: Mapped[int | None] = mapped_column(BigInteger)
    awater: Mapped[int | None] = mapped_column(BigInteger)
    intptlat: Mapped[str | None] = mapped_column(String(11))
    intptlon: Mapped[str | None] = mapped_column(String(12))
    funcstat: Mapped[str | None] = mapped_column(String(1))
    mtfcc: Mapped[str | None] = mapped_column(String(5))
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Tract(Base):
    """US Census TIGER/Line census tract boundaries (TRACT)."""

    __tablename__ = "tracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    statefp: Mapped[str | None] = mapped_column(String(2))
    countyfp: Mapped[str | None] = mapped_column(String(3))
    tractce: Mapped[str | None] = mapped_column(String(6))
    geoid: Mapped[str | None] = mapped_column(String(11), index=True)
    name: Mapped[str | None] = mapped_column(String)
    namelsad: Mapped[str | None] = mapped_column(String(100))
    aland: Mapped[int | None] = mapped_column(BigInteger)
    awater: Mapped[int | None] = mapped_column(BigInteger)
    intptlat: Mapped[str | None] = mapped_column(String(11))
    intptlon: Mapped[str | None] = mapped_column(String(12))
    funcstat: Mapped[str | None] = mapped_column(String(1))
    mtfcc: Mapped[str | None] = mapped_column(String(5))
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SchoolDistrict(Base):
    """US Census TIGER/Line school district boundaries (ELSD/SCSD/UNSD combined)."""

    __tablename__ = "school_districts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    district_type: Mapped[str | None] = mapped_column(String(10), index=True)
    statefp: Mapped[str | None] = mapped_column(String(2))
    geoid: Mapped[str | None] = mapped_column(String(7), index=True)
    name: Mapped[str | None] = mapped_column(String)
    lsad: Mapped[str | None] = mapped_column(String(2))
    lograde: Mapped[str | None] = mapped_column(String(2))
    higrade: Mapped[str | None] = mapped_column(String(2))
    aland: Mapped[int | None] = mapped_column(BigInteger)
    awater: Mapped[int | None] = mapped_column(BigInteger)
    intptlat: Mapped[str | None] = mapped_column(String(11))
    intptlon: Mapped[str | None] = mapped_column(String(12))
    funcstat: Mapped[str | None] = mapped_column(String(1))
    mtfcc: Mapped[str | None] = mapped_column(String(5))
    sdtyp: Mapped[str | None] = mapped_column(String(1))
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class County(Base):
    """US Census TIGER/Line county boundaries (COUNTY)."""

    __tablename__ = "counties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    statefp: Mapped[str | None] = mapped_column(String(2))
    countyfp: Mapped[str | None] = mapped_column(String(3))
    countyns: Mapped[str | None] = mapped_column(String(8))
    geoid: Mapped[str | None] = mapped_column(String(5), index=True)
    name: Mapped[str | None] = mapped_column(String)
    namelsad: Mapped[str | None] = mapped_column(String(100))
    lsad: Mapped[str | None] = mapped_column(String(2))
    classfp: Mapped[str | None] = mapped_column(String(2))
    aland: Mapped[int | None] = mapped_column(BigInteger)
    awater: Mapped[int | None] = mapped_column(BigInteger)
    intptlat: Mapped[str | None] = mapped_column(String(11))
    intptlon: Mapped[str | None] = mapped_column(String(12))
    funcstat: Mapped[str | None] = mapped_column(String(1))
    mtfcc: Mapped[str | None] = mapped_column(String(5))
    csafp: Mapped[str | None] = mapped_column(String(3))
    cbsafp: Mapped[str | None] = mapped_column(String(5))
    metdivfp: Mapped[str | None] = mapped_column(String(5))
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Township(Base):
    """US Census TIGER/Line county subdivision boundaries (COUSUB)."""

    __tablename__ = "townships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    statefp: Mapped[str | None] = mapped_column(String(2))
    countyfp: Mapped[str | None] = mapped_column(String(3))
    cousubfp: Mapped[str | None] = mapped_column(String(5))
    cousubns: Mapped[str | None] = mapped_column(String(8))
    geoid: Mapped[str | None] = mapped_column(String(10), index=True)
    name: Mapped[str | None] = mapped_column(String)
    namelsad: Mapped[str | None] = mapped_column(String(100))
    lsad: Mapped[str | None] = mapped_column(String(2))
    classfp: Mapped[str | None] = mapped_column(String(2))
    aland: Mapped[int | None] = mapped_column(BigInteger)
    awater: Mapped[int | None] = mapped_column(BigInteger)
    intptlat: Mapped[str | None] = mapped_column(String(11))
    intptlon: Mapped[str | None] = mapped_column(String(12))
    funcstat: Mapped[str | None] = mapped_column(String(1))
    mtfcc: Mapped[str | None] = mapped_column(String(5))
    cnectafp: Mapped[str | None] = mapped_column(String(3))
    nectafp: Mapped[str | None] = mapped_column(String(5))
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Road(Base):
    """TIGER/Line primary and secondary road centerlines (PRISECROADS).

    Combines S1100 (primary) and S1200 (secondary) MTFCC classes from
    state-level PRISECROADS shapefiles into a single table.
    """

    __tablename__ = "roads"
    __table_args__ = (Index("ix_roads_geom", "geom", postgresql_using="gist"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    linearid: Mapped[str | None] = mapped_column(String(22), unique=True, index=True)
    fullname: Mapped[str | None] = mapped_column(String(100))
    rttyp: Mapped[str | None] = mapped_column(String(1))
    mtfcc: Mapped[str | None] = mapped_column(String(5))
    geom = Column(Geometry("MULTILINESTRING", srid=4326))
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class StagingWakeCountyPropertyData(Base):
    """Wake County property assessment data staging table.

    Contains all 94 columns from the county's daily extract in fixed-width format.
    Truncate-and-reload pattern (no historical tracking). Raw coded values only.
    """

    __tablename__ = "staging_wake_county_property_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Ownership and mailing address
    owner_1: Mapped[str | None] = mapped_column(String(35), nullable=True)
    owner_2: Mapped[str | None] = mapped_column(String(35), nullable=True)
    address_1: Mapped[str | None] = mapped_column(String(35), nullable=True)
    address_2: Mapped[str | None] = mapped_column(String(35), nullable=True)
    address_3: Mapped[str | None] = mapped_column(String(35), nullable=True)

    # Property identification
    reid: Mapped[str | None] = mapped_column(String(7), nullable=True, index=True)
    card_num: Mapped[str | None] = mapped_column(String(3), nullable=True)
    num_cards: Mapped[str | None] = mapped_column(String(3), nullable=True)

    # Physical address components
    street_num: Mapped[str | None] = mapped_column(String(6), nullable=True)
    street_prefix: Mapped[str | None] = mapped_column(String(2), nullable=True)
    street_name: Mapped[str | None] = mapped_column(String(25), nullable=True)
    street_type: Mapped[str | None] = mapped_column(String(4), nullable=True)
    street_suffix: Mapped[str | None] = mapped_column(String(2), nullable=True)
    street_misc: Mapped[str | None] = mapped_column(String(2), nullable=True)

    # Location and jurisdiction
    planning_jurisdiction: Mapped[str | None] = mapped_column(String(2), nullable=True)
    township: Mapped[str | None] = mapped_column(String(2), nullable=True)
    fire_district: Mapped[str | None] = mapped_column(String(2), nullable=True)
    physical_city: Mapped[str | None] = mapped_column(String(50), nullable=True)
    physical_zip_code: Mapped[str | None] = mapped_column(String(5), nullable=True)
    city: Mapped[str | None] = mapped_column(String(3), nullable=True)

    # Parcel details
    parcel_identification: Mapped[str | None] = mapped_column(String(19), nullable=True)
    billing_class: Mapped[str | None] = mapped_column(String(1), nullable=True)
    land_classification: Mapped[str | None] = mapped_column(String(1), nullable=True)
    zoning: Mapped[str | None] = mapped_column(String(5), nullable=True)
    deeded_acreage: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Special districts
    special_district_1: Mapped[str | None] = mapped_column(String(3), nullable=True)
    special_district_2: Mapped[str | None] = mapped_column(String(3), nullable=True)
    special_district_3: Mapped[str | None] = mapped_column(String(3), nullable=True)

    # Land sales
    land_sale_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    land_sale_date: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Total sales
    total_sale_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_sale_date: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Assessed values
    assessed_building_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    assessed_land_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Deed information
    deed_book: Mapped[str | None] = mapped_column(String(6), nullable=True)
    deed_page: Mapped[str | None] = mapped_column(String(6), nullable=True)
    deed_date: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Property description and indexing
    property_description: Mapped[str | None] = mapped_column(String(40), nullable=True)
    vcs: Mapped[str | None] = mapped_column(String(7), nullable=True)
    property_index: Mapped[str | None] = mapped_column(String(40), nullable=True)
    type_use: Mapped[str | None] = mapped_column(String(3), nullable=True)

    # Building characteristics
    year_built: Mapped[int | None] = mapped_column(Integer, nullable=True)
    num_rooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heated_area: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Utilities and site features
    utilities: Mapped[str | None] = mapped_column(String(3), nullable=True)
    street_pavement: Mapped[str | None] = mapped_column(String(1), nullable=True)
    topography: Mapped[str | None] = mapped_column(String(1), nullable=True)

    # Building years and modifications
    year_of_addition: Mapped[int | None] = mapped_column(Integer, nullable=True)
    effective_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remodeled_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unused: Mapped[str | None] = mapped_column(String(2), nullable=True)
    special_write_in: Mapped[str | None] = mapped_column(String(8), nullable=True)

    # Building structure
    story_height: Mapped[str | None] = mapped_column(String(1), nullable=True)
    design_style: Mapped[str | None] = mapped_column(String(1), nullable=True)
    foundation_basement: Mapped[str | None] = mapped_column(String(1), nullable=True)
    foundation_basement_pct: Mapped[str | None] = mapped_column(String(2), nullable=True)
    exterior_wall: Mapped[str | None] = mapped_column(String(1), nullable=True)
    common_wall: Mapped[str | None] = mapped_column(String(1), nullable=True)
    roof: Mapped[str | None] = mapped_column(String(1), nullable=True)
    roof_floor_system: Mapped[str | None] = mapped_column(String(1), nullable=True)

    # Interior finishes
    floor_finish: Mapped[str | None] = mapped_column(String(1), nullable=True)
    interior_finish: Mapped[str | None] = mapped_column(String(1), nullable=True)
    interior_finish_1: Mapped[str | None] = mapped_column(String(1), nullable=True)
    interior_finish_1_pct: Mapped[str | None] = mapped_column(String(2), nullable=True)
    interior_finish_2: Mapped[str | None] = mapped_column(String(1), nullable=True)
    interior_finish_2_pct: Mapped[str | None] = mapped_column(String(2), nullable=True)

    # HVAC systems
    heat: Mapped[str | None] = mapped_column(String(1), nullable=True)
    heat_pct: Mapped[str | None] = mapped_column(String(2), nullable=True)
    air: Mapped[str | None] = mapped_column(String(1), nullable=True)
    air_pct: Mapped[str | None] = mapped_column(String(2), nullable=True)

    # Bathrooms
    bath: Mapped[str | None] = mapped_column(String(1), nullable=True)
    bath_fixtures: Mapped[str | None] = mapped_column(String(3), nullable=True)

    # Built-in features
    builtin_1_description: Mapped[str | None] = mapped_column(String(15), nullable=True)
    builtin_2_description: Mapped[str | None] = mapped_column(String(15), nullable=True)
    builtin_3_description: Mapped[str | None] = mapped_column(String(15), nullable=True)
    builtin_4_description: Mapped[str | None] = mapped_column(String(15), nullable=True)
    builtin_5_description: Mapped[str | None] = mapped_column(String(15), nullable=True)

    # Quality and condition
    grade: Mapped[str | None] = mapped_column(String(5), nullable=True)
    assessed_grade_difference: Mapped[str | None] = mapped_column(String(3), nullable=True)
    accrued_assessed_condition_pct: Mapped[str | None] = mapped_column(String(3), nullable=True)

    # Deferred values
    land_deferred_code: Mapped[str | None] = mapped_column(String(1), nullable=True)
    land_deferred_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    historic_deferred_code: Mapped[str | None] = mapped_column(String(1), nullable=True)
    historic_deferred_amount: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Additional flags
    recycled_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disqualifying_qualifying_flags: Mapped[str | None] = mapped_column(String(1), nullable=True)
    land_disqualify_qualify_flag: Mapped[str | None] = mapped_column(String(1), nullable=True)

    # Metadata
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class StagingRedfinListing(Base):
    """Redfin listing data parsed from SingleFile HTML snapshots.

    Upsert pattern keyed on address. Photos stored in S3, HTML archived after parsing.
    """

    __tablename__ = "staging_redfin_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Address
    address: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str | None] = mapped_column(String, nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String, nullable=True)

    # Status
    listing_status: Mapped[str | None] = mapped_column(String, nullable=True)
    sold_date: Mapped[str | None] = mapped_column(String, nullable=True)
    sold_price: Mapped[str | None] = mapped_column(String, nullable=True)

    # Key stats
    listing_price: Mapped[str | None] = mapped_column(String, nullable=True)
    beds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    baths: Mapped[float | None] = mapped_column(Float, nullable=True)
    sqft: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Description
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Key details
    year_built: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lot_size: Mapped[str | None] = mapped_column(String, nullable=True)
    price_per_sqft: Mapped[str | None] = mapped_column(String, nullable=True)

    # Agent info
    listing_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    listing_brokerage: Mapped[str | None] = mapped_column(String, nullable=True)
    buying_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    buying_brokerage: Mapped[str | None] = mapped_column(String, nullable=True)

    # Redfin estimate
    redfin_estimate: Mapped[str | None] = mapped_column(String, nullable=True)

    # JSON fields
    sale_history: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    tax_history: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    property_details: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    schools: Mapped[Any | None] = mapped_column(JSON, nullable=True)

    # Climate risk
    climate_flood_factor: Mapped[str | None] = mapped_column(String, nullable=True)
    climate_fire_factor: Mapped[str | None] = mapped_column(String, nullable=True)

    # Photos and source
    photo_s3_paths: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    source_file: Mapped[str | None] = mapped_column(String, nullable=True)
    redfin_url: Mapped[str | None] = mapped_column(String, nullable=True)

    # Metadata
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    extracted_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_processed: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_staging_unprocessed",
            "id",
            postgresql_where=text("is_processed = false"),
        ),
    )


class RedfinListing(Base):
    """Production property record transformed from staging Redfin data (silver layer)."""

    __tablename__ = "redfin_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Location
    street_address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    location = Column(Geometry("POINT", srid=4326), nullable=True)

    # Listing
    listing_status: Mapped[str | None] = mapped_column(String, nullable=True)
    sold_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sold_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    listing_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Climate risk
    flood_factor: Mapped[str | None] = mapped_column(String, nullable=True)
    fire_factor: Mapped[str | None] = mapped_column(String, nullable=True)
    flood_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fire_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Parking
    has_garage: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    num_garage_spaces: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parking_type: Mapped[str | None] = mapped_column(String, nullable=True)
    garage_entry: Mapped[str | None] = mapped_column(String, nullable=True)
    driveway_surface: Mapped[str | None] = mapped_column(String, nullable=True)
    has_workshop: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_circular_driveway: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_ev_charging: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    num_parking_spaces: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Fireplace
    has_fireplace: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_outdoor_fireplace: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_primary_fireplace: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_architectural_fireplace: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    fireplace_fuel_source: Mapped[str | None] = mapped_column(String, nullable=True)
    num_fireplaces: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Appliances / energy
    water_heater_energy_source: Mapped[str | None] = mapped_column(String, nullable=True)
    cooktop_energy_source: Mapped[str | None] = mapped_column(String, nullable=True)
    oven_energy_source: Mapped[str | None] = mapped_column(String, nullable=True)
    has_drink_fridge: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_stainless_appliances: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    appliances_included_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Windows
    has_efficient_windows: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_skylights: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_bay_window: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )

    # Laundry
    laundry_location: Mapped[str | None] = mapped_column(String, nullable=True)
    has_laundry_room: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_utility_sink: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )

    # Interior features
    countertop_material: Mapped[str | None] = mapped_column(String, nullable=True)
    is_primary_downstairs: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_guest_suite: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_butler_pantry: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_walkin_closets: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_tall_ceilings: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_luxury_ceilings: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_sauna: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_bar: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_second_primary: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_room_over_garage: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_open_floorplan: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )

    # Flooring
    is_carpet_free: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_premium_stone: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_hardwood: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_crawl_space: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )

    # Exterior / structure
    facade_type: Mapped[str | None] = mapped_column(String, nullable=True)
    building_area: Mapped[float | None] = mapped_column(Float, nullable=True)
    above_grade_finished_area: Mapped[float | None] = mapped_column(Float, nullable=True)
    below_grade_finished_area: Mapped[float | None] = mapped_column(Float, nullable=True)
    num_stories: Mapped[float | None] = mapped_column(Float, nullable=True)
    lot_size: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_waterfront: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    buyer_financing: Mapped[str | None] = mapped_column(String, nullable=True)

    # Utilities
    is_septic: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    is_well_water: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    no_heating: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    no_cooling: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )

    # HOA / community
    has_hoa: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    association_fee: Mapped[float | None] = mapped_column(Float, nullable=True)
    hoa_name: Mapped[str | None] = mapped_column(String, nullable=True)

    # Porch / outdoor
    has_enclosed_porch: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_front_porch: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_fenced_yard: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_outdoor_kitchen: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_sport_court: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_private_pool: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_community_pool: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_clubhouse: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_exterior_storage: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    has_garden: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )

    # Core stats
    year_built: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year_renovated: Mapped[int | None] = mapped_column(Integer, nullable=True)
    num_beds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    num_baths: Mapped[float | None] = mapped_column(Float, nullable=True)
    sqft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_per_sqft: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Agents
    listing_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    listing_brokerage: Mapped[str | None] = mapped_column(String, nullable=True)
    buying_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    buying_brokerage: Mapped[str | None] = mapped_column(String, nullable=True)

    # Identifiers
    apn: Mapped[str | None] = mapped_column(String, nullable=True)
    contract_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Raw data for UI
    property_details: Mapped[Any | None] = mapped_column(JSON, nullable=True)

    # Photos and source
    property_photos: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    source_file: Mapped[str | None] = mapped_column(String, nullable=True)
    redfin_url: Mapped[str | None] = mapped_column(String, nullable=True)

    # Change detection
    staging_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Metadata
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    schools_built_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    features_built_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    event: Mapped[str | None] = mapped_column(String, nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str | None] = mapped_column(String, nullable=True)


class TaxHistoryRecord(Base):
    """Individual tax assessment linked to a Redfin listing."""

    __tablename__ = "tax_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    property_tax: Mapped[float | None] = mapped_column(Float, nullable=True)
    assessment_value_land: Mapped[float | None] = mapped_column(Float, nullable=True)
    assessment_value_additions: Mapped[float | None] = mapped_column(Float, nullable=True)
    assessment_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str | None] = mapped_column(String, nullable=True)


class PropertyValuation(Base):
    """Property valuation from various sources (Redfin, ML model, etc.)."""

    __tablename__ = "property_valuations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("idx_property_valuations_property_source", "property_id", "source"),)


class RedfinPropertySchool(Base):
    """Raw linkage between properties and Redfin-extracted schools (bronze layer)."""

    __tablename__ = "redfin_property_schools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    redfin_school_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nces_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    street: Mapped[str | None] = mapped_column(String, nullable=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    school_type: Mapped[str | None] = mapped_column(String, nullable=True)
    school_level: Mapped[str | None] = mapped_column(String, nullable=True)
    grades: Mapped[str | None] = mapped_column(String, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    location = Column(Geometry("POINT", srid=4326), nullable=True)
    enrollment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    teachers: Mapped[float | None] = mapped_column(Float, nullable=True)
    student_teacher_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    free_lunch_eligible: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reduced_lunch_eligible: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_frl_eligible: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pct_frl_eligible: Mapped[float | None] = mapped_column(Float, nullable=True)
    district_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("idx_schools_location", "location", postgresql_using="gist"),)


class PropertySchool(Base):
    """Linkage between properties and gold schools."""

    __tablename__ = "property_schools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    school_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    assigned: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    distance_miles: Mapped[float | None] = mapped_column(Float, nullable=True)
    drive_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    walk_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(
        Integer,
        ForeignKey("redfin_listings.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    census_tract_geoid: Mapped[str | None] = mapped_column(String(11), nullable=True)
    census_block_group_geoid: Mapped[str | None] = mapped_column(String(12), nullable=True)
    county_subdivision_geoid: Mapped[str | None] = mapped_column(String(10), nullable=True)
    county_geoid: Mapped[str | None] = mapped_column(String(5), nullable=True)
    subdivision_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    subdivision_name: Mapped[str | None] = mapped_column(String, nullable=True)
    in_noise_zone: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    noise_max_db: Mapped[int | None] = mapped_column(Integer, nullable=True)
    noise_source_layers: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    in_risk_zone: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    risk_max_severity: Mapped[str | None] = mapped_column(String, nullable=True)
    risk_types: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    school_district_geoid: Mapped[str | None] = mapped_column(String(7), nullable=True)
    dist_nearest_school_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    dist_nearest_elementary_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    dist_nearest_middle_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    dist_nearest_high_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    dist_nearest_park_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    dist_nearest_greenway_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    dist_nearest_hospital_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_school_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_school_drive: Mapped[float | None] = mapped_column(Float, nullable=True)
    in_critical_risk_zone: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    built_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class NcesSchool(Base):
    """NCES school directory reference data."""

    __tablename__ = "nces_schools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nces_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    street: Mapped[str | None] = mapped_column(String, nullable=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    school_type: Mapped[str | None] = mapped_column(String, nullable=True)
    school_level: Mapped[str | None] = mapped_column(String, nullable=True)
    grades_low: Mapped[str | None] = mapped_column(String, nullable=True)
    grades_high: Mapped[str | None] = mapped_column(String, nullable=True)
    location = Column(Geometry("POINT", srid=4326), nullable=True)
    extras: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class WakeSubdivision(Base):
    """Wake County subdivision boundary from ArcGIS MapServer."""

    __tablename__ = "wake_subdivisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    objectid: Mapped[int | None] = mapped_column(Integer, index=True)
    name: Mapped[str | None] = mapped_column(String(40))
    snumber: Mapped[str | None] = mapped_column(String(10), index=True)
    access_rd: Mapped[str | None] = mapped_column(String(30))
    jurisdiction: Mapped[str | None] = mapped_column(String(25))
    status: Mapped[str | None] = mapped_column(String(20))
    acres: Mapped[float | None] = mapped_column(Float)
    lots: Mapped[int | None] = mapped_column(Integer)
    density: Mapped[float | None] = mapped_column(Float)
    mapclass: Mapped[int | None] = mapped_column(Integer)
    iscluster: Mapped[str | None] = mapped_column(String(5))
    approvdate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    appldate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_edited_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Subdivision(Base):
    """Gold subdivision boundary — all counties, keyed by (county_fips, source_id)."""

    __tablename__ = "subdivisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    county_fips: Mapped[str] = mapped_column(String(5), nullable=False)
    source_id: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    acres: Mapped[float | None] = mapped_column(Float, nullable=True)
    lots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    density: Mapped[float | None] = mapped_column(Float, nullable=True)
    geom = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    built_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    objectid: Mapped[int | None] = mapped_column(Integer, index=True)
    hifld_id: Mapped[str | None] = mapped_column(String, index=True)
    name: Mapped[str | None] = mapped_column(String, index=True)
    address: Mapped[str | None] = mapped_column(String)
    city: Mapped[str | None] = mapped_column(String)
    state: Mapped[str | None] = mapped_column(String)
    zip_code: Mapped[str | None] = mapped_column(String)
    telephone: Mapped[str | None] = mapped_column(String)
    hospital_type: Mapped[str | None] = mapped_column(String)
    status: Mapped[str | None] = mapped_column(String)
    population: Mapped[int | None] = mapped_column(Integer)
    county: Mapped[str | None] = mapped_column(String)
    countyfips: Mapped[str | None] = mapped_column(String)
    owner: Mapped[str | None] = mapped_column(String)
    beds: Mapped[int | None] = mapped_column(Integer)
    trauma: Mapped[str | None] = mapped_column(String)
    helipad: Mapped[str | None] = mapped_column(String)
    website: Mapped[str | None] = mapped_column(String)
    naics_code: Mapped[str | None] = mapped_column(String)
    naics_desc: Mapped[str | None] = mapped_column(String)
    ttl_staff: Mapped[int | None] = mapped_column(Integer)
    geom = Column(Geometry("POINT", srid=4326))
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Greenspace(Base):
    """Protected area / greenspace from PAD-US (Fee layer)."""

    __tablename__ = "greenspaces"
    __table_args__ = (Index("ix_greenspaces_geom", "geom", postgresql_using="gist"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String, index=True)
    gis_acres: Mapped[float | None] = mapped_column(Float)
    manager_type: Mapped[str | None] = mapped_column(String(10))
    manager_name: Mapped[str | None] = mapped_column(String)
    designation_type: Mapped[str | None] = mapped_column(String(20))
    pub_access: Mapped[str | None] = mapped_column(String(2))
    gap_sts: Mapped[int | None] = mapped_column(Integer)
    state_name: Mapped[str | None] = mapped_column(String)
    category: Mapped[str | None] = mapped_column(String)
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Trail(Base):
    """Trail from USGS National Digital Trails dataset."""

    __tablename__ = "trails"
    __table_args__ = (Index("ix_trails_geom", "geom", postgresql_using="gist"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    permanentidentifier: Mapped[str] = mapped_column(
        String, unique=True, nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(String, index=True)
    trail_type: Mapped[str | None] = mapped_column(String)
    length_miles: Mapped[float | None] = mapped_column(Float)
    maintainer: Mapped[str | None] = mapped_column(String)
    national_designation: Mapped[str | None] = mapped_column(String)
    hiker_pedestrian: Mapped[str | None] = mapped_column(String)
    bicycle: Mapped[str | None] = mapped_column(String)
    pack_saddle: Mapped[str | None] = mapped_column(String)
    atv: Mapped[str | None] = mapped_column(String)
    motorcycle: Mapped[str | None] = mapped_column(String)
    ohv_over_50_inches: Mapped[str | None] = mapped_column(String)
    snowshoe: Mapped[str | None] = mapped_column(String)
    cross_country_ski: Mapped[str | None] = mapped_column(String)
    dogsled: Mapped[str | None] = mapped_column(String)
    snowmobile: Mapped[str | None] = mapped_column(String)
    non_motorized_watercraft: Mapped[str | None] = mapped_column(String)
    motorized_watercraft: Mapped[str | None] = mapped_column(String)
    geom = Column(Geometry("MULTILINESTRING", srid=4326))
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CellTower(Base):
    """Cell tower location from HIFLD ArcGIS FeatureServer."""

    __tablename__ = "cell_towers"
    __table_args__ = (Index("ix_cell_towers_geom", "geom", postgresql_using="gist"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    objectid: Mapped[int | None] = mapped_column(Integer, index=True)
    licensee: Mapped[str | None] = mapped_column(String)
    callsign: Mapped[str | None] = mapped_column(String)
    city: Mapped[str | None] = mapped_column(String)
    state: Mapped[str | None] = mapped_column(String)
    county: Mapped[str | None] = mapped_column(String)
    structure_type: Mapped[str | None] = mapped_column(String)
    height_ft: Mapped[float | None] = mapped_column(Float)
    geom = Column(Geometry("POINT", srid=4326))
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TransmissionLine(Base):
    """Electric power transmission line from HIFLD ArcGIS FeatureServer."""

    __tablename__ = "transmission_lines"
    __table_args__ = (Index("ix_transmission_lines_geom", "geom", postgresql_using="gist"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    objectid: Mapped[int | None] = mapped_column(Integer, index=True)
    line_type: Mapped[str | None] = mapped_column(String)
    status: Mapped[str | None] = mapped_column(String)
    owner: Mapped[str | None] = mapped_column(String)
    voltage: Mapped[float | None] = mapped_column(Float)
    volt_class: Mapped[str | None] = mapped_column(String)
    sub_1: Mapped[str | None] = mapped_column(String)
    sub_2: Mapped[str | None] = mapped_column(String)
    geom = Column(Geometry("MULTILINESTRING", srid=4326))
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PowerPlant(Base):
    """Power plant location from HIFLD ArcGIS FeatureServer."""

    __tablename__ = "power_plants"
    __table_args__ = (Index("ix_power_plants_geom", "geom", postgresql_using="gist"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    objectid: Mapped[int | None] = mapped_column(Integer, index=True)
    plant_code: Mapped[int | None] = mapped_column(Integer)
    name: Mapped[str | None] = mapped_column(String, index=True)
    utility_name: Mapped[str | None] = mapped_column(String)
    state: Mapped[str | None] = mapped_column(String)
    county: Mapped[str | None] = mapped_column(String)
    primary_source: Mapped[str | None] = mapped_column(String)
    install_mw: Mapped[float | None] = mapped_column(Float)
    total_mw: Mapped[float | None] = mapped_column(Float)
    geom = Column(Geometry("POINT", srid=4326))
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class NatGasPipeline(Base):
    """Natural gas pipeline from HIFLD ArcGIS FeatureServer."""

    __tablename__ = "nat_gas_pipelines"
    __table_args__ = (Index("ix_nat_gas_pipelines_geom", "geom", postgresql_using="gist"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    objectid: Mapped[int | None] = mapped_column(Integer, index=True)
    pipe_type: Mapped[str | None] = mapped_column(String)
    operator: Mapped[str | None] = mapped_column(String)
    status: Mapped[str | None] = mapped_column(String)
    geom = Column(Geometry("MULTILINESTRING", srid=4326))
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PetroleumPipeline(Base):
    """Petroleum products pipeline from HIFLD ArcGIS FeatureServer."""

    __tablename__ = "petroleum_pipelines"
    __table_args__ = (Index("ix_petroleum_pipelines_geom", "geom", postgresql_using="gist"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    objectid: Mapped[int | None] = mapped_column(Integer, index=True)
    operator: Mapped[str | None] = mapped_column(String)
    pipe_name: Mapped[str | None] = mapped_column(String)
    geom = Column(Geometry("MULTILINESTRING", srid=4326))
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class RiskBoundary(Base):
    """Pre-computed risk buffer polygon around infrastructure."""

    __tablename__ = "risk_boundaries"
    __table_args__ = (
        Index("ix_risk_boundaries_geom", "geom", postgresql_using="gist"),
        Index("ix_risk_boundaries_infra", "infrastructure_type", "infrastructure_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    infrastructure_type: Mapped[str] = mapped_column(String, nullable=False)
    infrastructure_id: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    geom = Column(Geometry("GEOMETRY", srid=4326))
    built_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Railroad(Base):
    """HIFLD North American Rail Network lines (entire US)."""

    __tablename__ = "railroads"
    __table_args__ = (Index("ix_railroads_geom", "geom", postgresql_using="gist"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fraarcid: Mapped[int | None] = mapped_column(Integer, unique=True, index=True)
    rrowner1: Mapped[str | None] = mapped_column(String)
    rrowner2: Mapped[str | None] = mapped_column(String)
    rrowner3: Mapped[str | None] = mapped_column(String)
    stateab: Mapped[str | None] = mapped_column(String(2))
    cntyfips: Mapped[str | None] = mapped_column(String(5))
    subdivision: Mapped[str | None] = mapped_column(String)
    branch: Mapped[str | None] = mapped_column(String)
    passngr: Mapped[str | None] = mapped_column(String)
    tracks: Mapped[int | None] = mapped_column(Integer)
    miles: Mapped[float | None] = mapped_column(Float)
    net: Mapped[str | None] = mapped_column(String)
    geom = Column(Geometry("MULTILINESTRING", srid=4326))
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Airport(Base):
    """Airport location from OurAirports."""

    __tablename__ = "airports"
    __table_args__ = (
        Index("ix_airports_geom", "geom", postgresql_using="gist"),
        UniqueConstraint("ident", name="uq_airports_ident"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ident: Mapped[str] = mapped_column(String, nullable=False, index=True)
    airport_type: Mapped[str | None] = mapped_column(String)
    name: Mapped[str | None] = mapped_column(String, index=True)
    elevation_ft: Mapped[int | None] = mapped_column(Integer)
    iso_region: Mapped[str | None] = mapped_column(String)
    municipality: Mapped[str | None] = mapped_column(String)
    scheduled_service: Mapped[bool | None] = mapped_column(Boolean)
    iata_code: Mapped[str | None] = mapped_column(String)
    home_link: Mapped[str | None] = mapped_column(String)
    wikipedia_link: Mapped[str | None] = mapped_column(String)
    geom = Column(Geometry("POINT", srid=4326))
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TransportationNoise(Base):
    """Transportation noise polygon from BTS National Noise Map (aviation+road+rail)."""

    __tablename__ = "noises"
    __table_args__ = (
        Index("ix_noises_geom", "geom", postgresql_using="gist"),
        Index("ix_noises_noise_min_db", "noise_min_db"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    noise_min_db: Mapped[int] = mapped_column(Integer, nullable=False)
    noise_max_db: Mapped[int | None] = mapped_column(Integer, nullable=True)
    noise_band: Mapped[str] = mapped_column(String, nullable=False)
    source_layer: Mapped[str] = mapped_column(String, nullable=False)
    area_sq_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class StagingTransportationNoise(Base):
    """Staging table for raw BTS noise polygons (pre-smoothing).

    Holds jagged per-batch polygons before PostGIS clustering, merging,
    and Chaikin smoothing promote them to the production ``noises`` table.
    """

    __tablename__ = "staging_noises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    noise_min_db: Mapped[int] = mapped_column(Integer, nullable=False)
    noise_max_db: Mapped[int | None] = mapped_column(Integer, nullable=True)
    noise_band: Mapped[str] = mapped_column(String, nullable=False)
    source_layer: Mapped[str] = mapped_column(String, nullable=False)
    area_sq_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class StagingPlace(Base):
    """Staging table for Overture Maps places (bronze).

    Raw data loaded from S3 GeoParquet. Truncated on each run.
    No unique constraints or spatial indexes — optimized for fast bulk writes.
    """

    __tablename__ = "staging_places"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str | None] = mapped_column(String)
    category: Mapped[str | None] = mapped_column(String)
    alternate_categories: Mapped[Any | None] = mapped_column(JSON)
    confidence: Mapped[float | None] = mapped_column(Float)
    operating_status: Mapped[str | None] = mapped_column(String)
    address: Mapped[str | None] = mapped_column(String)
    city: Mapped[str | None] = mapped_column(String)
    state: Mapped[str | None] = mapped_column(String)
    postcode: Mapped[str | None] = mapped_column(String)
    country: Mapped[str | None] = mapped_column(String)
    brand_name: Mapped[str | None] = mapped_column(String)
    brand_wikidata: Mapped[str | None] = mapped_column(String)
    website: Mapped[str | None] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String)
    social: Mapped[str | None] = mapped_column(String)
    source_dataset: Mapped[str | None] = mapped_column(String)
    source_record_id: Mapped[str | None] = mapped_column(String)
    geom = Column(Geometry("POINT", srid=4326))
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String)
    category: Mapped[str | None] = mapped_column(String)
    alternate_categories: Mapped[Any | None] = mapped_column(JSON)
    confidence: Mapped[float | None] = mapped_column(Float)
    operating_status: Mapped[str | None] = mapped_column(String)
    address: Mapped[str | None] = mapped_column(String)
    city: Mapped[str | None] = mapped_column(String)
    state: Mapped[str | None] = mapped_column(String)
    postcode: Mapped[str | None] = mapped_column(String)
    country: Mapped[str | None] = mapped_column(String)
    brand_name: Mapped[str | None] = mapped_column(String)
    brand_wikidata: Mapped[str | None] = mapped_column(String)
    website: Mapped[str | None] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String)
    social: Mapped[str | None] = mapped_column(String)
    source_dataset: Mapped[str | None] = mapped_column(String)
    source_record_id: Mapped[str | None] = mapped_column(String)
    geom = Column(Geometry("POINT", srid=4326))
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PlaceName(Base):
    """Precomputed unique brand/name values from places for fast autocomplete."""

    __tablename__ = "place_names"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_type: Mapped[str] = mapped_column(String, nullable=False)  # "brand" or "name"
    value: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # representative category (MIN)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    refreshed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("match_type", "value", name="uq_place_name_type_value"),
        Index(
            "ix_place_names_value_trgm",
            "value",
            postgresql_using="gin",
            postgresql_ops={"value": "gin_trgm_ops"},
        ),
    )


class LlmQualityScore(Base):
    """LLM-generated property quality score from listing description analysis.

    Versioned by (listing_id, model_name, model_version) so multiple model
    versions can coexist for comparison and gold-layer promotion.
    """

    __tablename__ = "llm_quality_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    description_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quality_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    positive_factors: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    negative_factors: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    raw_response: Mapped[Any] = mapped_column(JSON, nullable=False)
    extracted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    photos_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    visual_quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    visual_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_features: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    renovation_level: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_response: Mapped[Any] = mapped_column(JSON, nullable=False)
    extracted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    geography_level: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    geoid: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    acs_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Population (B01001)
    total_population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    male_population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    female_population: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Age (aggregated from B01001 sub-vars)
    pop_under_18: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pop_18_to_22: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pop_23_to_29: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pop_30_to_39: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pop_40_to_49: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pop_50_to_64: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pop_65_plus: Mapped[int | None] = mapped_column(Integer, nullable=True)
    median_age: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Race (B02001)
    race_white: Mapped[int | None] = mapped_column(Integer, nullable=True)
    race_black: Mapped[int | None] = mapped_column(Integer, nullable=True)
    race_american_indian: Mapped[int | None] = mapped_column(Integer, nullable=True)
    race_asian: Mapped[int | None] = mapped_column(Integer, nullable=True)
    race_pacific_islander: Mapped[int | None] = mapped_column(Integer, nullable=True)
    race_other: Mapped[int | None] = mapped_column(Integer, nullable=True)
    race_two_or_more: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Hispanic (B03003)
    hispanic_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    not_hispanic: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hispanic: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Income brackets (B19001)
    total_households: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hh_income_under_10k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hh_income_10k_to_15k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hh_income_15k_to_20k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hh_income_20k_to_25k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hh_income_25k_to_30k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hh_income_30k_to_35k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hh_income_35k_to_40k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hh_income_40k_to_45k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hh_income_45k_to_50k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hh_income_50k_to_60k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hh_income_60k_to_75k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hh_income_75k_to_100k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hh_income_100k_to_125k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hh_income_125k_to_150k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hh_income_150k_to_200k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hh_income_200k_plus: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Median income (B19013)
    median_household_income: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Education (B15003, aggregated into 5 buckets, pop 25+)
    edu_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    edu_less_than_hs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    edu_high_school: Mapped[int | None] = mapped_column(Integer, nullable=True)
    edu_some_college: Mapped[int | None] = mapped_column(Integer, nullable=True)
    edu_bachelors: Mapped[int | None] = mapped_column(Integer, nullable=True)
    edu_graduate_plus: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Home ownership (B25003)
    housing_total_occupied: Mapped[int | None] = mapped_column(Integer, nullable=True)
    housing_owner_occupied: Mapped[int | None] = mapped_column(Integer, nullable=True)
    housing_renter_occupied: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Home value (B25077)
    median_home_value: Mapped[int | None] = mapped_column(Integer, nullable=True)

    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "geography_level",
            "geoid",
            "acs_year",
            name="uq_acs_demo_level_geoid_year",
        ),
    )


class AcsDetailedRace(Base):
    """Detailed race sub-group data from Census ACS tables (e.g. B02015 Asian).

    Stores one row per sub-group per geography, latest vintage only.
    Designed to support future race categories (Hispanic, Pacific Islander).
    """

    __tablename__ = "acs_detailed_race"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    geography_level: Mapped[str] = mapped_column(String(25), nullable=False)
    geoid: Mapped[str] = mapped_column(String(15), nullable=False)
    acs_year: Mapped[int] = mapped_column(Integer, nullable=False)
    race_category: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "asian"
    subgroup_code: Mapped[str] = mapped_column(String(15), nullable=False)  # e.g. "B02015_002E"
    subgroup_label: Mapped[str] = mapped_column(String(60), nullable=False)  # e.g. "Asian Indian"
    population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "geography_level",
            "geoid",
            "acs_year",
            "subgroup_code",
            name="uq_acs_detail_race_geo_year_code",
        ),
        Index("ix_acs_detail_race_lookup", "geography_level", "geoid", "acs_year"),
        Index("ix_acs_detail_race_category", "race_category"),
    )


class GreenspaceRegionMetric(Base):
    """Precomputed greenspace metrics at TIGER geographic levels.

    Stores park/trail counts, area ratios, and z-scores relative to
    peer regions for block_group, tract, county_subdivision, and county.
    """

    __tablename__ = "greenspace_region_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    geo_level: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    geoid: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)

    # Raw counts
    park_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Area / length
    total_park_acres: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_trail_miles: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    greenspace_area_sqm: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    region_land_area_sqm: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    greenspace_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Population-normalized
    population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parks_per_1k_residents: Mapped[float | None] = mapped_column(Float, nullable=True)
    greenspace_acres_per_1k_residents: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Z-scores (relative to peer regions)
    greenspace_ratio_zscore: Mapped[float | None] = mapped_column(Float, nullable=True)
    park_count_zscore: Mapped[float | None] = mapped_column(Float, nullable=True)
    trail_count_zscore: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_park_acres_zscore: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_trail_miles_zscore: Mapped[float | None] = mapped_column(Float, nullable=True)
    parks_per_1k_zscore: Mapped[float | None] = mapped_column(Float, nullable=True)
    greenspace_acres_per_1k_zscore: Mapped[float | None] = mapped_column(Float, nullable=True)

    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("geo_level", "geoid", name="uq_greenspace_region_level_geoid"),
    )


class EconomicIndicator(Base):
    """Macroeconomic time-series observation from FRED."""

    __tablename__ = "economic_indicators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_id: Mapped[str] = mapped_column(String, nullable=False)
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    loaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("series_id", "observation_date", name="uq_economic_series_date"),
        Index("idx_economic_series_date", "series_id", "observation_date"),
    )


class User(Base):
    """Application user account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool | None] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )
    is_admin: Mapped[bool | None] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    oauth_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    oauth_id: Mapped[str | None] = mapped_column(String, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )


class SavedProperty(Base):
    """Property saved/bookmarked by a user."""

    __tablename__ = "saved_properties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    listing_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("redfin_listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "listing_id", name="uq_saved_property_user_listing"),
    )


class SavedPoi(Base):
    """A POI (brand or name) saved by a user for proximity tracking."""

    __tablename__ = "saved_pois"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    match_type: Mapped[str] = mapped_column(String, nullable=False)  # "brand" or "name"
    match_value: Mapped[str] = mapped_column(String, nullable=False)  # exact value to match
    display_name: Mapped[str] = mapped_column(String, nullable=False)  # UI label
    category: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # informational, from Overture
    user_category: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # user-defined grouping
    marker_color: Mapped[str | None] = mapped_column(
        String(7), nullable=True
    )  # hex color like #FF5733
    marker_image_url: Mapped[str | None] = mapped_column(String, nullable=True)  # optional logo URL
    alternate_names: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True, server_default=text("'{}'")
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "match_type", "match_value", name="uq_saved_poi_user_match"),
    )


class DataRequest(Base):
    """User request to populate data for a property not yet in the database."""

    __tablename__ = "data_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'pending'"))
    requested_by_email: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )


class PropertyFeature(Base):
    """Persisted feature matrix row for a single property.

    Stores the assembled feature vector as JSONB so downstream consumers
    (model training, SHAP API, batch scoring) can read features without
    re-running the full feature engineering pipeline.
    """

    __tablename__ = "property_features"
    __table_args__ = (Index("ix_property_features_computed_at", "computed_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(
        Integer,
        ForeignKey("redfin_listings.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    features: Mapped[Any] = mapped_column(JSON, nullable=False)
    feature_hash: Mapped[str] = mapped_column(String, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )


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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(
        Integer,
        ForeignKey("redfin_listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    shap_values: Mapped[Any] = mapped_column(JSON, nullable=False)
    base_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    computed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    township_geoid: Mapped[str] = mapped_column(String(10), nullable=False)
    metric_month: Mapped[date] = mapped_column(Date, nullable=False)
    avg_days_on_market_1m: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_days_on_market_3m: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_days_on_market_1y: Mapped[float | None] = mapped_column(Float, nullable=True)
    median_sale_price_1m: Mapped[float | None] = mapped_column(Float, nullable=True)
    median_sale_price_3m: Mapped[float | None] = mapped_column(Float, nullable=True)
    median_sale_price_1y: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_count_1m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sample_count_3m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sample_count_1y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    built_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ApiKey(Base):
    """API key for programmatic access."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool | None] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )

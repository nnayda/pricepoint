"""SQLAlchemy ORM models with PostGIS geometry columns."""

from geoalchemy2 import Geometry
from sqlalchemy import Column, DateTime, Float, Integer, String, func
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


class School(Base):
    """School location and rating data."""

    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    school_type = Column(String)
    rating = Column(Float)
    location = Column(Geometry("POINT", srid=4326))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

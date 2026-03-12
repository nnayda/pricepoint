"""Integration tests for SQLAlchemy ORM models."""

import pytest
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point
from sqlalchemy.exc import IntegrityError

from pricepoint.db.models import PoliceIncident, Property, School


class TestPropertyModel:
    """Tests for the Property ORM model."""

    def test_create_property_with_geometry(self, db_session):
        """Create a property with a POINT geometry and read it back."""
        prop = Property(
            parcel_id="TEST-001",
            address="123 Test St",
            city="Testville",
            state="NC",
            zip_code="27511",
            assessed_value=350_000.0,
            location=from_shape(Point(-78.78, 35.78), srid=4326),
        )
        db_session.add(prop)
        db_session.flush()

        assert prop.id is not None
        point = to_shape(prop.location)
        assert round(point.x, 2) == -78.78
        assert round(point.y, 2) == 35.78

    def test_parcel_id_unique_constraint(self, db_session):
        """Duplicate parcel_id should raise IntegrityError."""
        prop1 = Property(parcel_id="DUP-001", address="1 Main St")
        prop2 = Property(parcel_id="DUP-001", address="2 Main St")
        db_session.add(prop1)
        db_session.flush()
        db_session.add(prop2)
        with pytest.raises(IntegrityError):
            db_session.flush()


class TestPoliceIncidentModel:
    """Tests for the PoliceIncident ORM model."""

    def test_create_incident_with_geometry(self, db_session):
        """Create a police incident with a POINT geometry."""
        incident = PoliceIncident(
            incident_id="INC-001",
            crime_category="THEFT",
            location=from_shape(Point(-78.64, 35.77), srid=4326),
        )
        db_session.add(incident)
        db_session.flush()

        assert incident.id is not None
        point = to_shape(incident.location)
        assert round(point.x, 2) == -78.64


class TestSchoolModel:
    """Tests for the School ORM model (gold layer)."""

    def test_create_school_with_geometry(self, db_session):
        """Create a gold school with a POINT geometry and NCES data."""
        school = School(
            nces_id="370001000001",
            name="Test Elementary",
            school_type="Regular",
            school_level="Elementary",
            rating=8.5,
            location=from_shape(Point(-78.80, 35.82), srid=4326),
        )
        db_session.add(school)
        db_session.flush()

        assert school.id is not None
        assert school.nces_id == "370001000001"
        assert school.rating == 8.5
        point = to_shape(school.location)
        assert round(point.x, 2) == -78.80

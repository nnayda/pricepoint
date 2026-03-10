"""Tests for the comparables route endpoint."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from pricepoint.api.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def _mock_listing(
    id_: int = 1,
    street_address: str = "100 Main St",
    city: str = "Cary",
    state: str = "NC",
    zip_code: str = "27513",
    num_beds: int = 3,
    num_baths: float = 2.0,
    sqft: int = 2000,
    lot_size: float = 0.25,
    year_built: int = 2005,
    listing_status: str = "Sold",
    sold_price: float = 400_000,
    sold_date: None = None,
    listing_price: float = 410_000,
    num_garage_spaces: int = 2,
    price_per_sqft: float = 200.0,
    property_photos: list | None = None,
    location: object = "fake_geom",
) -> MagicMock:
    mock = MagicMock()
    mock.id = id_
    mock.street_address = street_address
    mock.city = city
    mock.state = state
    mock.zip_code = zip_code
    mock.num_beds = num_beds
    mock.num_baths = num_baths
    mock.sqft = sqft
    mock.lot_size = lot_size
    mock.year_built = year_built
    mock.listing_status = listing_status
    mock.sold_price = sold_price
    mock.sold_date = sold_date
    mock.listing_price = listing_price
    mock.num_garage_spaces = num_garage_spaces
    mock.price_per_sqft = price_per_sqft
    mock.property_photos = property_photos or []
    mock.location = location
    mock.num_stories = 2
    mock.description = "A nice house"
    mock.redfin_url = None
    mock.association_fee = None
    mock.contract_date = None
    return mock


class TestComparablesEndpoint:
    """Tests for GET /api/comparables/search."""

    def test_404_when_no_subject(self, client):
        """Should return 404 when subject property is not found."""
        with patch("pricepoint.api.routes.comparables.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.execute.return_value.scalar_one_or_none.return_value = None
            mock_get_db.return_value = iter([mock_db])

            app.dependency_overrides[
                __import__("pricepoint.api.dependencies", fromlist=["get_db"]).get_db
            ] = lambda: mock_db

            resp = client.get(
                "/api/comparables/search",
                params={"lat": 35.7, "lon": -78.8, "address": "123 Fake St"},
            )
            assert resp.status_code == 404

            app.dependency_overrides.clear()

    def test_schema_validation(self):
        """ComparablesResponse schema should accept valid data."""
        from pricepoint.api.schemas.comparables import (
            ComparablesResponse,
            CompProperty,
            FeatureGroup,
        )

        subject = CompProperty(
            listing_id=1,
            address="100 Main St",
            city="Cary",
            state="NC",
            zip_code="27513",
            lat=35.7,
            lon=-78.8,
            beds=3,
            baths=2.0,
        )
        comp = CompProperty(
            listing_id=2,
            address="200 Oak Ave",
            city="Cary",
            state="NC",
            zip_code="27513",
            lat=35.71,
            lon=-78.81,
            beds=3,
            baths=2.0,
            similarity_distance=1.234,
            feature_groups=[
                FeatureGroup(
                    category="Core Stats",
                    features={"property_age": 15, "bed_bath_ratio": 1.5},
                )
            ],
        )
        resp = ComparablesResponse(
            subject=subject,
            comparables=[comp],
            total_candidates=10,
        )
        assert resp.total_candidates == 10
        assert len(resp.comparables) == 1
        assert resp.comparables[0].similarity_distance == 1.234

    def test_empty_comparables_response(self):
        """Should handle zero comparables."""
        from pricepoint.api.schemas.comparables import ComparablesResponse, CompProperty

        subject = CompProperty(
            listing_id=1,
            address="100 Main St",
            city="Cary",
            state="NC",
            zip_code="27513",
            lat=35.7,
            lon=-78.8,
            beds=3,
            baths=2.0,
        )
        resp = ComparablesResponse(subject=subject, comparables=[], total_candidates=0)
        data = resp.model_dump()
        assert data["total_candidates"] == 0
        assert data["comparables"] == []

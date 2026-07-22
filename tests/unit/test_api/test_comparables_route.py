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
    listing_status: str = "SOLD",
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
        from pricepoint.api.dependencies import get_db

        mock_db = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        # Override via dependency_overrides only. Patching the module-level
        # get_db corrupts FastAPI's lazily-built (and cached) dependency
        # graph: the MagicMock's (*args, **kwargs) signature gets read as
        # required query params, turning every later request into a 422.
        app.dependency_overrides[get_db] = lambda: mock_db
        try:
            resp = client.get(
                "/api/comparables/search",
                params={"lat": 35.7, "lon": -78.8, "address": "123 Fake St"},
            )
            assert resp.status_code == 404
        finally:
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

    def test_null_fields_not_excluded_by_range_filters(self, client):
        """Candidates with NULL sqft/lot_size/year_built should not be excluded."""
        from pricepoint.api.dependencies import get_db

        subject = _mock_listing(id_=1, sqft=2000, lot_size=0.25, year_built=2005)
        candidate = _mock_listing(
            id_=2,
            street_address="200 Oak Ave",
            sqft=None,
            lot_size=None,
            year_built=None,
        )

        mock_db = MagicMock()

        # First call: subject lookup (scalar_one_or_none)
        # Second call: geo lookup (scalar_one_or_none)
        # Third call: candidate IDs (all)
        # Then various calls for building CompProperty
        call_count = {"n": 0}

        def mock_execute(stmt):
            call_count["n"] += 1
            result = MagicMock()
            n = call_count["n"]

            if n == 1:
                # Subject lookup
                result.scalar_one_or_none.return_value = subject
            elif n == 2:
                # Geo lookup for school district
                result.scalar_one_or_none.return_value = None
            elif n == 3:
                # Candidate IDs query — return candidate
                row = MagicMock()
                row.__getitem__ = lambda self, i: candidate.id
                result.all.return_value = [row]
            elif n == 4:
                # ST_Y/ST_X for subject coords
                coord = MagicMock()
                coord.lat = 35.7
                coord.lon = -78.8
                result.one.return_value = coord
            elif n == 5:
                # LLM quality score for subject
                result.scalar_one_or_none.return_value = None
            elif n == 6:
                # LLM photo score for subject
                result.scalar_one_or_none.return_value = None
            elif n == 7:
                # Comp listings fetch
                result.scalars.return_value.all.return_value = [candidate]
            elif n == 8:
                # ST_Y/ST_X for candidate coords
                coord = MagicMock()
                coord.lat = 35.71
                coord.lon = -78.81
                result.one.return_value = coord
            elif n == 9:
                # LLM quality score for candidate
                result.scalar_one_or_none.return_value = None
            elif n == 10:
                # LLM photo score for candidate
                result.scalar_one_or_none.return_value = None
            else:
                result.all.return_value = []
                result.scalar_one_or_none.return_value = None
                result.scalars.return_value.all.return_value = []

            return result

        mock_db.execute = mock_execute

        with (
            patch("pricepoint.api.routes.comparables.assemble_features", return_value=None),
            patch("pricepoint.api.routes.comparables.query_nuisance_sources", return_value=[]),
            patch("pricepoint.api.routes.comparables.query_risk_features", return_value=[]),
        ):
            app.dependency_overrides[get_db] = lambda: mock_db
            try:
                resp = client.get(
                    "/api/comparables/search",
                    params={
                        "lat": 35.7,
                        "lon": -78.8,
                        "address": "100 Main St",
                        "sqft_pct": 10,
                        "lot_pct": 10,
                        "year_built_diff": 10,
                        "same_schools": False,
                        "same_beds": False,
                        "same_baths": False,
                    },
                )
                assert resp.status_code == 200
                data = resp.json()
                # The NULL-field candidate should be included, not filtered out
                assert data["total_candidates"] == 1
                assert len(data["comparables"]) == 1
            finally:
                app.dependency_overrides.clear()

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

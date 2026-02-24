"""Tests for the neighborhood valuation endpoints."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def mock_db(app):
    """Return the mock DB session used by the app."""
    from pricepoint.api.dependencies import get_db

    gen = app.dependency_overrides[get_db]()
    return next(gen)


class TestNeighborhoodValuation:
    """GET /api/neighborhood/valuation tests."""

    def test_no_tract_found(self, client, mock_db):
        """When no census tract contains the point, return unknown with nulls."""
        # first() returns None for tract lookup
        mock_db.execute.return_value.first.return_value = None

        resp = client.get("/api/neighborhood/valuation", params={"lat": 35.7, "lon": -78.6})
        assert resp.status_code == 200
        body = resp.json()
        assert body["tract_geoid"] == "unknown"
        assert body["median_value"] is None
        assert body["max_value"] is None
        assert body["sample_size"] == 0

    def test_tract_found_no_listings(self, client, mock_db):
        """Tract found but no listings → null median/max, sample_size=0."""
        # First call: tract lookup returns a row
        tract_row = MagicMock()
        tract_row.geoid = "37183052404"
        tract_row.geom = "fake_geom"

        # Second call: stats query returns count=0
        stats_row = MagicMock()
        stats_row.cnt = 0
        stats_row.median = None
        stats_row.max_val = None

        mock_db.execute.return_value.first.side_effect = [tract_row, stats_row]

        resp = client.get("/api/neighborhood/valuation", params={"lat": 35.7, "lon": -78.6})
        assert resp.status_code == 200
        body = resp.json()
        assert body["tract_geoid"] == "37183052404"
        assert body["median_value"] is None
        assert body["max_value"] is None
        assert body["sample_size"] == 0

    def test_under_five_properties(self, client, mock_db):
        """Fewer than 5 properties → null median/max with actual sample_size."""
        tract_row = MagicMock()
        tract_row.geoid = "37183052404"
        tract_row.geom = "fake_geom"

        stats_row = MagicMock()
        stats_row.cnt = 3
        stats_row.median = 400000.0
        stats_row.max_val = 500000.0

        mock_db.execute.return_value.first.side_effect = [tract_row, stats_row]

        resp = client.get("/api/neighborhood/valuation", params={"lat": 35.7, "lon": -78.6})
        assert resp.status_code == 200
        body = resp.json()
        assert body["tract_geoid"] == "37183052404"
        assert body["median_value"] is None
        assert body["max_value"] is None
        assert body["sample_size"] == 3

    def test_sufficient_properties(self, client, mock_db):
        """5+ properties → returns computed median and max."""
        tract_row = MagicMock()
        tract_row.geoid = "37183052404"
        tract_row.geom = "fake_geom"

        stats_row = MagicMock()
        stats_row.cnt = 12
        stats_row.median = 445000.50
        stats_row.max_val = 625000.0

        mock_db.execute.return_value.first.side_effect = [tract_row, stats_row]

        resp = client.get("/api/neighborhood/valuation", params={"lat": 35.7, "lon": -78.6})
        assert resp.status_code == 200
        body = resp.json()
        assert body["tract_geoid"] == "37183052404"
        assert body["median_value"] == 445000.50
        assert body["max_value"] == 625000.0
        assert body["sample_size"] == 12

    def test_missing_params(self, client):
        """Missing lat/lon returns 422."""
        resp = client.get("/api/neighborhood/valuation")
        assert resp.status_code == 422

    def test_invalid_lat(self, client):
        """Lat out of range returns 422."""
        resp = client.get("/api/neighborhood/valuation", params={"lat": 100, "lon": -78.6})
        assert resp.status_code == 422

    def test_invalid_lon(self, client):
        """Lon out of range returns 422."""
        resp = client.get("/api/neighborhood/valuation", params={"lat": 35.7, "lon": -200})
        assert resp.status_code == 422


class TestNeighborhoodValuationHistory:
    """GET /api/neighborhood/valuation/history tests."""

    def test_no_tract_found(self, client, mock_db):
        """No census tract → unknown with empty medians."""
        mock_db.execute.return_value.first.return_value = None

        resp = client.get(
            "/api/neighborhood/valuation/history",
            params={"lat": 35.7, "lon": -78.6},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["tract_geoid"] == "unknown"
        assert body["sample_size"] == 0
        assert body["monthly_medians"] == []

    def test_no_properties_in_tract(self, client, mock_db):
        """Tract found but no properties → empty."""
        tract_row = MagicMock()
        tract_row.geoid = "37183052404"
        tract_row.geom = "fake_geom"

        # first() for tract, all() for prop_ids
        mock_db.execute.return_value.first.return_value = tract_row
        mock_db.execute.return_value.all.return_value = []

        resp = client.get(
            "/api/neighborhood/valuation/history",
            params={"lat": 35.7, "lon": -78.6},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["tract_geoid"] == "37183052404"
        assert body["sample_size"] == 0

    def test_insufficient_sale_data(self, client, mock_db):
        """Only 2 properties with sales → under threshold, no medians."""
        tract_row = MagicMock()
        tract_row.geoid = "37183052404"
        tract_row.geom = "fake_geom"

        # Mock: first() returns tract, first all() returns prop IDs,
        # second all() returns sale rows with only 2 properties
        prop_rows = [(1,), (2,)]
        sale_rows = [
            MagicMock(property_id=1, date=datetime(2022, 6, 1), price=300000.0),
            MagicMock(property_id=2, date=datetime(2022, 6, 1), price=350000.0),
        ]

        mock_db.execute.return_value.first.return_value = tract_row
        mock_db.execute.return_value.all.side_effect = [prop_rows, sale_rows]

        resp = client.get(
            "/api/neighborhood/valuation/history",
            params={"lat": 35.7, "lon": -78.6},
        )
        assert resp.status_code == 200
        body = resp.json()
        # 2 properties interpolated, but each month only has 2 values < 3 threshold
        assert body["sample_size"] == 2
        assert body["monthly_medians"] == []

    def test_successful_interpolation(self, client, mock_db):
        """3+ properties with sale data → monthly medians returned."""
        tract_row = MagicMock()
        tract_row.geoid = "37183052404"
        tract_row.geom = "fake_geom"

        prop_rows = [(1,), (2,), (3,)]
        sale_rows = [
            MagicMock(property_id=1, date=datetime(2022, 1, 15), price=300000.0),
            MagicMock(property_id=2, date=datetime(2022, 1, 15), price=350000.0),
            MagicMock(property_id=3, date=datetime(2022, 1, 15), price=400000.0),
        ]

        mock_db.execute.return_value.first.return_value = tract_row
        mock_db.execute.return_value.all.side_effect = [prop_rows, sale_rows]

        resp = client.get(
            "/api/neighborhood/valuation/history",
            params={"lat": 35.7, "lon": -78.6},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["tract_geoid"] == "37183052404"
        assert body["sample_size"] == 3
        assert len(body["monthly_medians"]) > 0
        # Median of 300k, 350k, 400k = 350k
        medians = {m["date"]: m["median_value"] for m in body["monthly_medians"]}
        assert medians["2022-01"] == 350000.0

    def test_missing_params(self, client):
        """Missing lat/lon returns 422."""
        resp = client.get("/api/neighborhood/valuation/history")
        assert resp.status_code == 422

    def test_invalid_lat(self, client):
        """Lat out of range returns 422."""
        resp = client.get(
            "/api/neighborhood/valuation/history",
            params={"lat": 100, "lon": -78.6},
        )
        assert resp.status_code == 422

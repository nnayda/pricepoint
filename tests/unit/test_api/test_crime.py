"""Tests for the crime endpoint."""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from pricepoint.api.dependencies import get_db, get_valkey
from pricepoint.api.main import create_app


class _FakeRow:
    """Lightweight row object that supports attribute access like a SQLAlchemy Row."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            object.__setattr__(self, k, v)


def _make_row(
    incident_id="1",
    lat=35.79,
    lon=-78.78,
    occurred_at=None,
    description="Larceny",
    category="Property",
    source_city="Cary",
):
    """Create a mock DB row for crime query results."""
    if occurred_at is None:
        occurred_at = datetime.now(tz=UTC) - timedelta(days=30)
    return _FakeRow(
        incident_id=incident_id,
        lat=lat,
        lon=lon,
        occurred_at=occurred_at,
        description=description,
        category=category,
        source_city=source_city,
    )


@pytest.fixture
def crime_app():
    """Create a test app with mocked DB that returns crime data."""
    app = create_app()
    mock_session = MagicMock()

    now = datetime.now(tz=UTC)
    rows = [
        _make_row(
            incident_id="1",
            description="Larceny",
            category="Property",
            source_city="Cary",
            occurred_at=now - timedelta(days=10),
        ),
        _make_row(
            incident_id="2",
            description="Assault",
            category="Violent",
            source_city="Raleigh",
            occurred_at=now - timedelta(days=20),
            lat=35.791,
            lon=-78.781,
        ),
        _make_row(
            incident_id="3",
            description="Burglary",
            category="Property",
            source_city="Morrisville",
            occurred_at=now - timedelta(days=60),
            lat=35.792,
            lon=-78.782,
        ),
    ]

    mock_result = MagicMock()
    mock_result.all.return_value = rows

    # For the prior-period count query, return 0
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 2

    mock_session.execute.side_effect = [mock_result, mock_count_result]

    def _override_get_db():
        yield mock_session

    async def _override_get_valkey():
        yield None

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_valkey] = _override_get_valkey
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def crime_client(crime_app):
    """Test client for the crime app."""
    return TestClient(crime_app)


@pytest.fixture
def empty_crime_app():
    """Create a test app with mocked DB that returns no crime data."""
    app = create_app()
    mock_session = MagicMock()

    mock_result = MagicMock()
    mock_result.all.return_value = []

    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 0

    mock_session.execute.side_effect = [mock_result, mock_count_result]

    def _override_get_db():
        yield mock_session

    async def _override_get_valkey():
        yield None

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_valkey] = _override_get_valkey
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def empty_crime_client(empty_crime_app):
    """Test client for empty crime results."""
    return TestClient(empty_crime_app)


class TestCrimeReturns200:
    def test_returns_200_with_valid_params(self, crime_client):
        """GET /api/crime with valid params returns 200."""
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_response_is_json(self, crime_client):
        """Response body is valid JSON."""
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        data = resp.json()
        assert isinstance(data, dict)


class TestCrimeResponseShape:
    def test_response_has_all_top_level_keys(self, crime_client):
        """Response contains heatmap, incidents, and metrics."""
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        data = resp.json()
        for key in ["heatmap", "incidents", "metrics"]:
            assert key in data, f"Missing key: {key}"

    def test_heatmap_is_list(self, crime_client):
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["heatmap"], list)

    def test_incidents_is_list(self, crime_client):
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["incidents"], list)

    def test_metrics_is_dict(self, crime_client):
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["metrics"], dict)


class TestCrimeDataTypes:
    def test_heatmap_point_has_fields(self, crime_client):
        """Each heatmap point has lat, lon, intensity."""
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        points = resp.json()["heatmap"]
        assert len(points) > 0
        for field in ["lat", "lon", "intensity"]:
            assert field in points[0]

    def test_heatmap_intensity_is_float(self, crime_client):
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        point = resp.json()["heatmap"][0]
        assert isinstance(point["intensity"], (int, float))

    def test_incident_has_required_fields(self, crime_client):
        """Each incident has id, incident_type, category, date, lat, lon."""
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        incidents = resp.json()["incidents"]
        assert len(incidents) > 0
        for field in ["id", "incident_type", "category", "date", "lat", "lon"]:
            assert field in incidents[0], f"Missing incident field: {field}"

    def test_metrics_has_required_fields(self, crime_client):
        """Metrics has total_incidents_1mi, incidents_per_1000_people, crime_z_score, trend."""
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        metrics = resp.json()["metrics"]
        for field in [
            "total_incidents_1mi",
            "incidents_per_1000_people",
            "crime_z_score",
            "trend",
        ]:
            assert field in metrics, f"Missing metrics field: {field}"

    def test_total_incidents_is_int(self, crime_client):
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["metrics"]["total_incidents_1mi"], int)

    def test_trend_is_string(self, crime_client):
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["metrics"]["trend"], str)


class TestCrimeMissingParams:
    def test_missing_all_params_returns_422(self, crime_client):
        resp = crime_client.get("/api/crime")
        assert resp.status_code == 422

    def test_missing_lat_returns_422(self, crime_client):
        resp = crime_client.get("/api/crime", params={"lon": -78.78})
        assert resp.status_code == 422

    def test_missing_lon_returns_422(self, crime_client):
        resp = crime_client.get("/api/crime", params={"lat": 35.79})
        assert resp.status_code == 422


class TestCrimeParamValidation:
    def test_lat_out_of_range_returns_422(self, crime_client):
        resp = crime_client.get("/api/crime", params={"lat": 91.0, "lon": -78.78})
        assert resp.status_code == 422

    def test_lat_below_range_returns_422(self, crime_client):
        resp = crime_client.get("/api/crime", params={"lat": -91.0, "lon": -78.78})
        assert resp.status_code == 422

    def test_lon_out_of_range_returns_422(self, crime_client):
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": 181.0})
        assert resp.status_code == 422

    def test_lon_below_range_returns_422(self, crime_client):
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": -181.0})
        assert resp.status_code == 422

    def test_radius_zero_returns_422(self, crime_client):
        """radius_miles=0 should fail (gt=0 constraint)."""
        resp = crime_client.get(
            "/api/crime",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 0},
        )
        assert resp.status_code == 422

    def test_radius_negative_returns_422(self, crime_client):
        resp = crime_client.get(
            "/api/crime",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": -1},
        )
        assert resp.status_code == 422

    def test_radius_too_large_returns_422(self, crime_client):
        """radius_miles > 10 should fail (le=10 constraint)."""
        resp = crime_client.get(
            "/api/crime",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 11},
        )
        assert resp.status_code == 422

    def test_days_back_zero_returns_422(self, crime_client):
        """days_back=0 should fail (ge=1 constraint)."""
        resp = crime_client.get(
            "/api/crime",
            params={"lat": 35.79, "lon": -78.78, "days_back": 0},
        )
        assert resp.status_code == 422

    def test_days_back_too_large_returns_422(self, crime_client):
        """days_back > 3650 should fail."""
        resp = crime_client.get(
            "/api/crime",
            params={"lat": 35.79, "lon": -78.78, "days_back": 3651},
        )
        assert resp.status_code == 422


class TestCrimeDefaultRadius:
    def test_default_radius_works(self, crime_client):
        """Omitting radius_miles uses default and returns 200."""
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_explicit_radius_works(self, crime_client):
        """Providing explicit radius_miles returns 200."""
        resp = crime_client.get(
            "/api/crime",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 5.0},
        )
        assert resp.status_code == 200


class TestCrimeWithData:
    """Tests that verify real data processing from mocked DB rows."""

    def test_heatmap_count_matches_rows(self, crime_client):
        """Heatmap should have one point per row."""
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert len(resp.json()["heatmap"]) == 3

    def test_incidents_count_matches_rows(self, crime_client):
        """Incidents list matches the rows (capped at 50)."""
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert len(resp.json()["incidents"]) == 3

    def test_total_incidents_metric(self, crime_client):
        """total_incidents_1mi should equal the number of rows."""
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert resp.json()["metrics"]["total_incidents_1mi"] == 3

    def test_incident_id_includes_source_city(self, crime_client):
        """Incident IDs should be prefixed with source city."""
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        incident = resp.json()["incidents"][0]
        # First row is Cary (most recent)
        assert incident["id"].startswith("Cary-")

    def test_incidents_sorted_by_date_desc(self, crime_client):
        """Incidents should be sorted most recent first."""
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        incidents = resp.json()["incidents"]
        dates = [i["date"] for i in incidents]
        assert dates == sorted(dates, reverse=True)

    def test_heatmap_intensity_in_valid_range(self, crime_client):
        """Heatmap intensity values should be between 0 and 1."""
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        for point in resp.json()["heatmap"]:
            assert 0.0 < point["intensity"] <= 1.0

    def test_violent_incident_detected(self, crime_client):
        """Assault is a violent category so it should be reflected in data."""
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        categories = {i["category"] for i in resp.json()["incidents"]}
        assert "Violent" in categories

    def test_multiple_source_cities(self, crime_client):
        """Incidents come from multiple source cities."""
        resp = crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        ids = [i["id"] for i in resp.json()["incidents"]]
        prefixes = {i.split("-")[0] for i in ids}
        assert len(prefixes) >= 2


class TestCrimeEmptyResults:
    """Tests for when no incidents are found in the area."""

    def test_empty_returns_200(self, empty_crime_client):
        """Should still return 200 with empty lists."""
        resp = empty_crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_empty_heatmap(self, empty_crime_client):
        resp = empty_crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert resp.json()["heatmap"] == []

    def test_empty_incidents(self, empty_crime_client):
        resp = empty_crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert resp.json()["incidents"] == []

    def test_empty_metrics_zero(self, empty_crime_client):
        resp = empty_crime_client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        metrics = resp.json()["metrics"]
        assert metrics["total_incidents_1mi"] == 0
        assert metrics["crime_z_score"] == 0.0


class TestCrimeValkeyCaching:
    """Tests for Valkey cache integration."""

    def test_cache_hit_returns_cached_data(self):
        """When cache has data, should return it without DB query."""
        app = create_app()
        mock_session = MagicMock()
        mock_valkey = AsyncMock()

        cached_response = {
            "heatmap": [{"lat": 35.79, "lon": -78.78, "intensity": 0.5}],
            "incidents": [
                {
                    "id": "Cary-1",
                    "incident_type": "Larceny",
                    "category": "Property",
                    "date": "2024-12-01",
                    "lat": 35.79,
                    "lon": -78.78,
                    "description": "Theft",
                }
            ],
            "metrics": {
                "total_incidents_1mi": 1,
                "incidents_per_1000_people": 5.0,
                "crime_z_score": -0.5,
                "trend": "stable",
            },
        }
        mock_valkey.get.return_value = json.dumps(cached_response)

        def _override_get_db():
            yield mock_session

        async def _override_get_valkey():
            yield mock_valkey

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_valkey] = _override_get_valkey

        client = TestClient(app)
        resp = client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200
        assert resp.json()["heatmap"][0]["intensity"] == 0.5
        # DB should not have been queried
        mock_session.execute.assert_not_called()
        app.dependency_overrides.clear()

    def test_cache_miss_queries_db_and_caches(self):
        """When cache misses, should query DB and write to cache."""
        app = create_app()
        mock_session = MagicMock()
        mock_valkey = AsyncMock()
        mock_valkey.get.return_value = None  # Cache miss

        now = datetime.now(tz=UTC)
        rows = [
            _make_row(occurred_at=now - timedelta(days=5)),
        ]
        mock_result = MagicMock()
        mock_result.all.return_value = rows
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0
        mock_session.execute.side_effect = [mock_result, mock_count_result]

        def _override_get_db():
            yield mock_session

        async def _override_get_valkey():
            yield mock_valkey

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_valkey] = _override_get_valkey

        client = TestClient(app)
        resp = client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200
        # DB was queried
        assert mock_session.execute.call_count == 2
        # Cache was written
        mock_valkey.set.assert_called_once()
        app.dependency_overrides.clear()


class TestCrimeHelperFunctions:
    """Tests for internal helper functions."""

    def test_compute_intensity_recent(self):
        """Recent incident should have high intensity."""
        from pricepoint.api.routes.crime import _compute_intensity

        now = datetime.now(tz=UTC)
        recent = now - timedelta(days=1)
        intensity = _compute_intensity(recent, now, 365)
        assert intensity > 0.9

    def test_compute_intensity_old(self):
        """Old incident should have low intensity."""
        from pricepoint.api.routes.crime import _compute_intensity

        now = datetime.now(tz=UTC)
        old = now - timedelta(days=300)
        intensity = _compute_intensity(old, now, 365)
        assert intensity < 0.2

    def test_is_violent_true(self):
        """Assault category should be detected as violent."""
        from pricepoint.api.routes.crime import _is_violent

        assert _is_violent("Violent", "Assault at store") is True

    def test_is_violent_false(self):
        """Larceny is not violent."""
        from pricepoint.api.routes.crime import _is_violent

        assert _is_violent("Property", "Larceny from vehicle") is False

    def test_compute_trend_increasing(self):
        """More current than prior -> increasing."""
        from pricepoint.api.routes.crime import _compute_trend

        label, pct = _compute_trend(120, 80)
        assert label == "increasing"
        assert pct > 0

    def test_compute_trend_decreasing(self):
        """Fewer current than prior -> decreasing."""
        from pricepoint.api.routes.crime import _compute_trend

        label, pct = _compute_trend(70, 100)
        assert label == "decreasing"
        assert pct < 0

    def test_compute_trend_stable(self):
        """Similar counts -> stable."""
        from pricepoint.api.routes.crime import _compute_trend

        label, pct = _compute_trend(100, 100)
        assert label == "stable"

    def test_cache_key_deterministic(self):
        """Same inputs should produce the same cache key."""
        from pricepoint.api.routes.crime import _cache_key

        k1 = _cache_key(35.79, -78.78, 1.0, 365)
        k2 = _cache_key(35.79, -78.78, 1.0, 365)
        assert k1 == k2

    def test_cache_key_varies_with_params(self):
        """Different inputs should produce different cache keys."""
        from pricepoint.api.routes.crime import _cache_key

        k1 = _cache_key(35.79, -78.78, 1.0, 365)
        k2 = _cache_key(35.79, -78.78, 2.0, 365)
        assert k1 != k2

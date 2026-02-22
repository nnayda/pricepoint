"""Tests for the schools/nearby endpoint."""

from unittest.mock import MagicMock, PropertyMock


class TestSchoolsNearbyParams:
    def test_missing_lat_returns_422(self, client):
        resp = client.get("/api/schools/nearby", params={"lon": -78.78})
        assert resp.status_code == 422

    def test_missing_lon_returns_422(self, client):
        resp = client.get("/api/schools/nearby", params={"lat": 35.79})
        assert resp.status_code == 422

    def test_lat_out_of_range_returns_422(self, client):
        resp = client.get("/api/schools/nearby", params={"lat": 91, "lon": -78.78})
        assert resp.status_code == 422

    def test_lon_out_of_range_returns_422(self, client):
        resp = client.get("/api/schools/nearby", params={"lat": 35.79, "lon": 181})
        assert resp.status_code == 422

    def test_radius_negative_returns_422(self, client):
        resp = client.get(
            "/api/schools/nearby",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": -1},
        )
        assert resp.status_code == 422

    def test_limit_zero_returns_422(self, client):
        resp = client.get(
            "/api/schools/nearby",
            params={"lat": 35.79, "lon": -78.78, "limit": 0},
        )
        assert resp.status_code == 422


class TestSchoolsNearbyEmpty:
    def test_returns_empty_list_when_no_schools(self, client):
        """Returns empty list when no schools are in the DB."""
        resp = client.get(
            "/api/schools/nearby",
            params={"lat": 35.79, "lon": -78.78},
        )
        assert resp.status_code == 200
        assert resp.json() == []


class TestSchoolsNearbyWithData:
    def _make_school(self, school_id=1, name="Test Elementary", lat=35.79, lon=-78.78):
        """Create a mock School object."""
        school = MagicMock()
        school.id = school_id
        school.name = name
        school.street = "100 School Rd"
        school.city = "Cary"
        school.state = "NC"
        school.zip_code = "27513"
        school.school_type = "Regular"
        school.school_level = "Elementary"
        school.rating = 8.0
        school.grades = "K-5"
        school.enrollment = 500
        school.student_teacher_ratio = 15.0
        school.location = MagicMock()  # non-None geometry
        return school

    def test_returns_schools_with_correct_fields(self, app):
        """Nearby schools are returned with all expected fields."""
        from fastapi.testclient import TestClient

        from pricepoint.api.dependencies import get_db

        mock_db = MagicMock()
        school = self._make_school()

        # First execute: spatial school query → returns [(school, distance_m)]
        # Second execute: property lookup → returns None
        # Third execute: ST_Y/ST_X coord extraction
        school_row = MagicMock()
        school_row.__iter__ = MagicMock(return_value=iter([school, 1609.0]))

        call_count = 0

        def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()

            if call_count == 1:
                # Spatial school query
                result.all.return_value = [(school, 1609.0)]
                return result
            elif call_count == 2:
                # Property lookup
                result.scalar_one_or_none.return_value = None
                return result
            else:
                # ST_Y / ST_X coordinate extraction
                coord = MagicMock()
                coord.lat = 35.79
                coord.lon = -78.78
                result.one.return_value = coord
                return result

        mock_db.execute = mock_execute

        def _override():
            yield mock_db

        app.dependency_overrides[get_db] = _override
        client = TestClient(app)

        resp = client.get(
            "/api/schools/nearby",
            params={"lat": 35.79, "lon": -78.78},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

        s = data[0]
        assert s["name"] == "Test Elementary"
        assert s["address"] == "100 School Rd, Cary, NC, 27513"
        assert s["school_type"] == "Regular"
        assert s["school_level"] == "Elementary"
        assert s["rating"] == 8
        assert s["grades"] == "K-5"
        assert s["distance_miles"] == 1.0
        assert s["lat"] == 35.79
        assert s["lon"] == -78.78
        assert s["enrollment"] == 500
        assert s["student_teacher_ratio"] == 15.0
        assert s["assigned"] is False

        app.dependency_overrides.clear()

    def test_enriches_with_property_linkage(self, app):
        """Schools are enriched with assigned/travel data when property exists."""
        from fastapi.testclient import TestClient

        from pricepoint.api.dependencies import get_db

        mock_db = MagicMock()
        school = self._make_school()

        # Property linkage
        prop = MagicMock()
        prop.id = 42

        link = MagicMock()
        link.school_id = 1
        link.assigned = True
        link.distance_miles = 0.8
        link.drive_minutes = 3
        link.walk_minutes = 16

        call_count = 0

        def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()

            if call_count == 1:
                # Spatial school query
                result.all.return_value = [(school, 1609.0)]
                return result
            elif call_count == 2:
                # Property lookup
                result.scalar_one_or_none.return_value = prop
                return result
            elif call_count == 3:
                # PropertySchool linkage query
                result.scalars.return_value.all.return_value = [link]
                return result
            else:
                # ST_Y / ST_X coordinate extraction
                coord = MagicMock()
                coord.lat = 35.79
                coord.lon = -78.78
                result.one.return_value = coord
                return result

        mock_db.execute = mock_execute

        def _override():
            yield mock_db

        app.dependency_overrides[get_db] = _override
        client = TestClient(app)

        resp = client.get(
            "/api/schools/nearby",
            params={"lat": 35.79, "lon": -78.78},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

        s = data[0]
        assert s["assigned"] is True
        assert s["distance_miles"] == 0.8  # Uses linkage distance
        assert s["drive_minutes"] == 3
        assert s["walk_minutes"] == 16

        app.dependency_overrides.clear()

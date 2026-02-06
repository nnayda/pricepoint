"""Tests for the crime endpoint."""


class TestCrimeReturns200:
    def test_returns_200_with_valid_params(self, client):
        """GET /api/crime with valid params returns 200."""
        resp = client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_response_is_json(self, client):
        """Response body is valid JSON."""
        resp = client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        data = resp.json()
        assert isinstance(data, dict)


class TestCrimeResponseShape:
    def test_response_has_all_top_level_keys(self, client):
        """Response contains heatmap, incidents, and metrics."""
        resp = client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        data = resp.json()
        for key in ["heatmap", "incidents", "metrics"]:
            assert key in data, f"Missing key: {key}"

    def test_heatmap_is_list(self, client):
        resp = client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["heatmap"], list)

    def test_incidents_is_list(self, client):
        resp = client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["incidents"], list)

    def test_metrics_is_dict(self, client):
        resp = client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["metrics"], dict)


class TestCrimeDataTypes:
    def test_heatmap_point_has_fields(self, client):
        """Each heatmap point has lat, lon, intensity."""
        resp = client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        points = resp.json()["heatmap"]
        assert len(points) > 0
        for field in ["lat", "lon", "intensity"]:
            assert field in points[0]

    def test_heatmap_intensity_is_float(self, client):
        resp = client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        point = resp.json()["heatmap"][0]
        assert isinstance(point["intensity"], (int, float))

    def test_incident_has_required_fields(self, client):
        """Each incident has id, incident_type, category, date, lat, lon."""
        resp = client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        incidents = resp.json()["incidents"]
        assert len(incidents) > 0
        for field in ["id", "incident_type", "category", "date", "lat", "lon"]:
            assert field in incidents[0], f"Missing incident field: {field}"

    def test_metrics_has_required_fields(self, client):
        """Metrics has total_incidents_1mi, incidents_per_1000_people, crime_z_score, trend."""
        resp = client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        metrics = resp.json()["metrics"]
        for field in [
            "total_incidents_1mi",
            "incidents_per_1000_people",
            "crime_z_score",
            "trend",
        ]:
            assert field in metrics, f"Missing metrics field: {field}"

    def test_total_incidents_is_int(self, client):
        resp = client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["metrics"]["total_incidents_1mi"], int)

    def test_trend_is_string(self, client):
        resp = client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["metrics"]["trend"], str)


class TestCrimeMissingParams:
    def test_missing_all_params_returns_422(self, client):
        resp = client.get("/api/crime")
        assert resp.status_code == 422

    def test_missing_lat_returns_422(self, client):
        resp = client.get("/api/crime", params={"lon": -78.78})
        assert resp.status_code == 422

    def test_missing_lon_returns_422(self, client):
        resp = client.get("/api/crime", params={"lat": 35.79})
        assert resp.status_code == 422


class TestCrimeParamValidation:
    def test_lat_out_of_range_returns_422(self, client):
        resp = client.get("/api/crime", params={"lat": 91.0, "lon": -78.78})
        assert resp.status_code == 422

    def test_lat_below_range_returns_422(self, client):
        resp = client.get("/api/crime", params={"lat": -91.0, "lon": -78.78})
        assert resp.status_code == 422

    def test_lon_out_of_range_returns_422(self, client):
        resp = client.get("/api/crime", params={"lat": 35.79, "lon": 181.0})
        assert resp.status_code == 422

    def test_lon_below_range_returns_422(self, client):
        resp = client.get("/api/crime", params={"lat": 35.79, "lon": -181.0})
        assert resp.status_code == 422

    def test_radius_zero_returns_422(self, client):
        """radius_miles=0 should fail (gt=0 constraint)."""
        resp = client.get(
            "/api/crime",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 0},
        )
        assert resp.status_code == 422

    def test_radius_negative_returns_422(self, client):
        resp = client.get(
            "/api/crime",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": -1},
        )
        assert resp.status_code == 422

    def test_radius_too_large_returns_422(self, client):
        """radius_miles > 10 should fail (le=10 constraint)."""
        resp = client.get(
            "/api/crime",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 11},
        )
        assert resp.status_code == 422


class TestCrimeDefaultRadius:
    def test_default_radius_works(self, client):
        """Omitting radius_miles uses default and returns 200."""
        resp = client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_explicit_radius_works(self, client):
        """Providing explicit radius_miles returns 200."""
        resp = client.get(
            "/api/crime",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 5.0},
        )
        assert resp.status_code == 200


class TestCrimeRealisticData:
    def test_heatmap_has_many_points(self, client):
        """Heatmap should have a reasonable number of points."""
        resp = client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert len(resp.json()["heatmap"]) >= 10

    def test_incidents_has_multiple_entries(self, client):
        resp = client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert len(resp.json()["incidents"]) >= 5

    def test_intensity_in_valid_range(self, client):
        """Heatmap intensity values should be between 0 and 1."""
        resp = client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        for point in resp.json()["heatmap"]:
            assert 0.0 <= point["intensity"] <= 1.0

    def test_total_incidents_positive(self, client):
        resp = client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        assert resp.json()["metrics"]["total_incidents_1mi"] > 0

    def test_incidents_have_varied_categories(self, client):
        """Incidents should span multiple categories."""
        resp = client.get("/api/crime", params={"lat": 35.79, "lon": -78.78})
        categories = {i["category"] for i in resp.json()["incidents"]}
        assert len(categories) >= 2

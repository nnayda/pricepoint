"""Tests for the utilities endpoint."""


class TestUtilitiesReturns200:
    def test_returns_200_with_valid_params(self, client):
        """GET /api/utilities with valid params returns 200."""
        resp = client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_response_is_json(self, client):
        resp = client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        data = resp.json()
        assert isinstance(data, dict)


class TestUtilitiesResponseShape:
    def test_response_has_features_and_metrics(self, client):
        """Response contains 'features' and 'metrics' keys."""
        resp = client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        data = resp.json()
        assert "features" in data
        assert "metrics" in data

    def test_features_is_list(self, client):
        resp = client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["features"], list)

    def test_metrics_is_dict(self, client):
        resp = client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["metrics"], dict)


class TestUtilitiesDataTypes:
    def test_feature_has_required_fields(self, client):
        """Each feature has id, name, feature_type, lat, lon, distance_miles."""
        resp = client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        features = resp.json()["features"]
        assert len(features) > 0
        for field in ["id", "name", "feature_type", "lat", "lon", "distance_miles"]:
            assert field in features[0], f"Missing feature field: {field}"

    def test_feature_id_is_string(self, client):
        resp = client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        feature = resp.json()["features"][0]
        assert isinstance(feature["id"], str)

    def test_feature_name_is_string(self, client):
        resp = client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        feature = resp.json()["features"][0]
        assert isinstance(feature["name"], str)

    def test_feature_type_is_string(self, client):
        resp = client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        feature = resp.json()["features"][0]
        assert isinstance(feature["feature_type"], str)

    def test_distance_is_number(self, client):
        resp = client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        feature = resp.json()["features"][0]
        assert isinstance(feature["distance_miles"], (int, float))

    def test_metrics_has_required_fields(self, client):
        resp = client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        metrics = resp.json()["metrics"]
        for field in [
            "nearest_highway_miles",
            "nearest_railroad_miles",
            "nearest_powerline_miles",
            "nuisance_score",
        ]:
            assert field in metrics, f"Missing metrics field: {field}"

    def test_nuisance_score_is_number(self, client):
        resp = client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["metrics"]["nuisance_score"], (int, float))

    def test_nearest_highway_is_number(self, client):
        resp = client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["metrics"]["nearest_highway_miles"], (int, float))


class TestUtilitiesMissingParams:
    def test_missing_all_params_returns_422(self, client):
        resp = client.get("/api/utilities")
        assert resp.status_code == 422

    def test_missing_lat_returns_422(self, client):
        resp = client.get("/api/utilities", params={"lon": -78.78})
        assert resp.status_code == 422

    def test_missing_lon_returns_422(self, client):
        resp = client.get("/api/utilities", params={"lat": 35.79})
        assert resp.status_code == 422


class TestUtilitiesParamValidation:
    def test_lat_out_of_range_returns_422(self, client):
        resp = client.get("/api/utilities", params={"lat": 91.0, "lon": -78.78})
        assert resp.status_code == 422

    def test_lon_out_of_range_returns_422(self, client):
        resp = client.get("/api/utilities", params={"lat": 35.79, "lon": 181.0})
        assert resp.status_code == 422

    def test_radius_zero_returns_422(self, client):
        resp = client.get(
            "/api/utilities",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 0},
        )
        assert resp.status_code == 422

    def test_radius_negative_returns_422(self, client):
        resp = client.get(
            "/api/utilities",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": -1},
        )
        assert resp.status_code == 422

    def test_radius_too_large_returns_422(self, client):
        resp = client.get(
            "/api/utilities",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 11},
        )
        assert resp.status_code == 422


class TestUtilitiesDefaultRadius:
    def test_default_radius_works(self, client):
        resp = client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_explicit_radius_works(self, client):
        resp = client.get(
            "/api/utilities",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 5.0},
        )
        assert resp.status_code == 200


class TestUtilitiesRealisticData:
    def test_has_multiple_features(self, client):
        resp = client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        assert len(resp.json()["features"]) >= 3

    def test_features_have_varied_types(self, client):
        """Features should include different utility types."""
        resp = client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        types = {f["feature_type"] for f in resp.json()["features"]}
        assert len(types) >= 2

    def test_distances_are_positive(self, client):
        resp = client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        for feature in resp.json()["features"]:
            assert feature["distance_miles"] > 0

    def test_nearest_distances_are_positive(self, client):
        resp = client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        metrics = resp.json()["metrics"]
        assert metrics["nearest_highway_miles"] > 0
        assert metrics["nearest_railroad_miles"] > 0
        assert metrics["nearest_powerline_miles"] > 0

    def test_nuisance_score_is_positive(self, client):
        resp = client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        assert resp.json()["metrics"]["nuisance_score"] > 0

"""Tests for the greenspace endpoint."""


class TestGreenspaceReturns200:
    def test_returns_200_with_valid_params(self, client):
        """GET /api/greenspace with valid params returns 200."""
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_response_is_json(self, client):
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        data = resp.json()
        assert isinstance(data, dict)


class TestGreenspaceResponseShape:
    def test_response_has_features_and_metrics(self, client):
        """Response contains 'features' and 'metrics' keys."""
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        data = resp.json()
        assert "features" in data
        assert "metrics" in data

    def test_features_is_list(self, client):
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["features"], list)

    def test_metrics_is_dict(self, client):
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["metrics"], dict)


class TestGreenspaceDataTypes:
    def test_feature_has_required_fields(self, client):
        """Each feature has id, name, feature_type, lat, lon, distance_miles."""
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        features = resp.json()["features"]
        assert len(features) > 0
        for field in ["id", "name", "feature_type", "lat", "lon", "distance_miles"]:
            assert field in features[0], f"Missing feature field: {field}"

    def test_feature_id_is_string(self, client):
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        feature = resp.json()["features"][0]
        assert isinstance(feature["id"], str)

    def test_feature_type_is_string(self, client):
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        feature = resp.json()["features"][0]
        assert isinstance(feature["feature_type"], str)

    def test_acreage_is_number_or_null(self, client):
        """Acreage may be null (for trails) or a number."""
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        for feature in resp.json()["features"]:
            assert feature.get("acreage") is None or isinstance(feature["acreage"], (int, float))

    def test_metrics_has_required_fields(self, client):
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        metrics = resp.json()["metrics"]
        for field in [
            "parks_within_1mi",
            "nearest_park_miles",
            "total_green_acres_1mi",
            "greenspace_z_score",
        ]:
            assert field in metrics, f"Missing metrics field: {field}"

    def test_parks_within_1mi_is_int(self, client):
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["metrics"]["parks_within_1mi"], int)

    def test_z_score_is_float(self, client):
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["metrics"]["greenspace_z_score"], (int, float))


class TestGreenspaceMissingParams:
    def test_missing_all_params_returns_422(self, client):
        resp = client.get("/api/greenspace")
        assert resp.status_code == 422

    def test_missing_lat_returns_422(self, client):
        resp = client.get("/api/greenspace", params={"lon": -78.78})
        assert resp.status_code == 422

    def test_missing_lon_returns_422(self, client):
        resp = client.get("/api/greenspace", params={"lat": 35.79})
        assert resp.status_code == 422


class TestGreenspaceParamValidation:
    def test_lat_out_of_range_returns_422(self, client):
        resp = client.get("/api/greenspace", params={"lat": 91.0, "lon": -78.78})
        assert resp.status_code == 422

    def test_lon_out_of_range_returns_422(self, client):
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": 181.0})
        assert resp.status_code == 422

    def test_radius_zero_returns_422(self, client):
        resp = client.get(
            "/api/greenspace",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 0},
        )
        assert resp.status_code == 422

    def test_radius_negative_returns_422(self, client):
        resp = client.get(
            "/api/greenspace",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": -1},
        )
        assert resp.status_code == 422

    def test_radius_too_large_returns_422(self, client):
        resp = client.get(
            "/api/greenspace",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 11},
        )
        assert resp.status_code == 422


class TestGreenspaceDefaultRadius:
    def test_default_radius_works(self, client):
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_explicit_radius_works(self, client):
        resp = client.get(
            "/api/greenspace",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 5.0},
        )
        assert resp.status_code == 200


class TestGreenspaceRealisticData:
    def test_has_multiple_features(self, client):
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert len(resp.json()["features"]) >= 3

    def test_features_have_varied_types(self, client):
        """Features should include parks and trails."""
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        types = {f["feature_type"] for f in resp.json()["features"]}
        assert len(types) >= 2

    def test_distances_are_positive(self, client):
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        for feature in resp.json()["features"]:
            assert feature["distance_miles"] > 0

    def test_parks_within_1mi_is_positive(self, client):
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert resp.json()["metrics"]["parks_within_1mi"] > 0

    def test_nearest_park_miles_is_positive(self, client):
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert resp.json()["metrics"]["nearest_park_miles"] > 0

    def test_total_green_acres_is_positive(self, client):
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert resp.json()["metrics"]["total_green_acres_1mi"] > 0

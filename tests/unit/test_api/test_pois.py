"""Tests for the points of interest endpoint."""


class TestPoisReturns200:
    def test_returns_200_with_valid_params(self, client):
        """GET /api/pois with valid params returns 200."""
        resp = client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_response_is_json(self, client):
        resp = client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        data = resp.json()
        assert isinstance(data, dict)


class TestPoisResponseShape:
    def test_response_has_pois_key(self, client):
        """Response contains the 'pois' key."""
        resp = client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        assert "pois" in resp.json()

    def test_pois_is_list(self, client):
        resp = client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["pois"], list)


class TestPoisDataTypes:
    def test_poi_has_required_fields(self, client):
        """Each POI has id, name, category, lat, lon, distance_miles, drive_minutes."""
        resp = client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        pois = resp.json()["pois"]
        assert len(pois) > 0
        for field in [
            "id",
            "name",
            "category",
            "lat",
            "lon",
            "distance_miles",
            "drive_minutes",
        ]:
            assert field in pois[0], f"Missing POI field: {field}"

    def test_poi_id_is_string(self, client):
        resp = client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        poi = resp.json()["pois"][0]
        assert isinstance(poi["id"], str)

    def test_poi_name_is_string(self, client):
        resp = client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        poi = resp.json()["pois"][0]
        assert isinstance(poi["name"], str)

    def test_poi_category_is_string(self, client):
        resp = client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        poi = resp.json()["pois"][0]
        assert isinstance(poi["category"], str)

    def test_poi_distance_is_number(self, client):
        resp = client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        poi = resp.json()["pois"][0]
        assert isinstance(poi["distance_miles"], (int, float))

    def test_poi_drive_minutes_is_int(self, client):
        resp = client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        poi = resp.json()["pois"][0]
        assert isinstance(poi["drive_minutes"], int)


class TestPoisMissingParams:
    def test_missing_all_params_returns_422(self, client):
        resp = client.get("/api/pois")
        assert resp.status_code == 422

    def test_missing_lat_returns_422(self, client):
        resp = client.get("/api/pois", params={"lon": -78.78})
        assert resp.status_code == 422

    def test_missing_lon_returns_422(self, client):
        resp = client.get("/api/pois", params={"lat": 35.79})
        assert resp.status_code == 422


class TestPoisParamValidation:
    def test_lat_out_of_range_returns_422(self, client):
        resp = client.get("/api/pois", params={"lat": 91.0, "lon": -78.78})
        assert resp.status_code == 422

    def test_lon_out_of_range_returns_422(self, client):
        resp = client.get("/api/pois", params={"lat": 35.79, "lon": 181.0})
        assert resp.status_code == 422

    def test_radius_zero_returns_422(self, client):
        resp = client.get(
            "/api/pois",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 0},
        )
        assert resp.status_code == 422

    def test_radius_negative_returns_422(self, client):
        resp = client.get(
            "/api/pois",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": -1},
        )
        assert resp.status_code == 422

    def test_radius_too_large_returns_422(self, client):
        resp = client.get(
            "/api/pois",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 11},
        )
        assert resp.status_code == 422


class TestPoisDefaultRadius:
    def test_default_radius_works(self, client):
        """Omitting radius_miles uses default and returns 200."""
        resp = client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_explicit_radius_works(self, client):
        resp = client.get(
            "/api/pois",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 5.0},
        )
        assert resp.status_code == 200


class TestPoisRealisticData:
    def test_has_multiple_pois(self, client):
        resp = client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        assert len(resp.json()["pois"]) >= 5

    def test_pois_have_varied_categories(self, client):
        """POIs should span multiple categories."""
        resp = client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        categories = {p["category"] for p in resp.json()["pois"]}
        assert len(categories) >= 3

    def test_distances_are_positive(self, client):
        resp = client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        for poi in resp.json()["pois"]:
            assert poi["distance_miles"] > 0

    def test_drive_minutes_are_positive(self, client):
        resp = client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        for poi in resp.json()["pois"]:
            assert poi["drive_minutes"] > 0

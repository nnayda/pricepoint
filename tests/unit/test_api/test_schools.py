"""Tests for the schools/nearby endpoint."""

from unittest.mock import MagicMock


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
        """Returns empty wrapper when no schools are in the DB."""
        resp = client.get(
            "/api/schools/nearby",
            params={"lat": 35.79, "lon": -78.78},
        )
        assert resp.status_code == 200
        assert resp.json() == {"schools": [], "school_districts": []}


class TestSchoolsNearbyWithData:
    def _make_school(
        self,
        school_id=1,
        name="Test Elementary",
        lat=35.79,
        lon=-78.78,
        rating=8.0,
        district_id=None,
        pct_frl_eligible=None,
    ):
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
        school.rating = rating
        school.grades = "K-5"
        school.enrollment = 500
        school.student_teacher_ratio = 15.0
        school.location = MagicMock()  # non-None geometry
        school.district_id = district_id
        school.pct_frl_eligible = pct_frl_eligible
        return school

    def test_returns_schools_with_correct_fields(self, app):
        """Nearby schools are returned with all expected fields."""
        from fastapi.testclient import TestClient

        from pricepoint.api.dependencies import get_db

        mock_db = MagicMock()
        school = self._make_school(pct_frl_eligible=42.5)

        # Call order:
        # 1: spatial school query (includes lat/lon columns)
        # 2: geo lookup (school_district_geoid) → None
        # 3: district DWithin query → empty
        # 4: property lookup → None
        call_count = 0

        def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()

            if call_count == 1:
                # Spatial school query (school, distance_m, lat, lon)
                result.all.return_value = [(school, 1609.0, 35.79, -78.78)]
                return result
            elif call_count == 2:
                # Geo lookup — no precomputed data
                result.scalar_one_or_none.return_value = None
                return result
            elif call_count == 3:
                # District DWithin query — no districts found
                result.all.return_value = []
                return result
            else:
                # Property lookup
                result.scalar_one_or_none.return_value = None
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
        assert data["school_districts"] == []
        assert len(data["schools"]) == 1

        s = data["schools"][0]
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
        assert s["pct_frl_eligible"] == 42.5
        assert s["in_district"] is False

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

        # Call order:
        # 1: spatial school query (includes lat/lon columns)
        # 2: geo lookup (school_district_geoid) → None
        # 3: district DWithin query → empty
        # 4: property lookup → prop
        # 5: PropertySchool linkage query
        call_count = 0

        def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()

            if call_count == 1:
                # Spatial school query (school, distance_m, lat, lon)
                result.all.return_value = [(school, 1609.0, 35.79, -78.78)]
                return result
            elif call_count == 2:
                # Geo lookup — no precomputed data
                result.scalar_one_or_none.return_value = None
                return result
            elif call_count == 3:
                # District DWithin query — empty
                result.all.return_value = []
                return result
            elif call_count == 4:
                # Property lookup
                result.scalar_one_or_none.return_value = prop
                return result
            else:
                # PropertySchool linkage query
                result.scalars.return_value.all.return_value = [link]
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
        assert len(data["schools"]) == 1

        s = data["schools"][0]
        assert s["assigned"] is True
        assert s["distance_miles"] == 0.8  # Uses linkage distance
        assert s["drive_minutes"] == 3
        assert s["walk_minutes"] == 16

        app.dependency_overrides.clear()

    def test_null_rating_returned_as_none(self, app):
        """School with no rating returns null in response."""
        from fastapi.testclient import TestClient

        from pricepoint.api.dependencies import get_db

        mock_db = MagicMock()
        school = self._make_school(rating=None)

        call_count = 0

        def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()

            if call_count == 1:
                result.all.return_value = [(school, 1609.0, 35.79, -78.78)]
                return result
            elif call_count == 2:
                result.scalar_one_or_none.return_value = None
                return result
            elif call_count == 3:
                result.all.return_value = []
                return result
            else:
                result.scalar_one_or_none.return_value = None
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
        s = resp.json()["schools"][0]
        assert s["rating"] is None

        app.dependency_overrides.clear()

    def test_school_districts_returned_with_geojson(self, app):
        """District boundaries are returned when property is near districts."""
        import json

        from fastapi.testclient import TestClient

        from pricepoint.api.dependencies import get_db

        mock_db = MagicMock()
        school = self._make_school(district_id=10)

        home_district = MagicMock()
        home_district.id = 10
        home_district.name = "Wake County Schools"
        home_district.geoid = "3700390"
        home_district.district_type = "unified"
        home_district.geom = MagicMock()
        home_district.intptlat = "35.790000"
        home_district.intptlon = "-78.780000"

        neighbor_district = MagicMock()
        neighbor_district.id = 20
        neighbor_district.name = "Durham Public Schools"
        neighbor_district.geoid = "3701170"
        neighbor_district.district_type = "unified"
        neighbor_district.geom = MagicMock()
        neighbor_district.intptlat = "36.000000"
        neighbor_district.intptlon = "-78.900000"

        home_geojson = {"type": "MultiPolygon", "coordinates": [[[[0, 0], [1, 0], [1, 1], [0, 0]]]]}
        neighbor_geojson = {
            "type": "MultiPolygon",
            "coordinates": [[[[1, 0], [2, 0], [2, 1], [1, 0]]]],
        }

        call_count = 0

        def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()

            if call_count == 1:
                result.all.return_value = [(school, 1609.0, 35.79, -78.78)]
                return result
            elif call_count == 2:
                result.scalar_one_or_none.return_value = None
                return result
            elif call_count == 3:
                result.all.return_value = [
                    (home_district, True, json.dumps(home_geojson)),
                    (neighbor_district, False, json.dumps(neighbor_geojson)),
                ]
                return result
            else:
                result.scalar_one_or_none.return_value = None
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
        districts = data["school_districts"]
        assert len(districts) == 2

        home = next(d for d in districts if d["is_home"])
        assert home["name"] == "Wake County Schools"
        assert home["geoid"] == "3700390"
        assert home["district_type"] == "unified"
        assert home["geojson"]["type"] == "MultiPolygon"
        assert home["label_lat"] == 35.79
        assert home["label_lon"] == -78.78

        neighbor = next(d for d in districts if not d["is_home"])
        assert neighbor["name"] == "Durham Public Schools"
        assert neighbor["district_type"] == "unified"
        assert neighbor["geojson"]["type"] == "MultiPolygon"

        app.dependency_overrides.clear()

    def test_district_type_returned_for_each_district(self, app):
        """Each district includes its district_type (elementary/secondary/unified)."""
        import json

        from fastapi.testclient import TestClient

        from pricepoint.api.dependencies import get_db

        mock_db = MagicMock()
        school = self._make_school()

        elem_district = MagicMock()
        elem_district.id = 10
        elem_district.name = "Elem District"
        elem_district.geoid = "3700001"
        elem_district.district_type = "elementary"
        elem_district.geom = MagicMock()
        elem_district.intptlat = "35.79"
        elem_district.intptlon = "-78.78"

        sec_district = MagicMock()
        sec_district.id = 20
        sec_district.name = "Secondary District"
        sec_district.geoid = "3700002"
        sec_district.district_type = "secondary"
        sec_district.geom = MagicMock()
        sec_district.intptlat = "36.0"
        sec_district.intptlon = "-78.9"

        geojson = {"type": "MultiPolygon", "coordinates": []}
        call_count = 0

        def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()

            if call_count == 1:
                result.all.return_value = [(school, 1609.0, 35.79, -78.78)]
                return result
            elif call_count == 2:
                result.scalar_one_or_none.return_value = None
                return result
            elif call_count == 3:
                result.all.return_value = [
                    (elem_district, True, json.dumps(geojson)),
                    (sec_district, False, json.dumps(geojson)),
                ]
                return result
            else:
                result.scalar_one_or_none.return_value = None
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
        districts = resp.json()["school_districts"]
        assert len(districts) == 2

        by_type = {d["district_type"]: d for d in districts}
        assert "elementary" in by_type
        assert "secondary" in by_type
        assert by_type["elementary"]["name"] == "Elem District"
        assert by_type["secondary"]["name"] == "Secondary District"

        app.dependency_overrides.clear()

    def test_in_district_flag(self, app):
        """School with matching district_id gets in_district=true."""
        import json

        from fastapi.testclient import TestClient

        from pricepoint.api.dependencies import get_db

        mock_db = MagicMock()
        school = self._make_school(district_id=10)

        district = MagicMock()
        district.id = 10
        district.name = "Wake County Schools"
        district.geoid = "3700390"
        district.district_type = "unified"
        district.geom = MagicMock()
        district.intptlat = "35.790000"
        district.intptlon = "-78.780000"

        geojson_dict = {"type": "MultiPolygon", "coordinates": []}

        call_count = 0

        def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()

            if call_count == 1:
                result.all.return_value = [(school, 1609.0, 35.79, -78.78)]
                return result
            elif call_count == 2:
                result.scalar_one_or_none.return_value = None
                return result
            elif call_count == 3:
                result.all.return_value = [
                    (district, True, json.dumps(geojson_dict)),
                ]
                return result
            else:
                result.scalar_one_or_none.return_value = None
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
        s = resp.json()["schools"][0]
        assert s["in_district"] is True

        app.dependency_overrides.clear()

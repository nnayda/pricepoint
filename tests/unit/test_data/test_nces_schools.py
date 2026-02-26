"""Tests for the NCES school data collector."""

from unittest.mock import MagicMock, patch

import pytest

from pricepoint.data.geospatial.nces_schools import (
    _fetch_nces_page,
    _fips_to_state_abbr,
    _parse_nces_record,
    fetch_nces_schools,
    verify_nces_schools,
)


# ---------------------------------------------------------------------------
# TestParseNcesRecord
# ---------------------------------------------------------------------------
class TestParseNcesRecord:
    def _make_feature(self, **overrides):
        attrs = {
            "NCESSCH": "370001234567",
            "SCH_NAME": "Test Elementary School",
            "LSTREET1": "100 Main St",
            "LCITY": "Raleigh",
            "LSTATE": "NC",
            "LZIP": "27601",
            "LATCOD": 35.7796,
            "LONCOD": -78.6382,
            "SCHOOL_TYPE_TEXT": "Regular",
            "SCHOOL_LEVEL": "Elementary",
            "GSLO": "PK",
            "GSHI": "05",
            "STATUS": "1",
            "PHONE": "9195551234",
            "TOTAL": 500,
            "MEMBER": 480,
            "CHARTER_TEXT": "No",
            "VIRTUAL": "N",
            "FTE": 35.0,
            "STUTERATIO": 14.3,
            "FRELCH": 100,
            "REDLCH": 50,
            "TOTFRL": 150,
            "LEA_NAME": "Wake County Schools",
            "LEAID": "3700001",
            "ULOCALE": "21",
        }
        attrs.update(overrides)
        return {"attributes": attrs}

    def test_core_fields_extracted(self):
        feature = self._make_feature()
        result = _parse_nces_record(feature)
        assert result["nces_id"] == "370001234567"
        assert result["name"] == "Test Elementary School"
        assert result["street"] == "100 Main St"
        assert result["city"] == "Raleigh"
        assert result["state"] == "NC"
        assert result["zip_code"] == "27601"
        assert result["school_type"] == "Regular"
        assert result["school_level"] == "Elementary"
        assert result["grades_low"] == "PK"
        assert result["grades_high"] == "05"

    def test_lat_lon_parsed(self):
        feature = self._make_feature()
        result = _parse_nces_record(feature)
        assert result["lat"] == pytest.approx(35.7796)
        assert result["lon"] == pytest.approx(-78.6382)

    def test_extras_packed(self):
        feature = self._make_feature()
        result = _parse_nces_record(feature)
        assert result["extras"] is not None
        assert result["extras"]["PHONE"] == "9195551234"
        assert result["extras"]["TOTAL"] == 500
        assert result["extras"]["LEA_NAME"] == "Wake County Schools"

    def test_missing_lat_lon(self):
        feature = self._make_feature(LATCOD=None, LONCOD=None)
        result = _parse_nces_record(feature)
        assert result["lat"] is None
        assert result["lon"] is None

    def test_missing_extras_returns_none(self):
        """When all extra fields are None, extras should be None."""
        feature = self._make_feature()
        # Set all extra fields to None
        for field in [
            "PHONE",
            "TOTAL",
            "MEMBER",
            "CHARTER_TEXT",
            "VIRTUAL",
            "FTE",
            "STUTERATIO",
            "FRELCH",
            "REDLCH",
            "TOTFRL",
            "LEA_NAME",
            "LEAID",
            "ULOCALE",
        ]:
            feature["attributes"][field] = None
        result = _parse_nces_record(feature)
        assert result["extras"] is None

    def test_empty_nces_id(self):
        feature = self._make_feature(NCESSCH=None)
        result = _parse_nces_record(feature)
        assert result["nces_id"] == ""


# ---------------------------------------------------------------------------
# TestFipsToStateAbbr
# ---------------------------------------------------------------------------
class TestFipsToStateAbbr:
    def test_known_fips(self):
        assert _fips_to_state_abbr("37") == "NC"
        assert _fips_to_state_abbr("06") == "CA"
        assert _fips_to_state_abbr("48") == "TX"

    def test_unknown_fips_raises(self):
        with pytest.raises(ValueError, match="Unknown state FIPS code"):
            _fips_to_state_abbr("99")


# ---------------------------------------------------------------------------
# TestFetchNcesPage
# ---------------------------------------------------------------------------
class TestFetchNcesPage:
    @patch("pricepoint.data.geospatial.nces_schools.httpx.get")
    def test_returns_features(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "features": [
                {"attributes": {"NCESSCH": "001"}},
                {"attributes": {"NCESSCH": "002"}},
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = _fetch_nces_page("https://example.com/MapServer/0", 0)
        assert len(result) == 2

    @patch("pricepoint.data.geospatial.nces_schools.httpx.get")
    def test_empty_response(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"features": []}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = _fetch_nces_page("https://example.com/MapServer/0", 0)
        assert result == []

    @patch("pricepoint.data.geospatial.nces_schools.httpx.get")
    def test_pagination_offset_passed(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"features": []}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        _fetch_nces_page("https://example.com/MapServer/0", 2000)
        call_args = mock_get.call_args
        assert call_args[1]["params"]["resultOffset"] == "2000"

    @patch("pricepoint.data.geospatial.nces_schools.httpx.get")
    def test_all_us_schools_by_default(self, mock_get):
        """Without state_abbr, query fetches all active US schools."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"features": []}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        _fetch_nces_page("https://example.com/MapServer/0", 0)
        call_args = mock_get.call_args
        assert call_args[1]["params"]["where"] == "STATUS='1'"

    @patch("pricepoint.data.geospatial.nces_schools.httpx.get")
    def test_state_abbr_filter(self, mock_get):
        """When state_abbr is provided, query filters by state."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"features": []}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        _fetch_nces_page("https://example.com/MapServer/0", 0, state_abbr="NC")
        call_args = mock_get.call_args
        assert "STABR='NC'" in call_args[1]["params"]["where"]


# ---------------------------------------------------------------------------
# TestFetchNcesSchools (upsert-based)
# ---------------------------------------------------------------------------
class TestFetchNcesSchools:
    @patch("pricepoint.data.geospatial.nces_schools.pg_insert")
    @patch("pricepoint.data.geospatial.nces_schools.SessionLocal")
    @patch("pricepoint.data.geospatial.nces_schools._fetch_nces_page")
    @patch("pricepoint.data.geospatial.nces_schools.from_shape")
    def test_loads_records_via_upsert(
        self, mock_from_shape, mock_fetch_page, mock_session_cls, mock_pg_insert
    ):
        mock_from_shape.return_value = "mocked_geom"
        session = MagicMock()
        mock_session_cls.return_value = session

        # Set up pg_insert chain
        mock_stmt = MagicMock()
        mock_pg_insert.return_value.values.return_value = mock_stmt
        mock_stmt.on_conflict_do_update.return_value = mock_stmt

        # Mock delete result for stale cleanup
        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 0
        session.execute.return_value = mock_delete_result

        # Return one page of 2 records, then empty page
        mock_fetch_page.side_effect = [
            [
                {
                    "attributes": {
                        "NCESSCH": "001",
                        "SCH_NAME": "School A",
                        "LSTREET1": "100 Main",
                        "LCITY": "Raleigh",
                        "LSTATE": "NC",
                        "LZIP": "27601",
                        "LATCOD": 35.78,
                        "LONCOD": -78.64,
                        "SCHOOL_TYPE_TEXT": "Regular",
                        "SCHOOL_LEVEL": "Elementary",
                        "GSLO": "PK",
                        "GSHI": "05",
                        "STATUS": "1",
                    }
                },
                {
                    "attributes": {
                        "NCESSCH": "002",
                        "SCH_NAME": "School B",
                        "LSTREET1": "200 Oak",
                        "LCITY": "Cary",
                        "LSTATE": "NC",
                        "LZIP": "27513",
                        "LATCOD": 35.79,
                        "LONCOD": -78.78,
                        "SCHOOL_TYPE_TEXT": "Regular",
                        "SCHOOL_LEVEL": "Middle",
                        "GSLO": "06",
                        "GSHI": "08",
                        "STATUS": "1",
                    }
                },
            ],
            [],
        ]

        count = fetch_nces_schools()
        assert count == 2

        # Verify pg_insert was called with NcesSchool model
        from pricepoint.db.models import NcesSchool

        mock_pg_insert.assert_called_with(NcesSchool)

        # Verify on_conflict_do_update was called with nces_id index
        conflict_call = mock_stmt.on_conflict_do_update.call_args
        assert conflict_call[1]["index_elements"] == ["nces_id"]

        # Verify commit was called (upsert page + stale cleanup)
        session.commit.assert_called()

    @patch("pricepoint.data.geospatial.nces_schools.SessionLocal")
    @patch("pricepoint.data.geospatial.nces_schools._fetch_nces_page")
    def test_zero_records_no_stale_cleanup(self, mock_fetch_page, mock_session_cls):
        session = MagicMock()
        mock_session_cls.return_value = session

        mock_fetch_page.return_value = []

        count = fetch_nces_schools()
        assert count == 0
        # With zero records, no delete for stale cleanup should happen
        session.execute.assert_not_called()

    @patch("pricepoint.data.geospatial.nces_schools.pg_insert")
    @patch("pricepoint.data.geospatial.nces_schools.SessionLocal")
    @patch("pricepoint.data.geospatial.nces_schools._fetch_nces_page")
    def test_skips_empty_nces_id(self, mock_fetch_page, mock_session_cls, mock_pg_insert):
        session = MagicMock()
        mock_session_cls.return_value = session

        mock_fetch_page.side_effect = [
            [{"attributes": {"NCESSCH": None, "SCH_NAME": "Bad School"}}],
            [],
        ]

        count = fetch_nces_schools()
        assert count == 0
        # pg_insert should not be called since the only record was skipped
        mock_pg_insert.assert_not_called()

    @patch("pricepoint.data.geospatial.nces_schools.SessionLocal")
    @patch("pricepoint.data.geospatial.nces_schools._fetch_nces_page")
    def test_rollback_on_error(self, mock_fetch_page, mock_session_cls):
        session = MagicMock()
        mock_session_cls.return_value = session

        mock_fetch_page.side_effect = RuntimeError("API error")

        with pytest.raises(RuntimeError, match="API error"):
            fetch_nces_schools()

        session.rollback.assert_called_once()
        session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.nces_schools.pg_insert")
    @patch("pricepoint.data.geospatial.nces_schools.SessionLocal")
    @patch("pricepoint.data.geospatial.nces_schools._fetch_nces_page")
    @patch("pricepoint.data.geospatial.nces_schools.from_shape")
    def test_stale_rows_deleted_after_upsert(
        self, mock_from_shape, mock_fetch_page, mock_session_cls, mock_pg_insert
    ):
        """After upserting, rows with loaded_at < run_started are removed."""
        mock_from_shape.return_value = "mocked_geom"
        session = MagicMock()
        mock_session_cls.return_value = session

        mock_stmt = MagicMock()
        mock_pg_insert.return_value.values.return_value = mock_stmt
        mock_stmt.on_conflict_do_update.return_value = mock_stmt

        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 3
        session.execute.return_value = mock_delete_result

        mock_fetch_page.side_effect = [
            [
                {
                    "attributes": {
                        "NCESSCH": "001",
                        "SCH_NAME": "School A",
                        "LSTREET1": "100 Main",
                        "LCITY": "Raleigh",
                        "LSTATE": "NC",
                        "LZIP": "27601",
                        "LATCOD": 35.78,
                        "LONCOD": -78.64,
                        "SCHOOL_TYPE_TEXT": "Regular",
                        "SCHOOL_LEVEL": "Elementary",
                        "GSLO": "PK",
                        "GSHI": "05",
                        "STATUS": "1",
                    }
                },
            ],
            [],
        ]

        count = fetch_nces_schools()
        assert count == 1

        # Should have 2 commits: upsert page + stale cleanup
        assert session.commit.call_count == 2

        # The second execute call should be the stale DELETE
        # (first is the upsert stmt)
        assert session.execute.call_count == 2


# ---------------------------------------------------------------------------
# TestVerifyNcesSchools
# ---------------------------------------------------------------------------
class TestVerifyNcesSchools:
    @patch("pricepoint.data.geospatial.nces_schools.SessionLocal")
    def test_returns_count(self, mock_session_cls):
        session = MagicMock()
        mock_session_cls.return_value = session
        session.execute.return_value.scalar.return_value = 500

        count = verify_nces_schools()
        assert count == 500

    @patch("pricepoint.data.geospatial.nces_schools.SessionLocal")
    def test_raises_on_empty(self, mock_session_cls):
        session = MagicMock()
        mock_session_cls.return_value = session
        session.execute.return_value.scalar.return_value = 0

        with pytest.raises(RuntimeError, match="No records found"):
            verify_nces_schools()

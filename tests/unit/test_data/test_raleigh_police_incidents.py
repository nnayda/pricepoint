"""Unit tests for the Raleigh police incidents data collector."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from pricepoint.data.geospatial.police_incidents import (
    _map_raleigh_record,
    _parse_arcgis_timestamp,
    _query_arcgis_features,
    fetch_daily_raleigh_police_incidents,
    fetch_raleigh_police_incidents,
)

# -- Fixtures / helpers -------------------------------------------------------


def _make_feature(**overrides: object) -> dict:
    """Return a minimal ArcGIS feature dict with optional attribute overrides."""
    attrs: dict[str, object] = {
        "OBJECTID": 1,
        "GlobalID": "abc-123",
        "case_number": "24-001001",
        "crime_category": "LARCENY",
        "crime_code": "23F",
        "crime_description": "THEFT FROM MOTOR VEHICLE",
        "crime_type": "PROPERTY",
        "reported_block_address": "100 FAYETTEVILLE ST",
        "city_of_incident": "RALEIGH",
        "city": "RALEIGH",
        "district": "DOWNTOWN",
        "reported_date": 1705312800000,  # 2024-01-15T10:00:00 UTC
        "reported_year": 2024,
        "reported_month": 1,
        "reported_day": 15,
        "reported_hour": 10,
        "reported_dayofwk": "MONDAY",
        "latitude": 35.780,
        "longitude": -78.639,
        "agency": "RPD",
        "updated_date": 1705399200000,  # 2024-01-16T10:00:00 UTC
    }
    attrs.update(overrides)
    return {"attributes": attrs}


def _make_arcgis_response(features: list[dict], *, exceeded: bool = False) -> MagicMock:
    """Create a mock httpx response with ArcGIS JSON structure."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "features": features,
        "exceededTransferLimit": exceeded,
    }
    return resp


def _mock_session():
    """Create a mock SQLAlchemy session with the needed methods."""
    session = MagicMock()
    session.execute = MagicMock()
    session.commit = MagicMock()
    session.add_all = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session


# -- Tests: _parse_arcgis_timestamp -------------------------------------------


class TestParseArcgisTimestamp:
    def test_valid_epoch_ms(self):
        result = _parse_arcgis_timestamp(1705312800000)
        expected = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        assert result == expected

    def test_none_returns_none(self):
        assert _parse_arcgis_timestamp(None) is None

    def test_invalid_string_returns_none(self):
        assert _parse_arcgis_timestamp("not-a-timestamp") is None

    def test_zero_epoch(self):
        result = _parse_arcgis_timestamp(0)
        assert result == datetime(1970, 1, 1, tzinfo=UTC)


# -- Tests: _map_raleigh_record -----------------------------------------------


class TestMapRaleighRecord:
    def test_all_fields_mapped(self):
        feature = _make_feature()
        obj = _map_raleigh_record(feature)

        assert obj.objectid == "1"
        assert obj.global_id == "abc-123"
        assert obj.case_number == "24-001001"
        assert obj.crime_category == "LARCENY"
        assert obj.crime_code == "23F"
        assert obj.crime_description == "THEFT FROM MOTOR VEHICLE"
        assert obj.crime_type == "PROPERTY"
        assert obj.reported_block_address == "100 FAYETTEVILLE ST"
        assert obj.city_of_incident == "RALEIGH"
        assert obj.city == "RALEIGH"
        assert obj.district == "DOWNTOWN"
        assert obj.reported_date == datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        assert obj.reported_year == 2024
        assert obj.reported_month == 1
        assert obj.reported_day == 15
        assert obj.reported_hour == 10
        assert obj.reported_dayofwk == "MONDAY"
        assert obj.latitude == pytest.approx(35.780)
        assert obj.longitude == pytest.approx(-78.639)
        assert obj.agency == "RPD"
        assert obj.updated_date == datetime(2024, 1, 16, 10, 0, 0, tzinfo=UTC)
        assert obj.location is not None

    def test_missing_coordinates_null_geometry(self):
        feature = _make_feature(latitude=None, longitude=None)
        obj = _map_raleigh_record(feature)
        assert obj.location is None
        assert obj.latitude is None
        assert obj.longitude is None

    def test_none_objectid(self):
        feature = _make_feature(OBJECTID=None)
        obj = _map_raleigh_record(feature)
        assert obj.objectid is None


# -- Tests: _query_arcgis_features --------------------------------------------


class TestQueryArcgisFeatures:
    @patch("pricepoint.data.geospatial.police_incidents.httpx")
    def test_returns_features(self, mock_httpx):
        features = [_make_feature()]
        mock_httpx.get.return_value = _make_arcgis_response(features)

        result = _query_arcgis_features(
            "https://example.com/arcgis/rest/services",
            "Police_Incidents",
            offset=0,
            count=5000,
        )

        assert len(result) == 1
        mock_httpx.get.assert_called_once()
        call_args = mock_httpx.get.call_args
        assert "Police_Incidents/FeatureServer/0/query" in call_args[0][0]

    @patch("pricepoint.data.geospatial.police_incidents.httpx")
    def test_empty_response(self, mock_httpx):
        mock_httpx.get.return_value = _make_arcgis_response([])

        result = _query_arcgis_features(
            "https://example.com/arcgis/rest/services",
            "Police_Incidents",
        )

        assert result == []

    @patch("pricepoint.data.geospatial.police_incidents.httpx")
    def test_offset_passed_in_params(self, mock_httpx):
        mock_httpx.get.return_value = _make_arcgis_response([])

        _query_arcgis_features(
            "https://example.com/arcgis/rest/services",
            "Police_Incidents",
            offset=5000,
            count=5000,
        )

        call_args = mock_httpx.get.call_args
        params = call_args[1]["params"]
        assert params["resultOffset"] == 5000
        assert params["resultRecordCount"] == 5000


# -- Tests: fetch_raleigh_police_incidents ------------------------------------


class TestFetchRaleighPoliceIncidents:
    @patch("pricepoint.data.geospatial.police_incidents._query_arcgis_features")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_full_refresh_truncates(self, mock_session_cls, mock_query):
        session = _mock_session()
        mock_session_cls.return_value = session
        mock_query.return_value = []

        fetch_raleigh_police_incidents(full_refresh=True)

        # Delete should have been called (truncate)
        session.execute.assert_called_once()
        session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.police_incidents._query_arcgis_features")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_single_page_fetch(self, mock_session_cls, mock_query):
        session = _mock_session()
        mock_session_cls.return_value = session

        features = [_make_feature(case_number="R1"), _make_feature(case_number="R2")]
        mock_query.return_value = features

        fetch_raleigh_police_incidents(full_refresh=False)

        session.add_all.assert_called_once()
        added = session.add_all.call_args[0][0]
        assert len(added) == 2
        assert added[0].case_number == "R1"
        assert added[1].case_number == "R2"

    @patch("pricepoint.data.geospatial.police_incidents._query_arcgis_features")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_multi_page_pagination(self, mock_session_cls, mock_query):
        session = _mock_session()
        mock_session_cls.return_value = session

        # First call returns a full page (5000), second returns partial (100)
        page1 = [_make_feature(OBJECTID=i) for i in range(5000)]
        page2 = [_make_feature(OBJECTID=i) for i in range(5000, 5100)]
        mock_query.side_effect = [page1, page2]

        fetch_raleigh_police_incidents(full_refresh=False)

        assert mock_query.call_count == 2
        assert session.add_all.call_count == 2

    @patch("pricepoint.data.geospatial.police_incidents._query_arcgis_features")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_empty_dataset(self, mock_session_cls, mock_query):
        session = _mock_session()
        mock_session_cls.return_value = session
        mock_query.return_value = []

        fetch_raleigh_police_incidents(full_refresh=False)

        session.add_all.assert_not_called()
        session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.police_incidents._query_arcgis_features")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_exception_rolls_back(self, mock_session_cls, mock_query):
        session = _mock_session()
        mock_session_cls.return_value = session
        mock_query.side_effect = Exception("network error")

        with pytest.raises(Exception, match="network error"):
            fetch_raleigh_police_incidents(full_refresh=False)

        session.rollback.assert_called_once()
        session.close.assert_called_once()


# -- Tests: fetch_daily_raleigh_police_incidents ------------------------------


class TestFetchDailyRaleighPoliceIncidents:
    @patch("pricepoint.data.geospatial.police_incidents._query_arcgis_features")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_deduplication_skips_existing(self, mock_session_cls, mock_query):
        session = _mock_session()
        mock_session_cls.return_value = session

        features = [
            _make_feature(case_number="EXISTING-001"),
            _make_feature(case_number="NEW-001"),
        ]
        mock_query.return_value = features

        # Mock the existing case_number query
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = ["EXISTING-001"]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute.return_value = mock_result

        fetch_daily_raleigh_police_incidents()

        session.add_all.assert_called_once()
        added = session.add_all.call_args[0][0]
        assert len(added) == 1
        assert added[0].case_number == "NEW-001"

    @patch("pricepoint.data.geospatial.police_incidents._query_arcgis_features")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_inserts_new_records(self, mock_session_cls, mock_query):
        session = _mock_session()
        mock_session_cls.return_value = session

        features = [_make_feature(case_number="NEW-001")]
        mock_query.return_value = features

        # No existing records
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute.return_value = mock_result

        fetch_daily_raleigh_police_incidents()

        session.add_all.assert_called_once()
        added = session.add_all.call_args[0][0]
        assert len(added) == 1

    @patch("pricepoint.data.geospatial.police_incidents._query_arcgis_features")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_empty_daily_dataset(self, mock_session_cls, mock_query):
        session = _mock_session()
        mock_session_cls.return_value = session
        mock_query.return_value = []

        fetch_daily_raleigh_police_incidents()

        session.add_all.assert_not_called()
        session.close.assert_called_once()

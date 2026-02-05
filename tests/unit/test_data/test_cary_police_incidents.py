"""Unit tests for the Cary police incidents data collector."""

import logging
from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx

from pricepoint.data.geospatial.police_incidents import (
    _build_geometry,
    _map_record,
    fetch_cary_police_incidents,
)

# -- Fixtures / helpers -------------------------------------------------------

_API_URL = "https://data.townofcary.org/api/explore/v2.1/catalog/datasets/cpd-incidents/records"


def _make_record(**overrides):
    """Return a minimal API record dict with optional overrides."""
    base = {
        "id": "24001001",
        "incident_number": "24001001",
        "crime_category": "LARCENY",
        "crime_type": "LARCENY - FROM MV",
        "ucr": "230",
        "map_reference": "P083",
        "date_from": "2024-01-15T10:00:00+00:00",
        "from_time": "10:00:00",
        "date_to": "2024-01-15T12:00:00+00:00",
        "to_time": "12:00:00",
        "crimeday": "MONDAY",
        "geocode": "KILDAIRE FARM RD",
        "location_category": "RESIDENTIAL",
        "district": "CPDS",
        "beat_number": 50,
        "neighborhd_id": "0024",
        "apartment_complex": None,
        "residential_subdivision": "LOCHMERE",
        "subdivisn_id": "0173",
        "activity_date": "2024-01-15",
        "phxrecordstatus": "Active",
        "phxcommunity": "Yes",
        "phxstatus": "Active",
        "record": 114109,
        "offensecategory": "Larceny/Theft",
        "violentproperty": "Part I",
        "timeframe": "Day",
        "domestic": "N",
        "total_incidents": 1,
        "year": "2024",
        "older_than_five_years_from_now": "False",
        "chrgcnt": None,
        "lon": -78.748,
        "lat": 35.766,
        "location": {"lon": -78.748, "lat": 35.766},
    }
    base.update(overrides)
    return base


def _mock_session():
    """Create a mock SQLAlchemy session with the needed methods."""
    session = MagicMock()
    session.execute = MagicMock()
    session.commit = MagicMock()
    session.add_all = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session


# -- Tests: _build_geometry / _map_record --------------------------------------


class TestBuildGeometry:
    def test_valid_coordinates(self):
        geom = _build_geometry(-78.748, 35.766)
        assert geom is not None

    def test_none_lon(self):
        assert _build_geometry(None, 35.766) is None

    def test_none_lat(self):
        assert _build_geometry(-78.748, None) is None

    def test_invalid_string_logs_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            result = _build_geometry("bad", "coords")
        assert result is None
        assert "Invalid coordinates" in caplog.text


class TestMapRecord:
    def test_all_api_fields_mapped(self):
        record = _make_record()
        obj = _map_record(record)

        assert obj.api_id == "24001001"
        assert obj.incident_number == "24001001"
        assert obj.crime_category == "LARCENY"
        assert obj.crime_type == "LARCENY - FROM MV"
        assert obj.ucr == "230"
        assert obj.map_reference == "P083"
        assert obj.date_from == "2024-01-15T10:00:00+00:00"
        assert obj.from_time == "10:00:00"
        assert obj.date_to == "2024-01-15T12:00:00+00:00"
        assert obj.to_time == "12:00:00"
        assert obj.crimeday == "MONDAY"
        assert obj.geocode == "KILDAIRE FARM RD"
        assert obj.location_category == "RESIDENTIAL"
        assert obj.district == "CPDS"
        assert obj.beat_number == "50"
        assert obj.neighborhd_id == "0024"
        assert obj.apartment_complex is None
        assert obj.residential_subdivision == "LOCHMERE"
        assert obj.subdivisn_id == "0173"
        assert obj.activity_date == "2024-01-15"
        assert obj.phxrecordstatus == "Active"
        assert obj.phxcommunity == "Yes"
        assert obj.phxstatus == "Active"
        assert obj.record == "114109"
        assert obj.offensecategory == "Larceny/Theft"
        assert obj.violentproperty == "Part I"
        assert obj.timeframe == "Day"
        assert obj.domestic == "N"
        assert obj.total_incidents == "1"
        assert obj.year == "2024"
        assert obj.older_than_five_years_from_now == "False"
        assert obj.chrgcnt is None
        assert obj.lon == pytest.approx(-78.748)
        assert obj.lat == pytest.approx(35.766)
        assert obj.location is not None

    def test_missing_coordinates_sets_null_geometry(self):
        record = _make_record(lon=None, lat=None)
        obj = _map_record(record)
        assert obj.location is None
        assert obj.lon is None
        assert obj.lat is None


# -- Tests: fetch_cary_police_incidents ----------------------------------------


class TestFetchCaryPoliceIncidents:
    @respx.mock
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_single_page_fetch(self, mock_session_cls):
        session = _mock_session()
        mock_session_cls.return_value = session

        records = [_make_record(id="R1"), _make_record(id="R2")]
        respx.get(_API_URL).mock(
            return_value=httpx.Response(200, json={"total_count": 2, "results": records})
        )

        fetch_cary_police_incidents(full_refresh=True)

        # Should have called delete (truncate) then add_all
        session.execute.assert_called_once()
        session.add_all.assert_called_once()
        added = session.add_all.call_args[0][0]
        assert len(added) == 2
        assert added[0].api_id == "R1"
        assert added[1].api_id == "R2"
        session.close.assert_called_once()

    @respx.mock
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_pagination_multiple_pages(self, mock_session_cls):
        session = _mock_session()
        mock_session_cls.return_value = session

        page1 = [_make_record(id=f"R{i}") for i in range(100)]
        page2 = [_make_record(id=f"R{i}") for i in range(100, 150)]

        route = respx.get(_API_URL)
        route.side_effect = [
            httpx.Response(200, json={"total_count": 150, "results": page1}),
            httpx.Response(200, json={"total_count": 150, "results": page2}),
        ]

        fetch_cary_police_incidents(full_refresh=True)

        assert session.add_all.call_count == 2
        first_batch = session.add_all.call_args_list[0][0][0]
        second_batch = session.add_all.call_args_list[1][0][0]
        assert len(first_batch) == 100
        assert len(second_batch) == 50

    @respx.mock
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_empty_dataset(self, mock_session_cls):
        session = _mock_session()
        mock_session_cls.return_value = session

        respx.get(_API_URL).mock(
            return_value=httpx.Response(200, json={"total_count": 0, "results": []})
        )

        fetch_cary_police_incidents(full_refresh=True)

        session.add_all.assert_not_called()
        session.close.assert_called_once()

    @respx.mock
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_http_error_raises_and_rolls_back(self, mock_session_cls):
        session = _mock_session()
        mock_session_cls.return_value = session

        respx.get(_API_URL).mock(return_value=httpx.Response(500))

        with pytest.raises(httpx.HTTPStatusError):
            fetch_cary_police_incidents(full_refresh=True)

        session.rollback.assert_called_once()
        session.close.assert_called_once()

    @respx.mock
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_full_refresh_false_skips_truncate(self, mock_session_cls):
        session = _mock_session()
        mock_session_cls.return_value = session

        respx.get(_API_URL).mock(
            return_value=httpx.Response(200, json={"total_count": 1, "results": [_make_record()]})
        )

        fetch_cary_police_incidents(full_refresh=False)

        # session.execute should NOT have been called (no delete)
        session.execute.assert_not_called()
        session.add_all.assert_called_once()

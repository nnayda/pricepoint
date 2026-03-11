"""Unit tests for the Cary police incidents data collector."""

import logging
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from pricepoint.data.geospatial.police_incidents import (
    _build_geometry,
    _geocode_street_names,
    _map_record,
    fetch_cary_police_incidents,
)

# -- Fixtures / helpers -------------------------------------------------------


def _make_record(**overrides: str) -> dict[str, str]:
    """Return a minimal record dict with optional overrides."""
    base: dict[str, str] = {
        "incident_number": "24001001",
        "crime_type": "LARCENY - FROM MV",
        "ucr": "230",
        "map_reference": "P083",
        "date_from": "2024-01-15T10:00:00+00:00",
        "from_time": "10:00:00",
        "date_to": "2024-01-15T12:00:00+00:00",
        "to_time": "12:00:00",
        "crimeday": "MONDAY",
        "geocode": "KILDAIRE FARM RD",
        "district": "CPDS",
        "beat_number": "050",
        "neighborhd_id": "0024",
        "apartment_complex": "",
        "residential_subdivision": "LOCHMERE",
        "subdivisn_id": "0173",
        "activity_date": "2024-01-15",
        "phxrecordstatus": "Active",
        "phxcommunity": "Yes",
        "phxstatus": "Active",
        "year": "2024",
        "chrgcnt": "",
        "lon": "-78.748",
        "lat": "35.766",
    }
    base.update(overrides)
    return base


def _make_dataframe(*rows: dict[str, str]) -> pd.DataFrame:
    """Build a DataFrame from record dicts, using current API column names."""
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(list(rows))


def _mock_session():
    """Create a mock SQLAlchemy session with the needed methods."""
    session = MagicMock()
    session.execute = MagicMock()
    session.commit = MagicMock()
    session.add_all = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session


def _fake_geocode(query, limit=1, **kwargs):
    """Fake geocoder that returns coords for known Cary streets."""
    if "KILDAIRE FARM RD" in query:
        return [{"lat": 35.766, "lon": -78.748, "display_name": "Kildaire Farm Rd"}]
    if "NC 55 HWY" in query:
        return [{"lat": 35.7601, "lon": -78.7675, "display_name": "NC 55 Hwy"}]
    return []


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
    def test_all_csv_fields_mapped(self):
        record = _make_record()
        obj = _map_record(record)

        assert obj.incident_number == "24001001"
        assert obj.crime_type == "LARCENY - FROM MV"
        assert obj.ucr == "230"
        assert obj.map_reference == "P083"
        assert obj.date_from == "2024-01-15T10:00:00+00:00"
        assert obj.from_time == "10:00:00"
        assert obj.date_to == "2024-01-15T12:00:00+00:00"
        assert obj.to_time == "12:00:00"
        assert obj.crimeday == "MONDAY"
        assert obj.geocode == "KILDAIRE FARM RD"
        assert obj.district == "CPDS"
        assert obj.beat_number == "050"
        assert obj.neighborhd_id == "0024"
        assert obj.apartment_complex is None
        assert obj.residential_subdivision == "LOCHMERE"
        assert obj.subdivisn_id == "0173"
        assert obj.activity_date == "2024-01-15"
        assert obj.phxrecordstatus == "Active"
        assert obj.phxcommunity == "Yes"
        assert obj.phxstatus == "Active"
        assert obj.year == "2024"
        assert obj.chrgcnt is None
        assert obj.lon == pytest.approx(-78.748)
        assert obj.lat == pytest.approx(35.766)
        assert obj.location is not None

    def test_missing_coordinates_sets_null_geometry(self):
        record = _make_record(lon="", lat="")
        obj = _map_record(record)
        assert obj.location is None
        assert obj.lon is None
        assert obj.lat is None

    def test_fields_not_in_api_are_null(self):
        """Columns removed from the API schema remain nullable in the model."""
        record = _make_record()
        # These fields no longer come from the API
        for key in (
            "crime_category",
            "location_category",
            "record",
            "offensecategory",
            "violentproperty",
            "timeframe",
            "domestic",
            "total_incidents",
            "older_than_five_years_from_now",
        ):
            record.pop(key, None)

        obj = _map_record(record)
        assert obj.crime_category is None
        assert obj.location_category is None
        assert obj.record is None
        assert obj.offensecategory is None
        assert obj.violentproperty is None
        assert obj.timeframe is None
        assert obj.domestic is None
        assert obj.total_incidents is None
        assert obj.older_than_five_years_from_now is None
        # Other fields still work
        assert obj.crime_type == "LARCENY - FROM MV"
        assert obj.lon == pytest.approx(-78.748)


# -- Tests: _geocode_street_names ----------------------------------------------


class TestGeocodeStreetNames:
    def test_geocodes_unique_streets(self):
        result = _geocode_street_names(
            {"KILDAIRE FARM RD", "NC 55 HWY"},
            geocode_fn=_fake_geocode,
        )
        assert "KILDAIRE FARM RD" in result
        assert result["KILDAIRE FARM RD"] == pytest.approx((-78.748, 35.766))
        assert "NC 55 HWY" in result

    def test_missing_street_omitted(self):
        result = _geocode_street_names(
            {"UNKNOWN STREET XYZ"},
            geocode_fn=_fake_geocode,
        )
        assert "UNKNOWN STREET XYZ" not in result

    def test_empty_set(self):
        result = _geocode_street_names(set(), geocode_fn=_fake_geocode)
        assert result == {}

    def test_geocode_exception_handled(self, caplog):
        def _failing_geocode(*args, **kwargs):
            raise RuntimeError("service down")

        with caplog.at_level(logging.WARNING):
            result = _geocode_street_names({"MAIN ST"}, geocode_fn=_failing_geocode)
        assert result == {}
        assert "Geocode failed" in caplog.text

    def test_retries_on_empty_result_then_succeeds(self):
        """Geocoder should retry when first attempt returns empty (e.g. timeout)."""
        call_count = 0

        def _flaky_geocode(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return []  # first attempt fails (simulates timeout → empty)
            return _fake_geocode(*args, **kwargs)

        result = _geocode_street_names({"KILDAIRE FARM RD"}, geocode_fn=_flaky_geocode)
        assert "KILDAIRE FARM RD" in result
        assert call_count == 2

    def test_retries_on_exception_then_succeeds(self):
        """Geocoder should retry on exception and succeed on next attempt."""
        call_count = 0

        def _flaky_geocode(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("timeout")
            return _fake_geocode(*args, **kwargs)

        result = _geocode_street_names({"KILDAIRE FARM RD"}, geocode_fn=_flaky_geocode)
        assert "KILDAIRE FARM RD" in result
        assert call_count == 2


# -- Tests: fetch_cary_police_incidents ----------------------------------------


class TestFetchCaryPoliceIncidents:
    @patch("pricepoint.data.geospatial.police_incidents.ODSClient")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_single_page_fetch_with_geocoding(self, mock_session_cls, mock_ods_cls):
        session = _mock_session()
        mock_session_cls.return_value = session

        # Simulate ODS data — column names as returned by odsclient
        row1 = {
            "Incident Number": "R1",
            "Geo Code": "KILDAIRE FARM RD",
            "Crime Type": "LARCENY",
        }
        row2 = {
            "Incident Number": "R2",
            "Geo Code": "NC 55 HWY",
            "Crime Type": "FRAUD",
        }
        df = pd.DataFrame([row1, row2])
        mock_client = MagicMock()
        mock_client.get_whole_dataframe.return_value = df
        mock_ods_cls.return_value = mock_client

        fetch_cary_police_incidents(full_refresh=True, geocode_fn=_fake_geocode)

        mock_ods_cls.assert_called_once_with(base_url="https://data.townofcary.org/")
        mock_client.get_whole_dataframe.assert_called_once_with(dataset_id="cpd-incidents")
        session.execute.assert_called_once()
        session.add_all.assert_called_once()
        added = session.add_all.call_args[0][0]
        assert len(added) == 2
        # Coordinates should be populated from geocoder
        assert added[0].lon == pytest.approx(-78.748)
        assert added[0].lat == pytest.approx(35.766)
        assert added[0].location is not None
        assert added[1].lon is not None
        assert added[1].location is not None
        session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.police_incidents.ODSClient")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_records_without_geocode_have_null_coords(self, mock_session_cls, mock_ods_cls):
        session = _mock_session()
        mock_session_cls.return_value = session

        row = {"Incident Number": "R1", "Geo Code": "", "Crime Type": "LARCENY"}
        df = pd.DataFrame([row])
        mock_client = MagicMock()
        mock_client.get_whole_dataframe.return_value = df
        mock_ods_cls.return_value = mock_client

        fetch_cary_police_incidents(full_refresh=True, geocode_fn=_fake_geocode)

        added = session.add_all.call_args[0][0]
        assert len(added) == 1
        assert added[0].lon is None
        assert added[0].lat is None
        assert added[0].location is None

    @patch("pricepoint.data.geospatial.police_incidents.ODSClient")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_unknown_street_has_null_coords(self, mock_session_cls, mock_ods_cls):
        session = _mock_session()
        mock_session_cls.return_value = session

        row = {"Incident Number": "R1", "Geo Code": "UNKNOWN STREET XYZ", "Crime Type": "LARCENY"}
        df = pd.DataFrame([row])
        mock_client = MagicMock()
        mock_client.get_whole_dataframe.return_value = df
        mock_ods_cls.return_value = mock_client

        fetch_cary_police_incidents(full_refresh=True, geocode_fn=_fake_geocode)

        added = session.add_all.call_args[0][0]
        assert added[0].lon is None
        assert added[0].location is None

    @patch("pricepoint.data.geospatial.police_incidents.ODSClient")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_empty_dataset(self, mock_session_cls, mock_ods_cls):
        session = _mock_session()
        mock_session_cls.return_value = session

        mock_client = MagicMock()
        mock_client.get_whole_dataframe.return_value = pd.DataFrame()
        mock_ods_cls.return_value = mock_client

        fetch_cary_police_incidents(full_refresh=True, geocode_fn=_fake_geocode)

        session.add_all.assert_not_called()
        session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.police_incidents.ODSClient")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_exception_raises_and_rolls_back(self, mock_session_cls, mock_ods_cls):
        session = _mock_session()
        mock_session_cls.return_value = session

        mock_client = MagicMock()
        mock_client.get_whole_dataframe.side_effect = Exception("network error")
        mock_ods_cls.return_value = mock_client

        with pytest.raises(Exception, match="network error"):
            fetch_cary_police_incidents(full_refresh=True, geocode_fn=_fake_geocode)

        session.rollback.assert_called_once()
        session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.police_incidents.ODSClient")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_full_refresh_false_skips_truncate(self, mock_session_cls, mock_ods_cls):
        session = _mock_session()
        mock_session_cls.return_value = session

        row = {"Incident Number": "R1", "Geo Code": "KILDAIRE FARM RD", "Crime Type": "LARCENY"}
        mock_client = MagicMock()
        mock_client.get_whole_dataframe.return_value = pd.DataFrame([row])
        mock_ods_cls.return_value = mock_client

        fetch_cary_police_incidents(full_refresh=False, geocode_fn=_fake_geocode)

        # session.execute should NOT have been called (no delete)
        session.execute.assert_not_called()
        session.add_all.assert_called_once()

    @patch("pricepoint.data.geospatial.police_incidents.ODSClient")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_deduplicates_geocode_calls(self, mock_session_cls, mock_ods_cls):
        """Same street name should only be geocoded once."""
        session = _mock_session()
        mock_session_cls.return_value = session

        # Two records with the same street
        rows = [
            {"Incident Number": "R1", "Geo Code": "KILDAIRE FARM RD", "Crime Type": "LARCENY"},
            {"Incident Number": "R2", "Geo Code": "KILDAIRE FARM RD", "Crime Type": "FRAUD"},
        ]
        mock_client = MagicMock()
        mock_client.get_whole_dataframe.return_value = pd.DataFrame(rows)
        mock_ods_cls.return_value = mock_client

        call_count = 0

        def _counting_geocode(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return _fake_geocode(*args, **kwargs)

        fetch_cary_police_incidents(full_refresh=True, geocode_fn=_counting_geocode)

        # Only one geocode call for the one unique street
        assert call_count == 1
        added = session.add_all.call_args[0][0]
        assert added[0].lon == pytest.approx(-78.748)
        assert added[1].lon == pytest.approx(-78.748)

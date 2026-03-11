"""Unit tests for the Morrisville police incidents data collector."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from pricepoint.data.geospatial.police_incidents import (
    _map_morrisville_record,
    _parse_area_coords,
    fetch_morrisville_police_incidents,
)

# -- Fixtures / helpers -------------------------------------------------------


def _make_record(**overrides: str) -> dict[str, str]:
    """Return a minimal record dict with optional overrides."""
    base: dict[str, str] = {
        "date_rept": "2024-01-15T10:00:00+00:00",
        "date_occu": "2024-01-15T08:00:00+00:00",
        "dow1": "Monday",
        "monthstamp": "January",
        "yearstamp": "2024",
        "inci_id": "24001001",
        "offense": "LARCENY - FROM MOTOR VEHICLE",
        "street": "TOWN HALL DR",
        "city": "MORRISVILLE",
        "state": "NC",
        "zip": "27560",
        "neighborhd": "",
        "subdivisn": "0009",
        "tract": "P132",
        "zone": "2",
        "district": "MPD1",
        "asst_offcr": "1",
        "area": "35.812711, -78.819843",
    }
    base.update(overrides)
    return base


def _make_dataframe(*rows: dict[str, str]) -> pd.DataFrame:
    """Build a DataFrame from record dicts (short field IDs)."""
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(list(rows))


# Map short field IDs → odsclient display names (what get_whole_dataframe returns)
_DISPLAY_NAMES = {
    "date_rept": "Date Reported",
    "date_occu": "Date Occurred",
    "dow1": "Day of Week",
    "monthstamp": "Month",
    "yearstamp": "Year",
    "inci_id": "Incident ID",
    "offense": "Offense",
    "street": "Street",
    "city": "City",
    "state": "State",
    "zip": "Zip",
    "neighborhd": "Neighborhood",
    "subdivisn": "Subdivision",
    "tract": "Tract",
    "zone": "Zone",
    "district": "District",
    "asst_offcr": "# of Asst Officers",
    "area": "Area",
}


def _make_ods_dataframe(*rows: dict) -> pd.DataFrame:
    """Build a DataFrame with odsclient display-name columns.

    Accepts dicts keyed by short field IDs (same as ``_make_record``) and
    renames columns to match what ``ODSClient.get_whole_dataframe`` returns.
    """
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(list(rows))
    return df.rename(columns=_DISPLAY_NAMES)


def _mock_session():
    """Create a mock SQLAlchemy session with the needed methods."""
    session = MagicMock()
    session.execute = MagicMock()
    session.commit = MagicMock()
    session.add_all = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session


# -- Tests: _parse_area_coords ------------------------------------------------


class TestParseAreaCoords:
    def test_valid_area(self):
        lat, lon = _parse_area_coords("35.812711, -78.819843")
        assert lat == pytest.approx(35.812711)
        assert lon == pytest.approx(-78.819843)

    def test_empty_string(self):
        lat, lon = _parse_area_coords("")
        assert lat is None
        assert lon is None

    def test_none_equivalent(self):
        lat, lon = _parse_area_coords("")
        assert lat is None
        assert lon is None

    def test_invalid_string(self):
        lat, lon = _parse_area_coords("not-coords")
        assert lat is None
        assert lon is None

    def test_single_value(self):
        lat, lon = _parse_area_coords("35.812711")
        assert lat is None
        assert lon is None

    def test_dict_area(self):
        lat, lon = _parse_area_coords({"lat": 35.812711, "lon": -78.819843})
        assert lat == pytest.approx(35.812711)
        assert lon == pytest.approx(-78.819843)

    def test_dict_area_missing_key(self):
        lat, lon = _parse_area_coords({"lat": 35.812711})
        assert lat is None
        assert lon is None

    def test_dict_area_empty(self):
        lat, lon = _parse_area_coords({})
        assert lat is None
        assert lon is None


# -- Tests: _map_morrisville_record -------------------------------------------


class TestMapMorrisvilleRecord:
    def test_all_csv_fields_mapped(self):
        record = _make_record()
        obj = _map_morrisville_record(record)

        assert obj.inci_id == "24001001"
        assert obj.offense == "LARCENY - FROM MOTOR VEHICLE"
        assert obj.date_rept == "2024-01-15T10:00:00+00:00"
        assert obj.date_occu == "2024-01-15T08:00:00+00:00"
        assert obj.dow1 == "Monday"
        assert obj.monthstamp == "January"
        assert obj.yearstamp == "2024"
        assert obj.street == "TOWN HALL DR"
        assert obj.city == "MORRISVILLE"
        assert obj.state == "NC"
        assert obj.zip == "27560"
        assert obj.neighborhd is None  # empty string maps to None
        assert obj.subdivisn == "0009"
        assert obj.tract == "P132"
        assert obj.zone == "2"
        assert obj.district == "MPD1"
        assert obj.asst_offcr == "1"
        assert obj.lat == pytest.approx(35.812711)
        assert obj.lon == pytest.approx(-78.819843)
        assert obj.location is not None

    def test_missing_area_sets_null_geometry(self):
        record = _make_record(area="")
        obj = _map_morrisville_record(record)
        assert obj.location is None
        assert obj.lat is None
        assert obj.lon is None


# -- Tests: fetch_morrisville_police_incidents ---------------------------------


class TestFetchMorrisvillePoliceIncidents:
    @patch("pricepoint.data.geospatial.police_incidents.ODSClient")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_single_page_fetch(self, mock_session_cls, mock_ods_cls):
        session = _mock_session()
        mock_session_cls.return_value = session

        df = _make_ods_dataframe(
            _make_record(inci_id="R1"),
            _make_record(inci_id="R2"),
        )
        mock_client = MagicMock()
        mock_client.get_whole_dataframe.return_value = df
        mock_ods_cls.return_value = mock_client

        fetch_morrisville_police_incidents(full_refresh=True)

        mock_ods_cls.assert_called_once_with(base_url="https://opendata.townofmorrisville.org/")
        mock_client.get_whole_dataframe.assert_called_once_with(dataset_id="pd_incident_report")
        session.execute.assert_called_once()
        session.add_all.assert_called_once()
        added = session.add_all.call_args[0][0]
        assert len(added) == 2
        assert added[0].inci_id == "R1"
        assert added[1].inci_id == "R2"
        # Verify dates are populated (not None)
        assert added[0].date_rept == "2024-01-15T10:00:00+00:00"
        assert added[0].date_occu == "2024-01-15T08:00:00+00:00"
        session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.police_incidents.ODSClient")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_empty_dataset(self, mock_session_cls, mock_ods_cls):
        session = _mock_session()
        mock_session_cls.return_value = session

        mock_client = MagicMock()
        mock_client.get_whole_dataframe.return_value = pd.DataFrame()
        mock_ods_cls.return_value = mock_client

        fetch_morrisville_police_incidents(full_refresh=True)

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
            fetch_morrisville_police_incidents(full_refresh=True)

        session.rollback.assert_called_once()
        session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.police_incidents.ODSClient")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_timestamp_dates_converted_to_iso_strings(self, mock_session_cls, mock_ods_cls):
        """Verify that pandas Timestamp date values are stored as ISO strings."""
        session = _mock_session()
        mock_session_cls.return_value = session

        # Build a DataFrame with actual Timestamp columns (as odsclient returns)
        record = _make_record()
        record["date_rept"] = pd.Timestamp("2024-01-15T10:00:00+00:00")
        record["date_occu"] = pd.Timestamp("2024-01-15T08:00:00+00:00")
        df = _make_ods_dataframe(record)

        mock_client = MagicMock()
        mock_client.get_whole_dataframe.return_value = df
        mock_ods_cls.return_value = mock_client

        fetch_morrisville_police_incidents(full_refresh=True)

        added = session.add_all.call_args[0][0]
        assert added[0].date_rept == "2024-01-15T10:00:00+00:00"
        assert added[0].date_occu == "2024-01-15T08:00:00+00:00"

    @patch("pricepoint.data.geospatial.police_incidents.ODSClient")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_nat_dates_become_null(self, mock_session_cls, mock_ods_cls):
        """Verify that NaT date values are stored as None."""
        session = _mock_session()
        mock_session_cls.return_value = session

        record = _make_record()
        record["date_rept"] = pd.NaT
        record["date_occu"] = pd.NaT
        df = _make_ods_dataframe(record)

        mock_client = MagicMock()
        mock_client.get_whole_dataframe.return_value = df
        mock_ods_cls.return_value = mock_client

        fetch_morrisville_police_incidents(full_refresh=True)

        added = session.add_all.call_args[0][0]
        assert added[0].date_rept is None
        assert added[0].date_occu is None

    @patch("pricepoint.data.geospatial.police_incidents.ODSClient")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_dict_area_parsed_correctly(self, mock_session_cls, mock_ods_cls):
        """Verify that dict-format area values are parsed for lat/lon."""
        session = _mock_session()
        mock_session_cls.return_value = session

        record = _make_record()
        record["area"] = {"lat": 35.812711, "lon": -78.819843}
        df = _make_ods_dataframe(record)

        mock_client = MagicMock()
        mock_client.get_whole_dataframe.return_value = df
        mock_ods_cls.return_value = mock_client

        fetch_morrisville_police_incidents(full_refresh=True)

        added = session.add_all.call_args[0][0]
        assert added[0].lat == pytest.approx(35.812711)
        assert added[0].lon == pytest.approx(-78.819843)
        assert added[0].location is not None

    @patch("pricepoint.data.geospatial.police_incidents.ODSClient")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_full_refresh_false_skips_truncate(self, mock_session_cls, mock_ods_cls):
        session = _mock_session()
        mock_session_cls.return_value = session

        mock_client = MagicMock()
        mock_client.get_whole_dataframe.return_value = _make_ods_dataframe(_make_record())
        mock_ods_cls.return_value = mock_client

        fetch_morrisville_police_incidents(full_refresh=False)

        session.execute.assert_not_called()
        session.add_all.assert_called_once()

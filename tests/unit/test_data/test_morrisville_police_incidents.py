"""Unit tests for the Morrisville police incidents data collector."""

from unittest.mock import MagicMock, patch

import pytest

from pricepoint.data.geospatial.police_incidents import (
    _map_morrisville_record,
    _parse_area_coords,
    fetch_morrisville_police_incidents,
)

# -- Fixtures / helpers -------------------------------------------------------

_CSV_HEADERS = (
    "date_rept;date_occu;dow1;monthstamp;yearstamp;inci_id;offense;"
    "street;city;state;zip;neighborhd;subdivisn;tract;zone;district;"
    "asst_offcr;area"
)


def _make_csv(*rows: dict[str, str]) -> str:
    """Build a semicolon-delimited CSV string with the standard headers."""
    lines = [_CSV_HEADERS]
    for row in rows:
        fields = _CSV_HEADERS.split(";")
        lines.append(";".join(row.get(f, "") for f in fields))
    return "\n".join(lines)


def _make_record(**overrides: str) -> dict[str, str]:
    """Return a minimal CSV-style record dict with optional overrides."""
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
    @patch("pricepoint.data.geospatial.police_incidents.get_whole_dataset")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_single_page_fetch(self, mock_session_cls, mock_get_dataset):
        session = _mock_session()
        mock_session_cls.return_value = session

        csv_text = _make_csv(
            _make_record(inci_id="R1"),
            _make_record(inci_id="R2"),
        )
        mock_get_dataset.return_value = csv_text

        fetch_morrisville_police_incidents(full_refresh=True)

        mock_get_dataset.assert_called_once_with(
            "pd_incident_report",
            platform_id="opendata.townofmorrisville.org",
        )
        session.execute.assert_called_once()
        session.add_all.assert_called_once()
        added = session.add_all.call_args[0][0]
        assert len(added) == 2
        assert added[0].inci_id == "R1"
        assert added[1].inci_id == "R2"
        session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.police_incidents.get_whole_dataset")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_empty_dataset(self, mock_session_cls, mock_get_dataset):
        session = _mock_session()
        mock_session_cls.return_value = session

        mock_get_dataset.return_value = _make_csv()  # headers only

        fetch_morrisville_police_incidents(full_refresh=True)

        session.add_all.assert_not_called()
        session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.police_incidents.get_whole_dataset")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_exception_raises_and_rolls_back(self, mock_session_cls, mock_get_dataset):
        session = _mock_session()
        mock_session_cls.return_value = session

        mock_get_dataset.side_effect = Exception("network error")

        with pytest.raises(Exception, match="network error"):
            fetch_morrisville_police_incidents(full_refresh=True)

        session.rollback.assert_called_once()
        session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.police_incidents.get_whole_dataset")
    @patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
    def test_full_refresh_false_skips_truncate(self, mock_session_cls, mock_get_dataset):
        session = _mock_session()
        mock_session_cls.return_value = session

        mock_get_dataset.return_value = _make_csv(_make_record())

        fetch_morrisville_police_incidents(full_refresh=False)

        session.execute.assert_not_called()
        session.add_all.assert_called_once()

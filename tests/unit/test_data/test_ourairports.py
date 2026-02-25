"""Tests for OurAirports collector."""

from unittest.mock import MagicMock, patch

import pytest

from pricepoint.data.geospatial.ourairports import (
    fetch_airports,
    parse_airport_row,
    verify_airports,
)

# -- Sample data --------------------------------------------------------------

_FULL_ROW = {
    "id": "3632",
    "ident": "KRDU",
    "type": "large_airport",
    "name": "Raleigh-Durham International Airport",
    "latitude_deg": "35.8776",
    "longitude_deg": "-78.7875",
    "elevation_ft": "435",
    "continent": "NA",
    "iso_country": "US",
    "iso_region": "US-NC",
    "municipality": "Raleigh/Durham",
    "scheduled_service": "yes",
    "icao_code": "KRDU",
    "iata_code": "RDU",
    "gps_code": "KRDU",
    "local_code": "RDU",
    "home_link": "http://www.rdu.com/",
    "wikipedia_link": "https://en.wikipedia.org/wiki/Raleigh-Durham_International_Airport",
    "keywords": "",
}

_MINIMAL_ROW = {
    "id": "99999",
    "ident": "00A",
    "type": "small_airport",
    "name": "Total RF Heliport",
    "latitude_deg": "40.07",
    "longitude_deg": "-74.93",
    "elevation_ft": "",
    "continent": "NA",
    "iso_country": "US",
    "iso_region": "US-PA",
    "municipality": "Bensalem",
    "scheduled_service": "no",
    "icao_code": "",
    "iata_code": "",
    "gps_code": "",
    "local_code": "",
    "home_link": "",
    "wikipedia_link": "",
    "keywords": "",
}


# -- parse_airport_row --------------------------------------------------------


class TestParseAirportRow:
    def test_full_row_parsed(self):
        result = parse_airport_row(_FULL_ROW)
        assert result is not None
        assert result["ident"] == "KRDU"
        assert result["airport_type"] == "large_airport"
        assert result["name"] == "Raleigh-Durham International Airport"
        assert result["elevation_ft"] == 435
        assert result["iso_region"] == "US-NC"
        assert result["municipality"] == "Raleigh/Durham"
        assert result["scheduled_service"] is True
        assert result["iata_code"] == "RDU"
        assert result["home_link"] == "http://www.rdu.com/"
        assert result["wikipedia_link"].startswith("https://en.wikipedia.org/")
        assert result["lat"] == 35.8776
        assert result["lon"] == -78.7875

    def test_minimal_row_parsed(self):
        result = parse_airport_row(_MINIMAL_ROW)
        assert result is not None
        assert result["ident"] == "00A"
        assert result["elevation_ft"] is None
        assert result["scheduled_service"] is False
        assert result["iata_code"] is None
        assert result["home_link"] is None
        assert result["wikipedia_link"] is None

    def test_non_us_filtered_out(self):
        row = {**_FULL_ROW, "iso_country": "CA"}
        assert parse_airport_row(row) is None

    def test_missing_lat_skipped(self):
        row = {**_FULL_ROW, "latitude_deg": ""}
        assert parse_airport_row(row) is None

    def test_missing_lon_skipped(self):
        row = {**_FULL_ROW, "longitude_deg": ""}
        assert parse_airport_row(row) is None

    def test_invalid_lat_skipped(self):
        row = {**_FULL_ROW, "latitude_deg": "not_a_number"}
        assert parse_airport_row(row) is None

    def test_scheduled_service_yes(self):
        result = parse_airport_row({**_FULL_ROW, "scheduled_service": "yes"})
        assert result is not None
        assert result["scheduled_service"] is True

    def test_scheduled_service_no(self):
        result = parse_airport_row({**_FULL_ROW, "scheduled_service": "no"})
        assert result is not None
        assert result["scheduled_service"] is False

    def test_elevation_float_truncated(self):
        row = {**_FULL_ROW, "elevation_ft": "435.6"}
        result = parse_airport_row(row)
        assert result is not None
        assert result["elevation_ft"] == 435


# -- fetch_airports -----------------------------------------------------------


class TestFetchAirports:
    @patch("pricepoint.data.geospatial.ourairports.SessionLocal")
    @patch("pricepoint.data.geospatial.ourairports.httpx.get")
    def test_fetch_downloads_and_upserts(self, mock_get, mock_session_local):
        csv_content = (
            "id,ident,type,name,latitude_deg,longitude_deg,elevation_ft,"
            "continent,iso_country,iso_region,municipality,scheduled_service,"
            "icao_code,iata_code,gps_code,local_code,home_link,wikipedia_link,keywords\n"
            "3632,KRDU,large_airport,Raleigh-Durham International Airport,"
            "35.8776,-78.7875,435,NA,US,US-NC,Raleigh/Durham,yes,"
            "KRDU,RDU,KRDU,RDU,http://www.rdu.com/,https://en.wikipedia.org/wiki/RDU,\n"
            "9999,CYYZ,large_airport,Toronto Pearson,"
            "43.6772,-79.6306,569,NA,CA,CA-ON,Toronto,yes,"
            "CYYZ,YYZ,CYYZ,YYZ,,,\n"
        )
        mock_resp = MagicMock()
        mock_resp.text = csv_content
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        mock_session.execute.return_value = MagicMock(rowcount=0)

        count = fetch_airports()

        assert count == 1  # Only US airport
        mock_get.assert_called_once()
        mock_session.execute.assert_called()

    @patch("pricepoint.data.geospatial.ourairports.SessionLocal")
    @patch("pricepoint.data.geospatial.ourairports.httpx.get")
    def test_fetch_empty_csv(self, mock_get, mock_session_local):
        csv_content = (
            "id,ident,type,name,latitude_deg,longitude_deg,elevation_ft,"
            "continent,iso_country,iso_region,municipality,scheduled_service,"
            "icao_code,iata_code,gps_code,local_code,home_link,wikipedia_link,keywords\n"
        )
        mock_resp = MagicMock()
        mock_resp.text = csv_content
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        count = fetch_airports()

        assert count == 0


# -- verify_airports ----------------------------------------------------------


class TestVerifyAirports:
    @patch("pricepoint.data.geospatial.ourairports.SessionLocal")
    def test_verify_returns_count(self, mock_session_local):
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        mock_session.execute.return_value.scalar.return_value = 42

        count = verify_airports()
        assert count == 42

    @patch("pricepoint.data.geospatial.ourairports.SessionLocal")
    def test_verify_raises_when_empty(self, mock_session_local):
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        mock_session.execute.return_value.scalar.return_value = 0

        with pytest.raises(RuntimeError, match="No records found"):
            verify_airports()

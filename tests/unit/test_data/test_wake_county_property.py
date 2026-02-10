"""Tests for Wake County property data collector."""

import io
import zipfile
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from pricepoint.data.housing.wake_county_property import (
    _csv_float,
    _csv_int,
    _csv_val,
    _discover_zip_url,
    _download_zip,
    _extract_txt_from_zip,
    _map_record,
    _parse_fwf_data,
    fetch_wake_county_property_data,
)


def _make_test_zip(txt_content: str) -> bytes:
    """Create in-memory ZIP file with .txt content.

    Args:
        txt_content: Text file content

    Returns:
        ZIP file as bytes
    """
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("RealEstData.txt", txt_content.encode("latin1"))
    return zip_buf.getvalue()


# -- _download_zip tests -------------------------------------------------------


@patch("pricepoint.data.housing.wake_county_property.httpx.Client")
def test_download_zip_success(mock_client_cls):
    """_download_zip should download and return ZIP bytes."""
    mock_response = MagicMock()
    mock_response.content = b"fake zip content"
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = _download_zip("http://test.url")

    assert result == b"fake zip content"
    mock_client.get.assert_called_once_with("http://test.url")
    mock_response.raise_for_status.assert_called_once()


@patch("pricepoint.data.housing.wake_county_property.httpx.Client")
def test_download_zip_http_error(mock_client_cls):
    """_download_zip should raise on HTTP error."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("404 Not Found")
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_client_cls.return_value.__enter__.return_value = mock_client

    with pytest.raises(Exception, match="404 Not Found"):
        _download_zip("http://test.url")


# -- _discover_zip_url tests ---------------------------------------------------


@patch("pricepoint.data.housing.wake_county_property.httpx.Client")
def test_discover_zip_url_success(mock_client_cls):
    """_discover_zip_url should find the RealEstData ZIP link."""
    mock_response = MagicMock()
    mock_response.text = (
        '<html><body><a href="RealEstData02102026.zip">RealEstData02102026.zip</a></body></html>'
    )
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = _discover_zip_url("https://services.wake.gov/realdata_extracts/")

    assert result == "https://services.wake.gov/realdata_extracts/RealEstData02102026.zip"
    mock_response.raise_for_status.assert_called_once()


@patch("pricepoint.data.housing.wake_county_property.httpx.Client")
def test_discover_zip_url_no_match(mock_client_cls):
    """_discover_zip_url should raise ValueError if no matching link."""
    mock_response = MagicMock()
    mock_response.text = "<html><body>No links here</body></html>"
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_client_cls.return_value.__enter__.return_value = mock_client

    with pytest.raises(ValueError, match="No RealEstData ZIP link found"):
        _discover_zip_url("https://services.wake.gov/realdata_extracts/")


@patch("pricepoint.data.housing.wake_county_property.httpx.Client")
def test_discover_zip_url_http_error(mock_client_cls):
    """_discover_zip_url should raise on HTTP error."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("503 Service Unavailable")
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_client_cls.return_value.__enter__.return_value = mock_client

    with pytest.raises(Exception, match="503 Service Unavailable"):
        _discover_zip_url("https://services.wake.gov/realdata_extracts/")


@patch("pricepoint.data.housing.wake_county_property.httpx.Client")
def test_discover_zip_url_strips_trailing_slash(mock_client_cls):
    """_discover_zip_url should handle base URL with or without trailing slash."""
    mock_response = MagicMock()
    mock_response.text = '<a href="RealEstData01152026.zip">RealEstData01152026.zip</a>'
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = _discover_zip_url("https://services.wake.gov/realdata_extracts")

    assert result == "https://services.wake.gov/realdata_extracts/RealEstData01152026.zip"


# -- _extract_txt_from_zip tests -----------------------------------------------


def test_extract_txt_from_zip_success():
    """_extract_txt_from_zip should extract .txt file from ZIP."""
    test_content = "test line 1\ntest line 2\n"
    zip_bytes = _make_test_zip(test_content)

    result = _extract_txt_from_zip(zip_bytes)

    assert result == test_content


def test_extract_txt_no_txt_file():
    """_extract_txt_from_zip should raise ValueError if no .txt file."""
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("data.csv", "not a txt file")
    zip_bytes = zip_buf.getvalue()

    with pytest.raises(ValueError, match="No .txt file found"):
        _extract_txt_from_zip(zip_bytes)


def test_extract_txt_multiple_txt_files():
    """_extract_txt_from_zip should use first .txt file if multiple exist."""
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("file1.txt", "first file")
        zf.writestr("file2.txt", "second file")
    zip_bytes = zip_buf.getvalue()

    result = _extract_txt_from_zip(zip_bytes)

    assert result == "first file"


# -- _parse_fwf_data tests -----------------------------------------------------


def test_parse_fwf_data():
    """_parse_fwf_data should parse fixed-width format into DataFrame."""
    # Create proper FWF with first 3 columns only for test
    mini_map = {"Owner 1": 35, "Owner 2": 35, "Address 1": 35}
    sample_line = (
        "JONES JOHN DOE                     "
        "SMITH JANE                         "
        "123 MAIN ST                        \n"
    )
    with patch("pricepoint.data.housing.wake_county_property.COLUMN_MAP", mini_map):
        result = _parse_fwf_data(sample_line)

    assert len(result) == 1
    assert "Owner 1" in result.columns
    assert "Owner 2" in result.columns
    assert "Address 1" in result.columns


# -- _csv_val tests ------------------------------------------------------------


def test_csv_val_none():
    """_csv_val should return None for NaN."""
    assert _csv_val(pd.NA) is None
    assert _csv_val(float("nan")) is None


def test_csv_val_empty_string():
    """_csv_val should return None for empty string."""
    assert _csv_val("") is None
    assert _csv_val("   ") is None


def test_csv_val_valid_string():
    """_csv_val should return stripped string."""
    assert _csv_val("  hello  ") == "hello"
    assert _csv_val("test") == "test"


# -- _csv_int tests ------------------------------------------------------------


def test_csv_int_none():
    """_csv_int should return None for NaN."""
    assert _csv_int(pd.NA) is None
    assert _csv_int(float("nan")) is None


def test_csv_int_zero():
    """_csv_int should return None for zero."""
    assert _csv_int("0") is None
    assert _csv_int(0) is None


def test_csv_int_valid():
    """_csv_int should parse valid integers."""
    assert _csv_int("1234") == 1234
    assert _csv_int("1234.0") == 1234  # Handle float strings
    assert _csv_int(1234) == 1234


def test_csv_int_invalid():
    """_csv_int should return None for invalid values."""
    assert _csv_int("abc") is None
    assert _csv_int("") is None


# -- _csv_float tests ----------------------------------------------------------


def test_csv_float_none():
    """_csv_float should return None for NaN."""
    assert _csv_float(pd.NA) is None
    assert _csv_float(float("nan")) is None


def test_csv_float_zero():
    """_csv_float should return None for zero."""
    assert _csv_float("0") is None
    assert _csv_float("0.0") is None
    assert _csv_float(0.0) is None


def test_csv_float_valid():
    """_csv_float should parse valid floats."""
    assert _csv_float("123.45") == 123.45
    assert _csv_float("100") == 100.0
    assert _csv_float(99.99) == 99.99


def test_csv_float_invalid():
    """_csv_float should return None for invalid values."""
    assert _csv_float("abc") is None
    assert _csv_float("") is None


# -- _map_record tests ---------------------------------------------------------


def test_map_record():
    """_map_record should map DataFrame row to model."""
    from pricepoint.data.housing.wake_county_property import COLUMN_MAP

    # Create mock row with all columns
    row_data = {col: None for col in COLUMN_MAP}
    row_data.update(
        {
            "Owner 1": "JOHN DOE",
            "Owner 2": "JANE DOE",
            "REID": "0000101",
            "Year Built": "1985",
            "Heated Area": "2500.0",
            "Total Sale Price": "350000.0",
        }
    )
    row = pd.Series(row_data)

    result = _map_record(row)

    assert result.owner_1 == "JOHN DOE"
    assert result.owner_2 == "JANE DOE"
    assert result.reid == "0000101"
    assert result.year_built == 1985
    assert result.heated_area == 2500.0
    assert result.total_sale_price == 350000.0


# -- fetch_wake_county_property_data tests -------------------------------------


@patch("pricepoint.data.housing.wake_county_property.SessionLocal")
@patch("pricepoint.data.housing.wake_county_property._download_zip")
@patch("pricepoint.data.housing.wake_county_property._discover_zip_url")
@patch("pricepoint.data.housing.wake_county_property.get_settings")
def test_fetch_truncates_and_loads(mock_settings, mock_discover, mock_download, mock_session_cls):
    """fetch_wake_county_property_data should truncate and load records."""
    # Setup mocks
    mock_settings.return_value = MagicMock(
        wake_county_extracts_url="https://services.wake.gov/realdata_extracts/"
    )
    mock_discover.return_value = (
        "https://services.wake.gov/realdata_extracts/RealEstData02102026.zip"
    )
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    # Create minimal FWF data (3 records with simplified columns)
    from pricepoint.data.housing.wake_county_property import COLUMN_MAP

    # Build proper fixed-width record
    def make_fwf_line(owner1, owner2, reid):
        line = ""
        line += owner1.ljust(35)  # Owner 1
        line += owner2.ljust(35)  # Owner 2
        # Fill remaining columns with spaces
        for i, (col, width) in enumerate(COLUMN_MAP.items()):
            if i < 2:  # Skip Owner 1 and Owner 2 (already added)
                continue
            if col == "REID":
                line += reid.ljust(width)
            else:
                line += " " * width
        return line + "\n"

    sample_fwf = make_fwf_line("JOHN DOE", "JANE DOE", "0000101") + make_fwf_line(
        "SMITH LLC", "", "0000202"
    )
    zip_bytes = _make_test_zip(sample_fwf)
    mock_download.return_value = zip_bytes

    # Execute
    fetch_wake_county_property_data()

    # Verify
    mock_discover.assert_called_once_with("https://services.wake.gov/realdata_extracts/")
    mock_download.assert_called_once_with(
        "https://services.wake.gov/realdata_extracts/RealEstData02102026.zip"
    )
    mock_session.execute.assert_called()  # Truncate delete
    mock_session.add_all.assert_called_once()
    assert len(mock_session.add_all.call_args[0][0]) == 2  # 2 records
    mock_session.commit.assert_called()
    mock_session.close.assert_called_once()


@patch("pricepoint.data.housing.wake_county_property.SessionLocal")
@patch("pricepoint.data.housing.wake_county_property._discover_zip_url")
@patch("pricepoint.data.housing.wake_county_property.get_settings")
def test_fetch_rolls_back_on_error(mock_settings, mock_discover, mock_session_cls):
    """fetch_wake_county_property_data should rollback on error."""
    # Setup mocks
    mock_settings.return_value = MagicMock(
        wake_county_extracts_url="https://services.wake.gov/realdata_extracts/"
    )
    mock_discover.side_effect = Exception("Download failed")
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    # Execute and verify exception
    with pytest.raises(Exception, match="Download failed"):
        fetch_wake_county_property_data()

    # Verify rollback and close
    mock_session.rollback.assert_called_once()
    mock_session.close.assert_called_once()

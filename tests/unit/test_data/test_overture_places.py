"""Tests for the Overture Maps Places collector."""

from unittest.mock import MagicMock, patch

import pytest

from pricepoint.data.geospatial.overture_places import _map_overture_row


class TestMapOvertureRow:
    """Tests for the _map_overture_row mapper function."""

    def _make_row(self, **overrides):
        """Create a mock DuckDB result row as a tuple."""
        defaults = {
            "id": "overture-abc-123",
            "name": "Costco Wholesale",
            "category": "warehouse_club",
            "alternate_categories": ["shopping", "retail"],
            "confidence": 0.95,
            "operating_status": "open",
            "address": "123 Main St",
            "city": "Raleigh",
            "state": "NC",
            "postcode": "27601",
            "country": "US",
            "brand_name": "Costco",
            "brand_wikidata": "Q715583",
            "website": "https://costco.com",
            "phone": "+19195551234",
            "email": "info@costco.com",
            "social": "https://facebook.com/costco",
            "source_dataset": "meta",
            "source_record_id": "abc123",
            "longitude": -78.6382,
            "latitude": 35.7796,
        }
        defaults.update(overrides)
        return tuple(defaults.values())

    def test_maps_all_fields(self):
        row = self._make_row()
        result = _map_overture_row(row)
        assert result.source_id == "overture-abc-123"
        assert result.name == "Costco Wholesale"
        assert result.category == "warehouse_club"
        assert result.alternate_categories == ["shopping", "retail"]
        assert result.confidence == 0.95
        assert result.operating_status == "open"
        assert result.address == "123 Main St"
        assert result.city == "Raleigh"
        assert result.state == "NC"
        assert result.postcode == "27601"
        assert result.country == "US"
        assert result.brand_name == "Costco"
        assert result.brand_wikidata == "Q715583"
        assert result.website == "https://costco.com"
        assert result.phone == "+19195551234"
        assert result.email == "info@costco.com"
        assert result.social == "https://facebook.com/costco"
        assert result.source_dataset == "meta"
        assert result.source_record_id == "abc123"
        assert result.geom is not None

    def test_none_geometry_when_coords_missing(self):
        row = self._make_row(longitude=None, latitude=None)
        result = _map_overture_row(row)
        assert result.geom is None

    def test_none_longitude_produces_none_geom(self):
        row = self._make_row(longitude=None)
        result = _map_overture_row(row)
        assert result.geom is None

    def test_none_latitude_produces_none_geom(self):
        row = self._make_row(latitude=None)
        result = _map_overture_row(row)
        assert result.geom is None

    def test_none_optional_fields(self):
        row = self._make_row(
            brand_name=None,
            brand_wikidata=None,
            website=None,
            phone=None,
            email=None,
            social=None,
            address=None,
            country=None,
            source_dataset=None,
            source_record_id=None,
        )
        result = _map_overture_row(row)
        assert result.brand_name is None
        assert result.brand_wikidata is None
        assert result.website is None
        assert result.phone is None
        assert result.email is None
        assert result.social is None
        assert result.address is None
        assert result.country is None
        assert result.source_id == "overture-abc-123"

    def test_source_id_is_set(self):
        row = self._make_row()
        result = _map_overture_row(row)
        assert result.source_id is not None

    def test_different_categories(self):
        for category in ["restaurant", "grocery_store", "gas_station", "pharmacy"]:
            row = self._make_row(category=category)
            result = _map_overture_row(row)
            assert result.category == category


class TestFetchPlaces:
    """Tests for fetch_places with mocked DuckDB and DB."""

    @patch("pricepoint.data.geospatial.overture_places.SessionLocal")
    @patch("pricepoint.data.geospatial.overture_places.duckdb")
    @patch("pricepoint.data.geospatial.overture_places.get_settings")
    def test_fetch_calls_duckdb_with_s3_path(self, mock_settings, mock_duckdb, mock_session_cls):
        from pricepoint.data.geospatial.overture_places import fetch_places

        settings = MagicMock()
        settings.overture_places_s3_path = "s3://test-bucket/places/*"
        settings.overture_places_min_confidence = 0.5
        mock_settings.return_value = settings

        mock_con = MagicMock()
        mock_duckdb.connect.return_value = mock_con
        mock_result = MagicMock()
        mock_result.fetchmany.return_value = []
        mock_con.execute.return_value = mock_result

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        fetch_places()

        mock_duckdb.connect.assert_called_once()
        assert mock_con.execute.call_count >= 4  # spatial, httpfs, s3_region, query

    @patch("pricepoint.data.geospatial.overture_places.SessionLocal")
    @patch("pricepoint.data.geospatial.overture_places.duckdb")
    @patch("pricepoint.data.geospatial.overture_places.get_settings")
    def test_fetch_truncates_table_before_load(self, mock_settings, mock_duckdb, mock_session_cls):
        from pricepoint.data.geospatial.overture_places import fetch_places

        settings = MagicMock()
        settings.overture_places_s3_path = "s3://test-bucket/places/*"
        settings.overture_places_min_confidence = 0.5
        mock_settings.return_value = settings

        mock_con = MagicMock()
        mock_duckdb.connect.return_value = mock_con
        mock_result = MagicMock()
        mock_result.fetchmany.return_value = []
        mock_con.execute.return_value = mock_result

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        fetch_places()

        # Verify delete was called (truncate-and-reload pattern)
        mock_session.execute.assert_called()
        mock_session.commit.assert_called()

    @patch("pricepoint.data.geospatial.overture_places.SessionLocal")
    @patch("pricepoint.data.geospatial.overture_places.duckdb")
    @patch("pricepoint.data.geospatial.overture_places.get_settings")
    def test_fetch_inserts_rows_in_batches(self, mock_settings, mock_duckdb, mock_session_cls):
        from pricepoint.data.geospatial.overture_places import fetch_places

        settings = MagicMock()
        settings.overture_places_s3_path = "s3://test-bucket/places/*"
        settings.overture_places_min_confidence = 0.5
        mock_settings.return_value = settings

        mock_con = MagicMock()
        mock_duckdb.connect.return_value = mock_con

        row = (
            "id-1",
            "Test Place",
            "restaurant",
            ["dining"],
            0.9,
            "open",
            "123 St",
            "Raleigh",
            "NC",
            "27601",
            "US",
            "Brand",
            None,
            "https://test.com",
            "+1555",
            None,
            None,
            "meta",
            "rec-1",
            -78.6,
            35.7,
        )
        mock_result = MagicMock()
        mock_result.fetchmany.side_effect = [[row], []]
        mock_con.execute.return_value = mock_result

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        fetch_places()

        mock_session.add_all.assert_called_once()
        records = mock_session.add_all.call_args[0][0]
        assert len(records) == 1
        assert records[0].source_id == "id-1"


class TestVerifyPlaces:
    """Tests for verify_places."""

    @patch("pricepoint.data.geospatial.overture_places.SessionLocal")
    def test_verify_passes_when_records_exist(self, mock_session_cls):
        from pricepoint.data.geospatial.overture_places import verify_places

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.execute.return_value.scalar.return_value = 42

        verify_places()  # Should not raise

    @patch("pricepoint.data.geospatial.overture_places.SessionLocal")
    def test_verify_raises_when_no_records(self, mock_session_cls):
        from pricepoint.data.geospatial.overture_places import verify_places

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.execute.return_value.scalar.return_value = 0

        with pytest.raises(RuntimeError, match="No records found"):
            verify_places()


class TestBuildQuery:
    """Tests for the DuckDB query builder."""

    def test_query_contains_s3_path(self):
        from pricepoint.data.geospatial.overture_places import _build_query

        query = _build_query("s3://my-bucket/places/*", 0.5)
        assert "s3://my-bucket/places/*" in query

    def test_query_contains_confidence_filter(self):
        from pricepoint.data.geospatial.overture_places import _build_query

        query = _build_query("s3://bucket/*", 0.7)
        assert "0.7" in query

    def test_query_selects_expected_columns(self):
        from pricepoint.data.geospatial.overture_places import _build_query

        query = _build_query("s3://bucket/*", 0.5)
        for col in [
            "id",
            "name",
            "category",
            "alternate_categories",
            "confidence",
            "operating_status",
            "longitude",
            "latitude",
            "brand_wikidata",
            "email",
            "social",
            "source_dataset",
            "source_record_id",
            "country",
        ]:
            assert col in query

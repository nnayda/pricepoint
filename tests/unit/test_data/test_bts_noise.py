"""Unit tests for BTS National Transportation Noise Map collector."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from pricepoint.data.geospatial.bts_noise import (
    COLOR_TO_DB_BAND,
    NOISE_MODES,
    _build_noise_production,
    _classify_tile,
    _enumerate_tiles,
    _get_band_info,
    _get_band_labels,
    _lat_lon_to_tile,
    _match_color,
    _merge_batch_polygons,
    _reproject_3857_to_4326,
    _smooth_classified,
    _tile_affine,
    _tile_bounds_3857,
    _tile_to_lat_lon,
    _tile_url_template,
    _vectorize_tiles,
    fetch_all_transportation_noise,
    fetch_transportation_noise,
    verify_transportation_noise,
)


# ---------------------------------------------------------------------------
# NOISE_MODES registry tests
# ---------------------------------------------------------------------------
class TestNoiseModes:
    """Tests for the NOISE_MODES registry."""

    def test_all_modes_present(self):
        """All four expected modes should be in the registry."""
        assert "aviation" in NOISE_MODES
        assert "road" in NOISE_MODES
        assert "rail" in NOISE_MODES
        assert "aviation_road_rail" in NOISE_MODES

    def test_service_names_are_strings(self):
        """All service name values should be non-empty strings."""
        for _mode, service in NOISE_MODES.items():
            assert isinstance(service, str)
            assert len(service) > 0
            assert service.startswith("NTAD_Noise_2020_CONUS_")

    def test_tile_url_template(self):
        """_tile_url_template should produce a valid URL pattern."""
        url = _tile_url_template("https://example.com/rest", "SomeService")
        assert url == "https://example.com/rest/SomeService/MapServer/tile/{z}/{y}/{x}"


# ---------------------------------------------------------------------------
# Tile math tests
# ---------------------------------------------------------------------------
class TestTileMath:
    """Tests for tile coordinate conversion functions."""

    def test_lat_lon_to_tile_known_values(self):
        """Wake County area should map to known tile coords at zoom 12."""
        x, y = _lat_lon_to_tile(35.8, -78.7, 12)
        assert 1100 <= x <= 1200
        assert 1550 <= y <= 1650

    def test_lat_lon_to_tile_origin(self):
        """Equator/prime-meridian should map near center tiles."""
        x, y = _lat_lon_to_tile(0.0, 0.0, 1)
        assert x == 1
        assert y == 1

    def test_tile_to_lat_lon_roundtrip(self):
        """Converting to tile and back should be approximately consistent."""
        lat, lon = 35.8, -78.7
        x, y = _lat_lon_to_tile(lat, lon, 12)
        lat2, lon2 = _tile_to_lat_lon(x, y, 12)
        # Should be within ~1 degree (tile resolution)
        assert abs(lat - lat2) < 1.0
        assert abs(lon - lon2) < 1.0

    def test_enumerate_tiles_small_bbox(self):
        """Small bbox should produce a small number of tiles."""
        tiles = _enumerate_tiles(35.7, 35.9, -78.8, -78.6, 12)
        assert len(tiles) > 0
        assert len(tiles) < 20
        # All tuples of (x, y)
        for tx, ty in tiles:
            assert isinstance(tx, int)
            assert isinstance(ty, int)

    def test_enumerate_tiles_single_point(self):
        """A point bbox should produce at least 1 tile."""
        tiles = _enumerate_tiles(35.8, 35.8, -78.7, -78.7, 12)
        assert len(tiles) >= 1

    def test_tile_bounds_3857(self):
        """Tile bounds should return valid EPSG:3857 coordinates."""
        west, south, east, north = _tile_bounds_3857(1133, 1594, 12)
        assert west < east
        assert south < north
        # Should be in valid 3857 range
        assert abs(west) < 20_100_000
        assert abs(east) < 20_100_000

    def test_tile_affine_returns_transform(self):
        """tile_affine should return a valid rasterio Affine transform."""
        transform = _tile_affine(1133, 1594, 12)
        # Affine has a, b, c, d, e, f attributes
        assert hasattr(transform, "a")
        assert transform.a > 0  # positive x resolution


# ---------------------------------------------------------------------------
# Color classification tests
# ---------------------------------------------------------------------------
class TestColorClassification:
    """Tests for color matching and classification."""

    def test_match_color_exact(self):
        """Exact color match should return the correct band."""
        result = _match_color(255, 0, 0)
        assert result is not None
        min_db, max_db, label = result
        assert min_db == 55
        assert max_db == 60
        assert label == "55.0-59.9"

    def test_match_color_near_match(self):
        """Color within tolerance should match."""
        # Slightly off from (255, 0, 0) which is 55.0-59.9
        result = _match_color(250, 5, 5)
        assert result is not None
        _, _, label = result
        assert label == "55.0-59.9"

    def test_match_color_no_match(self):
        """Color far from all known colors should return None."""
        result = _match_color(0, 128, 0)  # green, not in ramp
        assert result is None

    def test_match_color_transparent_not_handled(self):
        """match_color only handles RGB, transparency handled elsewhere."""
        # Should still try to match pure black
        result = _match_color(0, 0, 0)
        assert result is None  # black is not in the color ramp

    def test_get_band_labels_sorted(self):
        """Band labels should be sorted."""
        labels = _get_band_labels()
        assert labels == sorted(labels)
        assert len(labels) > 0

    def test_get_band_info_valid(self):
        """Should return (min_db, max_db) for a known band."""
        min_db, max_db = _get_band_info("55.0-59.9")
        assert min_db == 55
        assert max_db == 60

    def test_get_band_info_unbounded(self):
        """The >90.0 band should have max_db=None."""
        min_db, max_db = _get_band_info(">90.0")
        assert min_db == 90
        assert max_db is None

    def test_get_band_info_invalid(self):
        """Invalid band label should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown band label"):
            _get_band_info("invalid-band")

    def test_classify_tile_all_transparent(self):
        """Fully transparent tile should produce all-zero array."""
        img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        buf = BytesIO()
        img.save(buf, format="PNG")
        result = _classify_tile(buf.getvalue())
        assert result.shape == (256, 256)
        assert not result.any()

    def test_classify_tile_with_known_color(self):
        """Tile with a known noise color should produce non-zero pixels."""
        # Create tile with one known color: (255, 0, 0) = 55.0-59.9 dB
        img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        # Paint a small region
        for x in range(10, 20):
            for y in range(10, 20):
                img.putpixel((x, y), (255, 0, 0, 255))
        buf = BytesIO()
        img.save(buf, format="PNG")
        result = _classify_tile(buf.getvalue())
        assert result.shape == (256, 256)
        assert result.any()
        # The painted region should have a non-zero band index
        assert result[10, 10] > 0


# ---------------------------------------------------------------------------
# Morphological smoothing tests
# ---------------------------------------------------------------------------
class TestSmoothClassified:
    """Tests for _smooth_classified morphological closing."""

    def test_fills_single_pixel_gap(self):
        """A single-pixel gap surrounded by the same band should be filled."""
        arr = np.zeros((256, 256), dtype=np.uint8)
        # Create a 3x3 block with a hole in the center
        arr[10, 10] = 1
        arr[10, 11] = 1
        arr[10, 12] = 1
        arr[11, 10] = 1
        # arr[11, 11] = 0  -- the gap
        arr[11, 12] = 1
        arr[12, 10] = 1
        arr[12, 11] = 1
        arr[12, 12] = 1

        result = _smooth_classified(arr)
        assert result[11, 11] == 1

    def test_no_cross_band_overwrite(self):
        """Closing for one band must not overwrite another band's pixels."""
        arr = np.zeros((256, 256), dtype=np.uint8)
        # Band 1 on the left, band 2 on the right, touching
        arr[10:20, 10:15] = 1
        arr[10:20, 15:20] = 2

        result = _smooth_classified(arr)
        # Band boundaries should be preserved
        assert np.all(result[10:20, 10:15] == 1)
        assert np.all(result[10:20, 15:20] == 2)

    def test_empty_array(self):
        """An all-zero array should remain all-zero."""
        arr = np.zeros((256, 256), dtype=np.uint8)
        result = _smooth_classified(arr)
        assert not result.any()

    def test_preserves_shape(self):
        """Output should have the same shape as input."""
        arr = np.zeros((256, 256), dtype=np.uint8)
        arr[50:100, 50:100] = 1
        result = _smooth_classified(arr)
        assert result.shape == (256, 256)

    def test_does_not_mutate_input(self):
        """The original array should not be modified."""
        arr = np.zeros((256, 256), dtype=np.uint8)
        arr[10:20, 10:20] = 1
        arr[15, 15] = 0  # gap
        original = arr.copy()
        _smooth_classified(arr)
        np.testing.assert_array_equal(arr, original)


# ---------------------------------------------------------------------------
# Vectorization tests
# ---------------------------------------------------------------------------
class TestVectorization:
    """Tests for vectorizing classified tile arrays."""

    def _make_classified_array(self, band_index: int, size: int = 50) -> np.ndarray:
        """Create a classified array with a square block of the given band."""
        arr = np.zeros((256, 256), dtype=np.uint8)
        arr[50 : 50 + size, 50 : 50 + size] = band_index
        return arr

    def test_vectorize_single_tile(self):
        """A single tile with one band should produce polygons for that band."""
        labels = _get_band_labels()
        # Use band index 1 (first band)
        classified = self._make_classified_array(1)
        tile_data = [((1133, 1594), classified)]

        result = _vectorize_tiles(tile_data, 12)
        assert isinstance(result, dict)
        # First band should have polygons
        assert len(result[labels[0]]) > 0

    def test_vectorize_empty_tile(self):
        """An all-zero tile should produce no polygons."""
        classified = np.zeros((256, 256), dtype=np.uint8)
        tile_data = [((1133, 1594), classified)]

        result = _vectorize_tiles(tile_data, 12)
        total_polys = sum(len(v) for v in result.values())
        assert total_polys == 0

    def test_vectorize_multiple_bands(self):
        """Tiles with multiple bands should produce polygons for each."""
        labels = _get_band_labels()
        arr = np.zeros((256, 256), dtype=np.uint8)
        arr[10:60, 10:60] = 1  # first band
        arr[100:150, 100:150] = 2  # second band
        tile_data = [((1133, 1594), arr)]

        result = _vectorize_tiles(tile_data, 12)
        assert len(result[labels[0]]) > 0
        assert len(result[labels[1]]) > 0


# ---------------------------------------------------------------------------
# Merge & reproject tests
# ---------------------------------------------------------------------------
class TestMergeAndReproject:
    """Tests for polygon merging and reprojection."""

    def test_reproject_3857_to_4326(self):
        """Reprojecting a point from 3857 to 4326 should produce valid lat/lon."""
        from shapely.geometry import Point

        # Roughly Wake County in 3857
        pt_3857 = Point(-8760000, 4260000)
        pt_4326 = _reproject_3857_to_4326(pt_3857)
        # Should be in NC area
        assert -80 < pt_4326.x < -77
        assert 35 < pt_4326.y < 37

    def test_merge_batch_polygons_empty(self):
        """Empty polygon dict should produce empty records list."""
        result = _merge_batch_polygons({}, 0.0001, 500.0, source_layer="aviation")
        assert result == []

    def test_merge_batch_polygons_filters_small(self):
        """Polygons smaller than min_area should be filtered out."""
        from shapely.geometry import box

        # Very small polygon in EPSG:3857 (< 500 sq metres)
        tiny = box(0, 0, 1, 1)  # 1 sq metre
        band_polygons = {"55.0-59.9": [tiny]}
        result = _merge_batch_polygons(band_polygons, 0.0001, 500.0, source_layer="road")
        assert len(result) == 0

    def test_merge_batch_polygons_keeps_large(self):
        """Polygons larger than min_area should be kept."""
        from shapely.geometry import box

        # Large polygon in EPSG:3857
        large = box(-8761000, 4259000, -8760000, 4260000)  # ~1km x 1km
        band_polygons = {"55.0-59.9": [large]}
        result = _merge_batch_polygons(
            band_polygons, 0.0001, 500.0, source_layer="aviation_road_rail"
        )
        assert len(result) == 1
        assert result[0]["noise_band"] == "55.0-59.9"
        assert result[0]["noise_min_db"] == 55
        assert result[0]["noise_max_db"] == 60
        assert result[0]["source_layer"] == "aviation_road_rail"

    def test_merge_batch_polygons_source_layer_parameterized(self):
        """source_layer should be set from the parameter, not a constant."""
        from shapely.geometry import box

        large = box(-8761000, 4259000, -8760000, 4260000)
        for layer in ("aviation", "road", "rail"):
            result = _merge_batch_polygons(
                {"55.0-59.9": [large]}, 0.0001, 500.0, source_layer=layer
            )
            assert result[0]["source_layer"] == layer

    def test_merge_batch_polygons_merges_adjacent(self):
        """Adjacent polygons of the same band should merge into fewer records."""
        from shapely.geometry import box

        # Two adjacent large boxes
        box1 = box(-8762000, 4259000, -8761000, 4260000)
        box2 = box(-8761000, 4259000, -8760000, 4260000)
        band_polygons = {"55.0-59.9": [box1, box2]}
        result = _merge_batch_polygons(band_polygons, 0.0001, 500.0, source_layer="road")
        # Should merge into 1 polygon
        assert len(result) == 1


# ---------------------------------------------------------------------------
# _build_noise_production tests
# ---------------------------------------------------------------------------
class TestBuildNoiseProduction:
    """Tests for the PostGIS promotion step."""

    def test_executes_sql_with_correct_params(self):
        """Should call session.execute with the promote SQL and correct params."""
        from datetime import UTC, datetime

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_session.execute.return_value = mock_result

        mock_settings = MagicMock()
        mock_settings.bts_noise_chaikin_iterations = 3
        mock_settings.bts_noise_simplify_tolerance = 0.001
        mock_settings.bts_noise_cluster_eps = 0.001
        mock_settings.bts_noise_buffer_distance = 0.0005
        mock_settings.bts_noise_max_hole_area_sq_m = 50000.0
        mock_settings.bts_noise_min_polygon_area_sq_m = 500.0

        run_started = datetime(2026, 1, 1, tzinfo=UTC)

        count = _build_noise_production(mock_session, "aviation", run_started, mock_settings)

        assert count == 5
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

        # Verify the params dict
        call_args = mock_session.execute.call_args
        params = call_args[0][1]
        assert params["iterations"] == 3
        assert params["tolerance"] == 0.001
        assert params["cluster_eps"] == 0.001
        assert params["buffer_dist"] == 0.0005
        assert params["max_hole_area"] == 50000.0
        assert params["min_area"] == 500.0
        assert params["run_started"] == run_started
        assert params["source_layer"] == "aviation"

    def test_returns_zero_when_no_rows(self):
        """Should return 0 when no rows promoted."""
        from datetime import UTC, datetime

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        mock_settings = MagicMock()
        mock_settings.bts_noise_chaikin_iterations = 3
        mock_settings.bts_noise_simplify_tolerance = 0.001
        mock_settings.bts_noise_cluster_eps = 0.001
        mock_settings.bts_noise_buffer_distance = 0.0005
        mock_settings.bts_noise_max_hole_area_sq_m = 50000.0
        mock_settings.bts_noise_min_polygon_area_sq_m = 500.0

        count = _build_noise_production(
            mock_session, "rail", datetime(2026, 1, 1, tzinfo=UTC), mock_settings
        )
        assert count == 0

    def test_promote_sql_subtracts_higher_bands(self):
        """Promote SQL should use ST_Difference to subtract louder bands from quieter ones."""
        from pricepoint.data.geospatial.bts_noise import _PROMOTE_SQL

        assert "ST_Difference" in _PROMOTE_SQL
        assert "ST_CollectionExtract" in _PROMOTE_SQL
        assert "holes_filled" in _PROMOTE_SQL
        assert "max_hole_area" in _PROMOTE_SQL
        assert "min_area" in _PROMOTE_SQL


# ---------------------------------------------------------------------------
# fetch_transportation_noise tests
# ---------------------------------------------------------------------------
class TestFetchTransportationNoise:
    """Tests for the main fetch function (mocked I/O)."""

    def _make_png(self, color: tuple[int, int, int, int] = (255, 0, 0, 255)) -> bytes:
        """Create a synthetic 256x256 PNG with a colored region."""
        img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        # Paint a large block so it's big enough to pass area filter
        for x in range(0, 256):
            for y in range(0, 256):
                img.putpixel((x, y), color)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    @patch("pricepoint.data.geospatial.bts_noise.SessionLocal")
    @patch("pricepoint.data.geospatial.bts_noise.get_settings")
    @patch("pricepoint.data.geospatial.bts_noise._download_tile")
    def test_fetch_success(self, mock_download, mock_settings, mock_session_cls):
        """fetch_transportation_noise should download, vectorize, stage, and promote."""
        settings = MagicMock()
        settings.bts_noise_zoom = 12
        settings.bts_noise_base_url = "https://geo.dot.gov/server/rest/services/Hosted"
        settings.bts_noise_tile_rate_limit = 0.0
        settings.bts_noise_batch_size = 100
        settings.bts_noise_simplify_tolerance = 0.001
        settings.bts_noise_min_polygon_area_sq_m = 0.0  # accept all
        settings.bts_noise_bbox_south = 35.78
        settings.bts_noise_bbox_north = 35.82
        settings.bts_noise_bbox_west = -78.72
        settings.bts_noise_bbox_east = -78.68
        settings.bts_noise_morphological_closing = True
        settings.bts_noise_chaikin_iterations = 3
        settings.bts_noise_cluster_eps = 0.001
        settings.bts_noise_buffer_distance = 0.0005
        mock_settings.return_value = settings

        mock_download.return_value = self._make_png()

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        # Make execute return a result with rowcount for promotion and cleanup
        mock_execute = MagicMock()
        mock_execute.rowcount = 5
        mock_session.execute.return_value = mock_execute

        count = fetch_transportation_noise(mode="aviation")
        assert count == 5  # from the mock promotion rowcount
        assert mock_session.add.called
        assert mock_session.commit.called

    @patch("pricepoint.data.geospatial.bts_noise.SessionLocal")
    @patch("pricepoint.data.geospatial.bts_noise.get_settings")
    @patch("pricepoint.data.geospatial.bts_noise._download_tile")
    def test_fetch_no_tiles(self, mock_download, mock_settings, mock_session_cls):
        """If all tile downloads fail, should return 0."""
        settings = MagicMock()
        settings.bts_noise_zoom = 12
        settings.bts_noise_base_url = "https://geo.dot.gov/server/rest/services/Hosted"
        settings.bts_noise_tile_rate_limit = 0.0
        settings.bts_noise_batch_size = 100
        settings.bts_noise_simplify_tolerance = 0.0001
        settings.bts_noise_min_polygon_area_sq_m = 500.0
        settings.bts_noise_bbox_south = 35.78
        settings.bts_noise_bbox_north = 35.82
        settings.bts_noise_bbox_west = -78.72
        settings.bts_noise_bbox_east = -78.68
        settings.bts_noise_morphological_closing = False
        mock_settings.return_value = settings

        mock_download.return_value = None  # All tiles fail

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        count = fetch_transportation_noise(mode="road")
        assert count == 0

    def test_fetch_invalid_mode(self):
        """Unknown mode should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown noise mode"):
            fetch_transportation_noise(mode="helicopter")

    @patch("pricepoint.data.geospatial.bts_noise.SessionLocal")
    @patch("pricepoint.data.geospatial.bts_noise.get_settings")
    @patch("pricepoint.data.geospatial.bts_noise._download_tile")
    def test_fetch_uses_correct_url_for_mode(self, mock_download, mock_settings, mock_session_cls):
        """Each mode should use the correct BTS service name in the URL."""
        settings = MagicMock()
        settings.bts_noise_zoom = 12
        settings.bts_noise_base_url = "https://geo.dot.gov/server/rest/services/Hosted"
        settings.bts_noise_tile_rate_limit = 0.0
        settings.bts_noise_batch_size = 100
        settings.bts_noise_simplify_tolerance = 0.0001
        settings.bts_noise_min_polygon_area_sq_m = 500.0
        settings.bts_noise_bbox_south = 35.8
        settings.bts_noise_bbox_north = 35.8
        settings.bts_noise_bbox_west = -78.7
        settings.bts_noise_bbox_east = -78.7
        settings.bts_noise_morphological_closing = False
        mock_settings.return_value = settings

        mock_download.return_value = None

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        fetch_transportation_noise(mode="rail")

        # Check the URL template passed to _download_tile contains the rail service name
        if mock_download.called:
            url_arg = mock_download.call_args[0][1]
            assert "NTAD_Noise_2020_CONUS_Rail" in url_arg


# ---------------------------------------------------------------------------
# fetch_all_transportation_noise tests
# ---------------------------------------------------------------------------
class TestFetchAllTransportationNoise:
    """Tests for the convenience wrapper that fetches all modes."""

    @patch("pricepoint.data.geospatial.bts_noise.fetch_transportation_noise")
    @patch("pricepoint.data.geospatial.bts_noise.get_settings")
    def test_calls_all_modes(self, mock_settings, mock_fetch):
        """Should call fetch_transportation_noise for each configured mode."""
        settings = MagicMock()
        settings.bts_noise_modes = ["aviation", "road", "rail", "aviation_road_rail"]
        mock_settings.return_value = settings
        mock_fetch.return_value = 10

        total = fetch_all_transportation_noise()
        assert total == 40
        assert mock_fetch.call_count == 4
        mock_fetch.assert_any_call(mode="aviation")
        mock_fetch.assert_any_call(mode="road")
        mock_fetch.assert_any_call(mode="rail")
        mock_fetch.assert_any_call(mode="aviation_road_rail")

    @patch("pricepoint.data.geospatial.bts_noise.fetch_transportation_noise")
    @patch("pricepoint.data.geospatial.bts_noise.get_settings")
    def test_subset_of_modes(self, mock_settings, mock_fetch):
        """Should only call modes listed in settings."""
        settings = MagicMock()
        settings.bts_noise_modes = ["aviation", "road"]
        mock_settings.return_value = settings
        mock_fetch.return_value = 5

        total = fetch_all_transportation_noise()
        assert total == 10
        assert mock_fetch.call_count == 2


# ---------------------------------------------------------------------------
# verify_transportation_noise tests
# ---------------------------------------------------------------------------
class TestVerifyTransportationNoise:
    """Tests for the verify function."""

    @patch("pricepoint.data.geospatial.bts_noise.SessionLocal")
    def test_verify_success(self, mock_session_cls):
        """Should return count when records exist."""
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.execute.return_value.scalar.return_value = 42

        count = verify_transportation_noise()
        assert count == 42

    @patch("pricepoint.data.geospatial.bts_noise.SessionLocal")
    def test_verify_empty(self, mock_session_cls):
        """Should raise RuntimeError when table is empty."""
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.execute.return_value.scalar.return_value = 0

        with pytest.raises(RuntimeError, match="No records found"):
            verify_transportation_noise()


# ---------------------------------------------------------------------------
# COLOR_TO_DB_BAND mapping tests
# ---------------------------------------------------------------------------
class TestColorMapping:
    """Tests for the color-to-dB-band mapping consistency."""

    def test_all_bands_have_valid_ranges(self):
        """All bands should have min_db >= 45 and consistent max_db."""
        for color, (min_db, max_db, label) in COLOR_TO_DB_BAND.items():
            assert min_db >= 45
            if max_db is not None:
                assert max_db > min_db
            assert isinstance(label, str)
            assert len(color) == 3

    def test_band_labels_unique_per_range(self):
        """Each (min_db, max_db) pair should map to a single label."""
        range_to_labels: dict[tuple[int, int | None], set[str]] = {}
        for _, (min_db, max_db, label) in COLOR_TO_DB_BAND.items():
            key = (min_db, max_db)
            if key not in range_to_labels:
                range_to_labels[key] = set()
            range_to_labels[key].add(label)
        for key, labels in range_to_labels.items():
            assert len(labels) == 1, f"Multiple labels for range {key}: {labels}"

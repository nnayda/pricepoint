"""Unit tests for the risk boundaries gold builder."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pricepoint.data.geospatial.risk_boundaries import (
    _FT_TO_M,
    _get_distances,
    build_risk_boundaries,
    verify_risk_boundaries,
)


class TestGetDistances:
    """Test distance config lookup."""

    def test_cell_towers(self):
        distances = _get_distances("cell_towers")
        assert distances["critical"] == pytest.approx(1300 * _FT_TO_M)
        assert distances["caution"] == pytest.approx(3000 * _FT_TO_M)

    def test_transmission_lines(self):
        distances = _get_distances("transmission_lines")
        assert distances["critical"] == pytest.approx(50 * _FT_TO_M)
        assert distances["caution"] == pytest.approx(300 * _FT_TO_M)

    def test_nat_gas_pipelines(self):
        distances = _get_distances("nat_gas_pipelines")
        assert distances["critical"] == pytest.approx(600 * _FT_TO_M)
        assert distances["caution"] == pytest.approx(5280 * _FT_TO_M)

    def test_petroleum_pipelines(self):
        distances = _get_distances("petroleum_pipelines")
        assert distances["critical"] == pytest.approx(600 * _FT_TO_M)
        assert distances["caution"] == pytest.approx(5280 * _FT_TO_M)

    def test_power_plant_nuclear(self):
        distances = _get_distances("power_plants", "Nuclear")
        assert distances["critical"] == pytest.approx(52800 * _FT_TO_M)
        assert distances["caution"] == pytest.approx(264000 * _FT_TO_M)

    def test_power_plant_case_insensitive(self):
        distances = _get_distances("power_plants", "SOLAR")
        assert distances["critical"] == pytest.approx(300 * _FT_TO_M)
        assert distances["caution"] == pytest.approx(1000 * _FT_TO_M)

    def test_power_plant_with_whitespace(self):
        distances = _get_distances("power_plants", " Wind ")
        assert distances["critical"] == pytest.approx(2500 * _FT_TO_M)
        assert distances["caution"] == pytest.approx(7920 * _FT_TO_M)

    def test_power_plant_default_fallback(self):
        """Unknown primary source uses _default distances."""
        distances = _get_distances("power_plants", "hydroelectric")
        assert distances["critical"] == pytest.approx(2640 * _FT_TO_M)
        assert distances["caution"] == pytest.approx(10560 * _FT_TO_M)

    def test_power_plant_none_source(self):
        """None primary_source uses _default distances."""
        distances = _get_distances("power_plants", None)
        assert distances["critical"] == pytest.approx(2640 * _FT_TO_M)
        assert distances["caution"] == pytest.approx(10560 * _FT_TO_M)

    def test_power_plant_natural_gas(self):
        distances = _get_distances("power_plants", "natural gas")
        assert distances["critical"] == pytest.approx(10560 * _FT_TO_M)
        assert distances["caution"] == pytest.approx(26400 * _FT_TO_M)

    def test_power_plant_coal(self):
        distances = _get_distances("power_plants", "coal")
        assert distances["critical"] == pytest.approx(26400 * _FT_TO_M)
        assert distances["caution"] == pytest.approx(158400 * _FT_TO_M)


class TestBuildRiskBoundaries:
    """Test the main build function."""

    @patch("pricepoint.data.geospatial.risk_boundaries._build_power_plant_buffers")
    @patch("pricepoint.data.geospatial.risk_boundaries._build_simple_buffers")
    def test_build_calls_all_types(self, mock_simple, mock_power):
        """Build should process all 4 simple types + power plants."""
        mock_simple.return_value = 10
        mock_power.return_value = 5
        session = MagicMock()
        # Mock the delete result
        session.execute.return_value.rowcount = 0

        count = build_risk_boundaries(session)

        assert mock_simple.call_count == 4
        assert mock_power.call_count == 1
        # 4 simple types * 10 each + 5 power plants = 45
        assert count == 45

    @patch("pricepoint.data.geospatial.risk_boundaries._build_power_plant_buffers")
    @patch("pricepoint.data.geospatial.risk_boundaries._build_simple_buffers")
    def test_build_deletes_existing(self, mock_simple, mock_power):
        """Build should delete existing records first."""
        mock_simple.return_value = 0
        mock_power.return_value = 0
        session = MagicMock()
        session.execute.return_value.rowcount = 100

        build_risk_boundaries(session)

        # First call to execute should be delete
        assert session.execute.called

    @patch("pricepoint.data.geospatial.risk_boundaries._build_power_plant_buffers")
    @patch("pricepoint.data.geospatial.risk_boundaries._build_simple_buffers")
    def test_build_simple_types(self, mock_simple, mock_power):
        """Verify the correct model/infra_type pairs are passed to _build_simple_buffers."""
        mock_simple.return_value = 0
        mock_power.return_value = 0
        session = MagicMock()
        session.execute.return_value.rowcount = 0

        build_risk_boundaries(session)

        infra_types = [call.args[2] for call in mock_simple.call_args_list]
        assert "cell_towers" in infra_types
        assert "transmission_lines" in infra_types
        assert "nat_gas_pipelines" in infra_types
        assert "petroleum_pipelines" in infra_types


class TestVerifyRiskBoundaries:
    """Test the verification function."""

    def test_verify_raises_on_empty(self):
        """Should raise RuntimeError if table is empty."""
        session = MagicMock()
        session.scalar.return_value = 0

        with pytest.raises(RuntimeError, match="No records"):
            verify_risk_boundaries(session)

    def test_verify_passes_with_data(self):
        """Should not raise when records exist."""
        session = MagicMock()
        session.scalar.return_value = 100

        verify_risk_boundaries(session)

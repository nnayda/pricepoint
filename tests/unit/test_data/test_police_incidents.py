"""Unit tests for the main fetch_police_incidents orchestrator."""

from unittest.mock import patch

from pricepoint.data.geospatial.police_incidents import fetch_police_incidents


MODULE = "pricepoint.data.geospatial.police_incidents"


class TestFetchPoliceIncidents:
    @patch(f"{MODULE}.fetch_morrisville_police_incidents")
    @patch(f"{MODULE}.fetch_raleigh_police_incidents")
    @patch(f"{MODULE}.fetch_cary_police_incidents")
    def test_calls_all_collectors(self, mock_cary, mock_raleigh, mock_morrisville):
        """All three city collectors are called with the full_refresh flag."""
        results = fetch_police_incidents(full_refresh=True)

        mock_cary.assert_called_once_with(full_refresh=True)
        mock_raleigh.assert_called_once_with(full_refresh=True)
        mock_morrisville.assert_called_once_with(full_refresh=True)
        assert results == {"cary": "ok", "raleigh": "ok", "morrisville": "ok"}

    @patch(f"{MODULE}.fetch_morrisville_police_incidents")
    @patch(f"{MODULE}.fetch_raleigh_police_incidents")
    @patch(f"{MODULE}.fetch_cary_police_incidents")
    def test_passes_full_refresh_false(self, mock_cary, mock_raleigh, mock_morrisville):
        """When full_refresh=False, that flag is forwarded to each collector."""
        results = fetch_police_incidents(full_refresh=False)

        mock_cary.assert_called_once_with(full_refresh=False)
        mock_raleigh.assert_called_once_with(full_refresh=False)
        mock_morrisville.assert_called_once_with(full_refresh=False)
        assert results == {"cary": "ok", "raleigh": "ok", "morrisville": "ok"}

    @patch(f"{MODULE}.fetch_morrisville_police_incidents")
    @patch(f"{MODULE}.fetch_raleigh_police_incidents")
    @patch(f"{MODULE}.fetch_cary_police_incidents")
    def test_one_collector_failure_continues(self, mock_cary, mock_raleigh, mock_morrisville):
        """If one collector raises, the others still run and results reflect the error."""
        mock_raleigh.side_effect = Exception("Raleigh API down")

        results = fetch_police_incidents(full_refresh=True)

        mock_cary.assert_called_once()
        mock_raleigh.assert_called_once()
        mock_morrisville.assert_called_once()
        assert results["cary"] == "ok"
        assert results["raleigh"] == "error"
        assert results["morrisville"] == "ok"

    @patch(f"{MODULE}.fetch_morrisville_police_incidents")
    @patch(f"{MODULE}.fetch_raleigh_police_incidents")
    @patch(f"{MODULE}.fetch_cary_police_incidents")
    def test_all_collectors_fail(self, mock_cary, mock_raleigh, mock_morrisville):
        """If all collectors raise, all results show error and no exception propagates."""
        mock_cary.side_effect = Exception("Cary error")
        mock_raleigh.side_effect = Exception("Raleigh error")
        mock_morrisville.side_effect = Exception("Morrisville error")

        results = fetch_police_incidents(full_refresh=True)

        assert results == {"cary": "error", "raleigh": "error", "morrisville": "error"}

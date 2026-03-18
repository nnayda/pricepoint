"""Tests for the model methodology API endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(app):
    """HTTP test client bound to the test application."""
    return TestClient(app)


# ── /api/model/methodology ──


class _FakeModelVersion:
    def __init__(self, run_id: str = "run123", version: str = "5"):
        self.run_id = run_id
        self.version = version


class _FakeRunInfo:
    start_time = 1700000000000  # 2023-11-14T22:13:20Z


class _FakeRunData:
    metrics = {
        "mae": 25000.0,
        "rmse": 35000.0,
        "mape": 8.5,
        "r2": 0.92,
        "median_ae": 18000.0,
        "n_features": 94,
        "n_training_samples": 1200,
        "feature_importance_top20_sqft": 0.15,
        "feature_importance_top20_year_built": 0.08,
    }
    params = {"objective": "reg:squarederror", "n_estimators": "500", "max_depth": "6"}


class _FakeRun:
    info = _FakeRunInfo()
    data = _FakeRunData()


class _FakeArtifact:
    def __init__(self, path: str):
        self.path = path


def _mock_mlflow_client():
    """Return a configured mock MlflowClient."""
    mock_client = MagicMock()
    mock_client.get_model_version_by_alias.return_value = _FakeModelVersion()
    mock_client.get_run.return_value = _FakeRun()
    mock_client.list_artifacts.side_effect = lambda run_id, subdir: {
        "plots": [_FakeArtifact("plots/actual_vs_predicted.png")],
        "eda": [_FakeArtifact("eda/eda_pairwise_target.png")],
    }.get(subdir, [])
    return mock_client


def test_methodology_returns_response(client):
    """Methodology endpoint returns full response with correct schema."""
    mock_client = _mock_mlflow_client()

    with patch(
        "pricepoint.api.routes.model_methodology._get_mlflow_client",
        return_value=mock_client,
    ):
        resp = client.get("/api/model/methodology")

    assert resp.status_code == 200
    body = resp.json()
    assert body["metadata"]["model_version"] == "5"
    assert body["metadata"]["run_id"] == "run123"
    assert body["metadata"]["n_features"] == 94
    assert body["metadata"]["n_training_samples"] == 1200
    assert body["metadata"]["algorithm"] == "reg:squarederror"
    assert body["metrics"]["mae"] == 25000.0
    assert body["metrics"]["r2"] == 0.92
    assert len(body["feature_importance"]) == 2
    assert body["feature_importance"][0]["feature"] == "sqft"
    assert body["available_plots"] == ["plots/actual_vs_predicted.png"]
    assert body["available_eda_plots"] == ["eda/eda_pairwise_target.png"]


def test_methodology_404_no_champion(client):
    """Returns 404 when no champion model exists."""
    from mlflow.exceptions import RestException

    mock_client = MagicMock()
    mock_client.get_model_version_by_alias.side_effect = RestException(
        {"error_code": "RESOURCE_DOES_NOT_EXIST", "message": "not found"}
    )

    with patch(
        "pricepoint.api.routes.model_methodology._get_mlflow_client",
        return_value=mock_client,
    ):
        resp = client.get("/api/model/methodology")

    assert resp.status_code == 404
    assert "champion" in resp.json()["detail"].lower()


def test_methodology_503_mlflow_rest_error(client):
    """Returns 503 when MLflow returns a non-404 REST error."""
    from mlflow.exceptions import RestException

    mock_client = MagicMock()
    mock_client.get_model_version_by_alias.side_effect = RestException(
        {"error_code": "INTERNAL_ERROR", "message": "server error"}
    )

    with patch(
        "pricepoint.api.routes.model_methodology._get_mlflow_client",
        return_value=mock_client,
    ):
        resp = client.get("/api/model/methodology")

    assert resp.status_code == 503


def test_methodology_503_mlflow_connection_error(client):
    """Returns 503 when MLflow raises a generic MlflowException (e.g. connection)."""
    from mlflow.exceptions import MlflowException

    mock_client = MagicMock()
    mock_client.get_model_version_by_alias.side_effect = MlflowException(
        "API request to endpoint /api/2.0/mlflow/registered-models/alias failed"
    )

    with patch(
        "pricepoint.api.routes.model_methodology._get_mlflow_client",
        return_value=mock_client,
    ):
        resp = client.get("/api/model/methodology")

    assert resp.status_code == 503


def test_methodology_503_mlflow_unreachable(client):
    """Returns 503 when MLflow cannot be reached."""
    with patch(
        "pricepoint.api.routes.model_methodology._get_mlflow_client",
        side_effect=ConnectionError("unreachable"),
    ):
        resp = client.get("/api/model/methodology")

    assert resp.status_code == 503


# ── /api/model/artifact/{path} ──


def test_artifact_returns_png(client, tmp_path):
    """Artifact endpoint streams a PNG image."""
    mock_client = _mock_mlflow_client()

    # Create a fake PNG file in the temp directory
    artifact_dir = tmp_path / "plots"
    artifact_dir.mkdir()
    png_file = artifact_dir / "actual_vs_predicted.png"
    png_file.write_bytes(b"\x89PNG fake image data")

    mock_client.download_artifacts.return_value = str(png_file)

    with patch(
        "pricepoint.api.routes.model_methodology._get_mlflow_client",
        return_value=mock_client,
    ):
        resp = client.get("/api/model/artifact/plots/actual_vs_predicted.png")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.headers["cache-control"] == "public, max-age=86400"
    assert b"PNG" in resp.content


def test_artifact_rejects_traversal(client):
    """Artifact endpoint rejects path traversal attempts."""
    mock_client = _mock_mlflow_client()

    with patch(
        "pricepoint.api.routes.model_methodology._get_mlflow_client",
        return_value=mock_client,
    ):
        # URL-encoded traversal that won't be normalized by the HTTP framework
        resp = client.get("/api/model/artifact/plots/..%2F..%2Fetc%2Fpasswd")

    # Either 400 (our check) or 404 (route miss) — both are safe
    assert resp.status_code in (400, 404)


def test_artifact_rejects_invalid_prefix(client):
    """Artifact endpoint rejects paths not starting with plots/ or eda/."""
    mock_client = _mock_mlflow_client()

    with patch(
        "pricepoint.api.routes.model_methodology._get_mlflow_client",
        return_value=mock_client,
    ):
        resp = client.get("/api/model/artifact/model/model.pkl")

    assert resp.status_code == 400


def test_artifact_404_missing(client):
    """Artifact endpoint returns 404 for non-existent artifacts."""
    mock_client = _mock_mlflow_client()
    mock_client.download_artifacts.side_effect = Exception("not found")

    with patch(
        "pricepoint.api.routes.model_methodology._get_mlflow_client",
        return_value=mock_client,
    ):
        resp = client.get("/api/model/artifact/plots/nonexistent.png")

    assert resp.status_code == 404


# ── /api/model/features ──


def test_features_returns_catalog(client):
    """Features endpoint returns parsed feature catalog."""
    fake_markdown = """\
# Feature Catalog

## 1. Location & Address

Fields identifying the property.

| Column | SQL Type | Source | Derivation | Example | Default |
|--------|----------|--------|------------|---------|---------|
| `street_address` | `String` | `staging.address` | parse | `"123 Main"` | — |
| `city` | `String` | `staging.city` | Direct | `"Charlotte"` | `NULL` |

## 2. Listing & Pricing

Pricing info.

| Column | SQL Type | Source | Derivation | Example | Default |
|--------|----------|--------|------------|---------|---------|
| `sold_price` | `Float` | `staging.sold_price` | parse_price | `721000.0` | `NULL` |
"""
    with (
        patch(
            "pricepoint.api.routes.model_methodology.Path.exists",
            return_value=True,
        ),
        patch(
            "pricepoint.api.routes.model_methodology.Path.read_text",
            return_value=fake_markdown,
        ),
    ):
        # Clear the cache
        import pricepoint.api.routes.model_methodology as mod

        mod._feature_catalog_cache = None

        resp = client.get("/api/model/features")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["features"]) == 3
    assert body["categories"] == ["Location & Address", "Listing & Pricing"]
    assert body["features"][0]["name"] == "street_address"
    assert body["features"][0]["category"] == "Location & Address"
    assert body["features"][2]["name"] == "sold_price"

    # Reset cache
    mod._feature_catalog_cache = None


def test_features_search_by_name(client):
    """Verify feature catalog includes expected fields for filtering."""
    fake_markdown = """\
# Catalog

## 1. Test Category

| Column | SQL Type | Source | Derivation | Example | Default |
|--------|----------|--------|------------|---------|---------|
| `sqft` | `Integer` | `staging` | parse | `2450` | `NULL` |
"""
    with (
        patch(
            "pricepoint.api.routes.model_methodology.Path.exists",
            return_value=True,
        ),
        patch(
            "pricepoint.api.routes.model_methodology.Path.read_text",
            return_value=fake_markdown,
        ),
    ):
        import pricepoint.api.routes.model_methodology as mod

        mod._feature_catalog_cache = None

        resp = client.get("/api/model/features")

    body = resp.json()
    assert any(f["name"] == "sqft" for f in body["features"])
    mod._feature_catalog_cache = None

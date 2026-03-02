"""Tests for the Redfin HTML upload endpoint."""

from io import BytesIO
from unittest.mock import patch

import pytest


@pytest.fixture
def html_file():
    """Return a tuple (filename, file-like, content-type) for a .html upload."""
    return ("listing.html", BytesIO(b"<html></html>"), "text/html")


def test_upload_single_file(client, tmp_path):
    with (
        patch("pricepoint.api.routes.upload.get_settings") as mock,
        patch("pricepoint.api.routes.upload._trigger_airflow_dag", return_value=True),
    ):
        mock.return_value.redfin_html_dir = str(tmp_path)
        resp = client.post(
            "/api/upload/redfin",
            files=[("files", ("listing.html", BytesIO(b"<html></html>"), "text/html"))],
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["saved"] == ["listing.html"]
    assert data["errors"] == []
    assert (tmp_path / "listing.html").read_bytes() == b"<html></html>"


def test_upload_multiple_files(client, tmp_path):
    with (
        patch("pricepoint.api.routes.upload.get_settings") as mock,
        patch("pricepoint.api.routes.upload._trigger_airflow_dag", return_value=True),
    ):
        mock.return_value.redfin_html_dir = str(tmp_path)
        resp = client.post(
            "/api/upload/redfin",
            files=[
                ("files", ("a.html", BytesIO(b"<a>"), "text/html")),
                ("files", ("b.html", BytesIO(b"<b>"), "text/html")),
            ],
        )
    assert resp.status_code == 200
    assert set(resp.json()["saved"]) == {"a.html", "b.html"}


def test_upload_rejects_non_html(client, tmp_path):
    with patch("pricepoint.api.routes.upload.get_settings") as mock:
        mock.return_value.redfin_html_dir = str(tmp_path)
        resp = client.post(
            "/api/upload/redfin",
            files=[("files", ("data.csv", BytesIO(b"a,b"), "text/csv"))],
        )
    assert resp.status_code == 400
    data = resp.json()
    assert data["saved"] == []
    assert any("data.csv" in e for e in data["errors"])


def test_upload_creates_directory(client, tmp_path):
    dest = tmp_path / "nested" / "dir"
    with (
        patch("pricepoint.api.routes.upload.get_settings") as mock,
        patch("pricepoint.api.routes.upload._trigger_airflow_dag", return_value=True),
    ):
        mock.return_value.redfin_html_dir = str(dest)
        resp = client.post(
            "/api/upload/redfin",
            files=[("files", ("test.html", BytesIO(b"<html/>"), "text/html"))],
        )
    assert resp.status_code == 200
    assert dest.is_dir()
    assert (dest / "test.html").exists()


def test_upload_triggers_dag_on_success(client, tmp_path):
    """DAG is triggered when files are saved successfully."""
    with (
        patch("pricepoint.api.routes.upload.get_settings") as mock,
        patch(
            "pricepoint.api.routes.upload._trigger_airflow_dag", return_value=True
        ) as trigger_mock,
    ):
        mock.return_value.redfin_html_dir = str(tmp_path)
        resp = client.post(
            "/api/upload/redfin",
            files=[("files", ("listing.html", BytesIO(b"<html></html>"), "text/html"))],
        )
    assert resp.status_code == 200
    assert resp.json()["dag_triggered"] is True
    trigger_mock.assert_called_once_with("redfin_listing_collection")


def test_upload_dag_trigger_failure_still_returns_200(client, tmp_path):
    """Upload succeeds even if DAG trigger fails."""
    with (
        patch("pricepoint.api.routes.upload.get_settings") as mock,
        patch("pricepoint.api.routes.upload._trigger_airflow_dag", return_value=False),
    ):
        mock.return_value.redfin_html_dir = str(tmp_path)
        resp = client.post(
            "/api/upload/redfin",
            files=[("files", ("listing.html", BytesIO(b"<html></html>"), "text/html"))],
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["saved"] == ["listing.html"]
    assert data["dag_triggered"] is False


def test_upload_no_dag_trigger_on_failure(client, tmp_path):
    """DAG is not triggered when no files are saved."""
    with (
        patch("pricepoint.api.routes.upload.get_settings") as mock,
        patch(
            "pricepoint.api.routes.upload._trigger_airflow_dag"
        ) as trigger_mock,
    ):
        mock.return_value.redfin_html_dir = str(tmp_path)
        resp = client.post(
            "/api/upload/redfin",
            files=[("files", ("data.csv", BytesIO(b"a,b"), "text/csv"))],
        )
    assert resp.status_code == 400
    trigger_mock.assert_not_called()

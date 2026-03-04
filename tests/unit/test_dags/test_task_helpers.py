"""Tests for shared Airflow task helper utilities."""

import sys
from datetime import datetime
from pathlib import Path

# Add dags/ to sys.path so we can import the helpers without Airflow
_dags_dir = str(Path(__file__).resolve().parents[3] / "dags")
if _dags_dir not in sys.path:
    sys.path.insert(0, _dags_dir)

from common.task_helpers import (  # noqa: E402
    get_execution_date_str,
    notify_on_failure,
    send_ntfy_notification,
)


def test_get_execution_date_str():
    """Should format a datetime as YYYY-MM-DD."""
    dt = datetime(2024, 7, 15, 10, 30, 0)
    assert get_execution_date_str(dt) == "2024-07-15"


def test_get_execution_date_str_leading_zeros():
    """Should pad single-digit month/day with leading zeros."""
    dt = datetime(2025, 1, 5)
    assert get_execution_date_str(dt) == "2025-01-05"


class MockDag:
    def __init__(self, dag_id):
        self.dag_id = dag_id


class MockTaskInstance:
    def __init__(self, task_id):
        self.task_id = task_id


def test_notify_on_failure_logs_alert(caplog):
    """Should log an alert message with dag and task info."""
    context = {
        "dag": MockDag("test_dag"),
        "task_instance": MockTaskInstance("test_task"),
    }
    with caplog.at_level("ERROR"):
        notify_on_failure(context)
    assert "ALERT" in caplog.text
    assert "test_task" in caplog.text
    assert "test_dag" in caplog.text


def test_notify_on_failure_handles_missing_context(caplog):
    """Should handle empty context without raising."""
    with caplog.at_level("ERROR"):
        notify_on_failure({})
    assert "unknown" in caplog.text


class TestSendNtfyNotification:
    """Tests for send_ntfy_notification."""

    def test_success(self, monkeypatch):
        """Should POST JSON to ntfy server and return True."""
        from unittest.mock import MagicMock, patch

        fake_resp = MagicMock()
        fake_resp.status = 200
        fake_resp.__enter__ = lambda s: s
        fake_resp.__exit__ = MagicMock(return_value=False)

        captured_req = {}

        def fake_urlopen(req, timeout=None):
            captured_req["url"] = req.full_url
            captured_req["data"] = req.data
            captured_req["method"] = req.method
            captured_req["headers"] = dict(req.headers)
            return fake_resp

        with patch("urllib.request.urlopen", fake_urlopen):
            result = send_ntfy_notification(
                topic="test-topic",
                title="Test Title",
                message="Test body",
                server_url="https://ntfy.example.com",
                priority="high",
                tags=["tada"],
            )

        assert result is True
        assert captured_req["url"] == "https://ntfy.example.com/test-topic"
        assert captured_req["method"] == "POST"

        import json

        payload = json.loads(captured_req["data"])
        assert payload["topic"] == "test-topic"
        assert payload["title"] == "Test Title"
        assert payload["message"] == "Test body"
        assert payload["priority"] == "high"
        assert payload["tags"] == ["tada"]

    def test_strips_trailing_slash(self, monkeypatch):
        """Should strip trailing slash from server_url."""
        from unittest.mock import MagicMock, patch

        fake_resp = MagicMock()
        fake_resp.status = 200
        fake_resp.__enter__ = lambda s: s
        fake_resp.__exit__ = MagicMock(return_value=False)

        captured_url = {}

        def fake_urlopen(req, timeout=None):
            captured_url["url"] = req.full_url
            return fake_resp

        with patch("urllib.request.urlopen", fake_urlopen):
            send_ntfy_notification(
                topic="t",
                title="T",
                message="M",
                server_url="https://ntfy.sh/",
            )

        assert captured_url["url"] == "https://ntfy.sh/t"

    def test_returns_false_on_network_error(self, caplog):
        """Should return False and log warning on failure."""
        from unittest.mock import patch

        with (
            patch("urllib.request.urlopen", side_effect=OSError("connection refused")),
            caplog.at_level("WARNING"),
        ):
            result = send_ntfy_notification(topic="t", title="T", message="M")

        assert result is False
        assert "Failed to send ntfy notification" in caplog.text

    def test_no_tags(self):
        """Should omit tags key when tags is None."""
        import json
        from unittest.mock import MagicMock, patch

        fake_resp = MagicMock()
        fake_resp.status = 200
        fake_resp.__enter__ = lambda s: s
        fake_resp.__exit__ = MagicMock(return_value=False)

        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["data"] = req.data
            return fake_resp

        with patch("urllib.request.urlopen", fake_urlopen):
            send_ntfy_notification(topic="t", title="T", message="M")

        payload = json.loads(captured["data"])
        assert "tags" not in payload

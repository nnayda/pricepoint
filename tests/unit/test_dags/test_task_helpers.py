"""Tests for shared Airflow task helper utilities."""

import sys
from datetime import datetime
from pathlib import Path

# Add dags/ to sys.path so we can import the helpers without Airflow
_dags_dir = str(Path(__file__).resolve().parents[3] / "dags")
if _dags_dir not in sys.path:
    sys.path.insert(0, _dags_dir)

from common.task_helpers import get_execution_date_str, notify_on_failure  # noqa: E402


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

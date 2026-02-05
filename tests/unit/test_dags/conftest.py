"""Fixtures for Airflow DAG tests."""

from pathlib import Path

import pytest

DAGS_DIR = Path(__file__).resolve().parents[3] / "dags"


@pytest.fixture
def dags_dir():
    """Return the path to the dags directory."""
    return DAGS_DIR


@pytest.fixture
def dag_files(dags_dir):
    """Return all dag_*.py files in the dags directory."""
    return sorted(dags_dir.glob("dag_*.py"))

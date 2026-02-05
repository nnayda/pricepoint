"""Tests that DAG files parse without syntax errors (no Airflow import needed)."""

import ast


def test_all_dag_files_parse(dag_files):
    """Every DAG file should be valid Python (no SyntaxError)."""
    for dag_file in dag_files:
        try:
            ast.parse(dag_file.read_text())
        except SyntaxError as exc:
            raise AssertionError(f"{dag_file.name} has a syntax error: {exc}") from exc


def test_expected_dag_files_exist(dag_files):
    """There should be exactly 5 DAG files."""
    names = {f.name for f in dag_files}
    assert "dag_data_collection.py" in names
    assert "dag_feature_engineering.py" in names
    assert "dag_model_training.py" in names
    assert "dag_cary_police_collection.py" in names
    assert "dag_raleigh_police_collection.py" in names
    assert len(dag_files) == 5

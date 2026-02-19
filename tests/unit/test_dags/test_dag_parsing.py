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
    """There should be exactly 11 DAG files."""
    names = {f.name for f in dag_files}
    assert "dag_data_collection.py" in names
    assert "dag_feature_engineering.py" in names
    assert "dag_model_training.py" in names
    assert "dag_cary_police_collection.py" in names
    assert "dag_raleigh_police_collection.py" in names
    assert "dag_morrisville_police_collection.py" in names
    assert "dag_tiger_boundary_collection.py" in names
    assert "dag_wake_county_property_collection.py" in names
    assert "dag_redfin_listing_collection.py" in names
    assert "dag_redfin_transform.py" in names
    assert "dag_nces_school_collection.py" in names
    assert "dag_description_scoring.py" in names
    assert "dag_photo_scoring.py" in names
    assert "dag_wake_subdivision_collection.py" in names
    assert "dag_wake_farmers_market_collection.py" in names
    assert "dag_wake_library_collection.py" in names
    assert "dag_wake_hospital_collection.py" in names
    assert "dag_wake_park_collection.py" in names
    assert "dag_raleigh_park_collection.py" in names
    assert "dag_cary_park_collection.py" in names
    assert "dag_wake_greenway_collection.py" in names
    assert "dag_raleigh_greenway_collection.py" in names
    assert "dag_cary_greenway_collection.py" in names
    assert "dag_wake_railroad_collection.py" in names
    assert "dag_wake_major_road_collection.py" in names
    assert "dag_wake_highway_collection.py" in names
    assert "dag_wake_utility_easement_collection.py" in names
    assert "dag_economic_collection.py" in names
    assert len(dag_files) == 28

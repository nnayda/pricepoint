"""Tests for feature assembly module."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from pricepoint.features.assembly import (
    assemble_features,
    get_stale_property_ids,
    reset_features_built_at,
)


@pytest.fixture()
def mock_db():
    """Create a mock database session."""
    return MagicMock()


def _geo_df(property_ids: list[int]) -> pd.DataFrame:
    """Create a sample geospatial features DataFrame."""
    return pd.DataFrame(
        {"dist_nearest_school_m": [100.0] * len(property_ids)},
        index=pd.Index(property_ids, name="property_id"),
    )


def _housing_df(property_ids: list[int]) -> pd.DataFrame:
    """Create a sample housing features DataFrame."""
    return pd.DataFrame(
        {"property_age": [10] * len(property_ids)},
        index=pd.Index(property_ids, name="property_id"),
    )


def _econ_df(property_ids: list[int]) -> pd.DataFrame:
    """Create a sample economic features DataFrame."""
    return pd.DataFrame(
        {"mortgage_rate_30yr": [6.5] * len(property_ids)},
        index=pd.Index(property_ids, name="property_id"),
    )


def _comp_df(property_ids: list[int]) -> pd.DataFrame:
    """Create a sample comparable features DataFrame."""
    return pd.DataFrame(
        {"comp_median_ppsf": [200.0] * len(property_ids)},
        index=pd.Index(property_ids, name="property_id"),
    )


@patch("pricepoint.features.assembly.build_comparable_features")
@patch("pricepoint.features.assembly.build_economic_features")
@patch("pricepoint.features.assembly.build_housing_features")
@patch("pricepoint.features.assembly.build_geospatial_features")
def test_assemble_merges_all_four(mock_geo, mock_housing, mock_econ, mock_comp, mock_db):
    """assemble_features merges geo, housing, econ, and comp DataFrames on property_id."""
    ids = [1, 2, 3]
    mock_geo.return_value = _geo_df(ids)
    mock_housing.return_value = _housing_df(ids)
    mock_econ.return_value = _econ_df(ids)
    mock_comp.return_value = _comp_df(ids)

    result = assemble_features(mock_db)

    assert result.shape == (3, 4)
    assert "dist_nearest_school_m" in result.columns
    assert "property_age" in result.columns
    assert "mortgage_rate_30yr" in result.columns
    assert "comp_median_ppsf" in result.columns
    assert list(result.index) == ids


@patch("pricepoint.features.assembly.build_comparable_features")
@patch("pricepoint.features.assembly.build_economic_features")
@patch("pricepoint.features.assembly.build_housing_features")
@patch("pricepoint.features.assembly.build_geospatial_features")
def test_assemble_passes_property_ids(mock_geo, mock_housing, mock_econ, mock_comp, mock_db):
    """assemble_features forwards property_ids to all four builders."""
    mock_geo.return_value = _geo_df([1])
    mock_housing.return_value = _housing_df([1])
    mock_econ.return_value = _econ_df([1])
    mock_comp.return_value = _comp_df([1])

    assemble_features(mock_db, property_ids=[1])

    mock_geo.assert_called_once_with(mock_db, property_ids=[1])
    mock_housing.assert_called_once_with(mock_db, property_ids=[1])
    mock_econ.assert_called_once_with(mock_db, property_ids=[1])
    mock_comp.assert_called_once_with(mock_db, property_ids=[1])


@patch("pricepoint.features.assembly.build_comparable_features")
@patch("pricepoint.features.assembly.build_economic_features")
@patch("pricepoint.features.assembly.build_housing_features")
@patch("pricepoint.features.assembly.build_geospatial_features")
def test_assemble_drops_all_nan_rows(mock_geo, mock_housing, mock_econ, mock_comp, mock_db):
    """Rows where every feature is NaN should be dropped."""
    mock_geo.return_value = pd.DataFrame(
        {"dist_nearest_school_m": [100.0, float("nan")]},
        index=pd.Index([1, 2], name="property_id"),
    )
    mock_housing.return_value = pd.DataFrame(
        {"property_age": [10, float("nan")]},
        index=pd.Index([1, 2], name="property_id"),
    )
    mock_econ.return_value = pd.DataFrame(
        {"mortgage_rate_30yr": [6.5, float("nan")]},
        index=pd.Index([1, 2], name="property_id"),
    )
    mock_comp.return_value = pd.DataFrame(
        {"comp_median_ppsf": [200.0, float("nan")]},
        index=pd.Index([1, 2], name="property_id"),
    )

    result = assemble_features(mock_db)

    assert len(result) == 1
    assert 1 in result.index
    assert 2 not in result.index


@patch("pricepoint.features.assembly.build_comparable_features")
@patch("pricepoint.features.assembly.build_economic_features")
@patch("pricepoint.features.assembly.build_housing_features")
@patch("pricepoint.features.assembly.build_geospatial_features")
def test_assemble_empty_inputs(mock_geo, mock_housing, mock_econ, mock_comp, mock_db):
    """Returns an empty DataFrame when all builders return empty."""
    mock_geo.return_value = pd.DataFrame()
    mock_housing.return_value = pd.DataFrame()
    mock_econ.return_value = pd.DataFrame()
    mock_comp.return_value = pd.DataFrame()

    result = assemble_features(mock_db)

    assert result.empty


@patch("pricepoint.features.assembly.build_comparable_features")
@patch("pricepoint.features.assembly.build_economic_features")
@patch("pricepoint.features.assembly.build_housing_features")
@patch("pricepoint.features.assembly.build_geospatial_features")
def test_assemble_partial_overlap(mock_geo, mock_housing, mock_econ, mock_comp, mock_db):
    """Properties present in some builders but not others get NaN for missing columns."""
    mock_geo.return_value = pd.DataFrame(
        {"dist_nearest_school_m": [100.0, 200.0]},
        index=pd.Index([1, 2], name="property_id"),
    )
    mock_housing.return_value = pd.DataFrame(
        {"property_age": [10]},
        index=pd.Index([1], name="property_id"),
    )
    mock_econ.return_value = pd.DataFrame(
        {"mortgage_rate_30yr": [6.5]},
        index=pd.Index([2], name="property_id"),
    )
    mock_comp.return_value = pd.DataFrame(
        {"comp_median_ppsf": [200.0]},
        index=pd.Index([1], name="property_id"),
    )

    result = assemble_features(mock_db)

    # Both rows should survive since they have at least one non-NaN value
    assert len(result) == 2
    assert pd.isna(result.loc[2, "property_age"])
    assert pd.isna(result.loc[1, "mortgage_rate_30yr"])


@patch("pricepoint.features.assembly.build_comparable_features")
@patch("pricepoint.features.assembly.build_economic_features")
@patch("pricepoint.features.assembly.build_housing_features")
@patch("pricepoint.features.assembly.build_geospatial_features")
def test_assemble_keeps_partial_nan_rows(mock_geo, mock_housing, mock_econ, mock_comp, mock_db):
    """Rows with some NaN values but not all should be kept."""
    mock_geo.return_value = pd.DataFrame(
        {"dist_nearest_school_m": [100.0]},
        index=pd.Index([1], name="property_id"),
    )
    mock_housing.return_value = pd.DataFrame(
        {"property_age": [float("nan")]},
        index=pd.Index([1], name="property_id"),
    )
    mock_econ.return_value = pd.DataFrame(
        {"mortgage_rate_30yr": [6.5]},
        index=pd.Index([1], name="property_id"),
    )
    mock_comp.return_value = pd.DataFrame(
        {"comp_median_ppsf": [200.0]},
        index=pd.Index([1], name="property_id"),
    )

    result = assemble_features(mock_db)

    assert len(result) == 1
    assert pd.isna(result.loc[1, "property_age"])
    assert result.loc[1, "dist_nearest_school_m"] == 100.0


# ---------------------------------------------------------------------------
# get_stale_property_ids
# ---------------------------------------------------------------------------


def test_get_stale_property_ids_returns_ids_with_null_features_built_at(mock_db):
    """Properties with features_built_at=NULL should be detected as stale."""
    mock_db.execute.return_value.scalars.return_value.all.return_value = [1, 3, 7]

    result = get_stale_property_ids(mock_db)

    assert result == [1, 3, 7]
    mock_db.execute.assert_called_once()


def test_get_stale_property_ids_returns_empty_when_all_current(mock_db):
    """No stale properties returns empty list."""
    mock_db.execute.return_value.scalars.return_value.all.return_value = []

    result = get_stale_property_ids(mock_db)

    assert result == []


# ---------------------------------------------------------------------------
# reset_features_built_at
# ---------------------------------------------------------------------------


def test_reset_features_built_at_nulls_timestamps(mock_db):
    """reset_features_built_at should null features_built_at and commit."""
    mock_db.execute.return_value.rowcount = 42

    count = reset_features_built_at(mock_db)

    assert count == 42
    mock_db.execute.assert_called_once()
    mock_db.commit.assert_called_once()


def test_reset_features_built_at_returns_zero_when_none_set(mock_db):
    """Returns 0 when no properties had features_built_at set."""
    mock_db.execute.return_value.rowcount = 0

    count = reset_features_built_at(mock_db)

    assert count == 0

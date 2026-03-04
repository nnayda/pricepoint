"""Tests for pricepoint.models.training."""

import numpy as np
import pandas as pd
import pytest
from xgboost import XGBRegressor

from pricepoint.models.training import (
    DEFAULT_PARAMS,
    MAX_NAN_FRACTION,
    OUTLIER_PERCENTILE_HIGH,
    OUTLIER_PERCENTILE_LOW,
    prepare_features,
    train_model,
)


class TestPrepareFeatures:
    """Tests for the prepare_features function."""

    def test_separates_target(self, synthetic_df: pd.DataFrame) -> None:
        x, y = prepare_features(synthetic_df, "sold_price", filter_outliers=False)
        assert "sold_price" not in x.columns
        assert len(y) == len(synthetic_df)

    def test_drops_raw_strings_keeps_categoricals(
        self, synthetic_df_with_strings: pd.DataFrame
    ) -> None:
        x, _y = prepare_features(synthetic_df_with_strings, "sold_price")
        # Raw string column should be dropped
        assert "city" not in x.columns
        # Category dtype column should be kept
        assert "parking_type" in x.columns

    def test_drops_high_nan_columns(self, synthetic_df_with_nan: pd.DataFrame) -> None:
        x, _y = prepare_features(synthetic_df_with_nan, "sold_price")
        assert "mostly_nan_col" not in x.columns

    def test_drops_nan_target_rows(self, synthetic_df: pd.DataFrame) -> None:
        df = synthetic_df.copy()
        df.loc[0:4, "sold_price"] = np.nan
        x, y = prepare_features(df, "sold_price", filter_outliers=False)
        assert len(x) == len(df) - 5
        assert len(y) == len(df) - 5

    def test_missing_target_column_raises(self, synthetic_df: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="Target column"):
            prepare_features(synthetic_df, "nonexistent")

    def test_categoricals_have_category_dtype(self, synthetic_df: pd.DataFrame) -> None:
        x, _y = prepare_features(synthetic_df, "sold_price")
        assert "parking_type" in x.columns
        assert x["parking_type"].dtype.name == "category"

    def test_outlier_filtering_removes_extremes(self, synthetic_df: pd.DataFrame) -> None:
        df = synthetic_df.copy()
        # Add extreme outliers
        df.loc[0, "sold_price"] = 1.0  # Family transfer
        df.loc[1, "sold_price"] = 50_000_000.0  # Extreme high
        x_filtered, y_filtered = prepare_features(df, "sold_price", filter_outliers=True)
        x_unfiltered, y_unfiltered = prepare_features(df, "sold_price", filter_outliers=False)
        assert len(y_filtered) <= len(y_unfiltered)

    def test_outlier_filtering_disabled(self, synthetic_df: pd.DataFrame) -> None:
        x, y = prepare_features(synthetic_df, "sold_price", filter_outliers=False)
        assert len(y) == len(synthetic_df)

    def test_log_transform_target(self, synthetic_df: pd.DataFrame) -> None:
        _, y_raw = prepare_features(synthetic_df, "sold_price", log_transform_target=False)
        _, y_log = prepare_features(synthetic_df, "sold_price", log_transform_target=True)
        # log1p values should be much smaller than raw prices
        assert y_log.max() < y_raw.max()
        # Verify inverse transform recovers original
        np.testing.assert_allclose(np.expm1(y_log.values), y_raw.values, rtol=1e-5)


class TestTrainModel:
    """Tests for train_model."""

    def test_returns_tuple(self, synthetic_df: pd.DataFrame) -> None:
        result = train_model(features=synthetic_df)
        assert isinstance(result, tuple)
        model, test_indices = result
        assert isinstance(model, XGBRegressor)
        assert isinstance(test_indices, list)
        assert len(test_indices) > 0

    def test_model_can_predict(self, synthetic_df: pd.DataFrame) -> None:
        model, _ = train_model(features=synthetic_df)
        x, _y = prepare_features(synthetic_df, "sold_price")
        preds = model.predict(x)
        assert len(preds) > 0
        assert not np.isnan(preds).any()

    def test_custom_params(self, synthetic_df: pd.DataFrame) -> None:
        model, _ = train_model(features=synthetic_df, params={"n_estimators": 10, "max_depth": 3})
        assert isinstance(model, XGBRegressor)

    def test_handles_nan_features(self, synthetic_df_with_nan: pd.DataFrame) -> None:
        model, _ = train_model(features=synthetic_df_with_nan)
        assert isinstance(model, XGBRegressor)

    def test_handles_string_columns(self, synthetic_df_with_strings: pd.DataFrame) -> None:
        model, _ = train_model(features=synthetic_df_with_strings)
        assert isinstance(model, XGBRegressor)
        assert "city" not in model.feature_names_in_

    def test_missing_target_raises(self, synthetic_df: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="Target column"):
            train_model(features=synthetic_df, target_col="missing_col")

    def test_test_indices_valid(self, synthetic_df: pd.DataFrame) -> None:
        _, test_indices = train_model(features=synthetic_df)
        # test_indices should be a subset of the original index
        assert all(idx in synthetic_df.index for idx in test_indices)

    def test_log_target_attribute(self, synthetic_df: pd.DataFrame) -> None:
        model, _ = train_model(features=synthetic_df, log_transform_target=True)
        assert model.log_target is True

    def test_no_log_target_attribute(self, synthetic_df: pd.DataFrame) -> None:
        model, _ = train_model(features=synthetic_df, log_transform_target=False)
        assert model.log_target is False

    def test_calibration_residuals_stored(self, synthetic_df: pd.DataFrame) -> None:
        model, _ = train_model(features=synthetic_df)
        assert hasattr(model, "calibration_residuals_")
        assert isinstance(model.calibration_residuals_, np.ndarray)
        assert len(model.calibration_residuals_) > 0
        # Should be sorted (ascending)
        assert np.all(np.diff(model.calibration_residuals_) >= 0)

    def test_early_stopping_active(self, synthetic_df: pd.DataFrame) -> None:
        """Early stopping should stop before max n_estimators."""
        model, _ = train_model(features=synthetic_df, params={"n_estimators": 1000})
        assert hasattr(model, "best_iteration")
        assert model.best_iteration < 1000

    def test_default_params_values(self) -> None:
        assert DEFAULT_PARAMS["n_estimators"] == 500
        assert DEFAULT_PARAMS["max_depth"] == 4
        assert DEFAULT_PARAMS["learning_rate"] == 0.03
        assert MAX_NAN_FRACTION == 0.5

    def test_default_params_enable_categorical(self) -> None:
        assert DEFAULT_PARAMS["enable_categorical"] is True
        assert DEFAULT_PARAMS["tree_method"] == "hist"

    def test_outlier_constants(self) -> None:
        assert OUTLIER_PERCENTILE_LOW == 0.01
        assert OUTLIER_PERCENTILE_HIGH == 0.99

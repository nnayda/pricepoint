"""Tests for pricepoint.models.training."""

import numpy as np
import pandas as pd
import pytest
from xgboost import XGBRegressor

from pricepoint.models.training import (
    DEFAULT_PARAMS,
    MAX_NAN_FRACTION,
    prepare_features,
    train_model,
)


class TestPrepareFeatures:
    """Tests for the prepare_features function."""

    def test_separates_target(self, synthetic_df: pd.DataFrame) -> None:
        x, y = prepare_features(synthetic_df, "sold_price")
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
        x, y = prepare_features(df, "sold_price")
        assert len(x) == len(df) - 5
        assert len(y) == len(df) - 5

    def test_missing_target_column_raises(self, synthetic_df: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="Target column"):
            prepare_features(synthetic_df, "nonexistent")

    def test_categoricals_have_category_dtype(self, synthetic_df: pd.DataFrame) -> None:
        x, _y = prepare_features(synthetic_df, "sold_price")
        assert "parking_type" in x.columns
        assert x["parking_type"].dtype.name == "category"


class TestTrainModel:
    """Tests for train_model."""

    def test_returns_xgb_regressor(self, synthetic_df: pd.DataFrame) -> None:
        model = train_model(features=synthetic_df)
        assert isinstance(model, XGBRegressor)

    def test_model_can_predict(self, synthetic_df: pd.DataFrame) -> None:
        model = train_model(features=synthetic_df)
        x, _y = prepare_features(synthetic_df, "sold_price")
        preds = model.predict(x)
        assert len(preds) == len(x)
        assert not np.isnan(preds).any()

    def test_custom_params(self, synthetic_df: pd.DataFrame) -> None:
        model = train_model(features=synthetic_df, params={"n_estimators": 10, "max_depth": 3})
        assert isinstance(model, XGBRegressor)

    def test_handles_nan_features(self, synthetic_df_with_nan: pd.DataFrame) -> None:
        model = train_model(features=synthetic_df_with_nan)
        assert isinstance(model, XGBRegressor)

    def test_handles_string_columns(self, synthetic_df_with_strings: pd.DataFrame) -> None:
        model = train_model(features=synthetic_df_with_strings)
        assert isinstance(model, XGBRegressor)
        assert "city" not in model.feature_names_in_

    def test_missing_target_raises(self, synthetic_df: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="Target column"):
            train_model(features=synthetic_df, target_col="missing_col")

    def test_predictions_are_reasonable(self, synthetic_df: pd.DataFrame) -> None:
        """Model should learn the pattern and get close predictions."""
        model = train_model(features=synthetic_df)
        x, _y = prepare_features(synthetic_df, "sold_price")
        preds = model.predict(x)
        # R^2 should be high on training data for this simple relationship
        ss_res = np.sum((synthetic_df["sold_price"].values - preds) ** 2)
        ss_tot = np.sum(
            (synthetic_df["sold_price"].values - synthetic_df["sold_price"].mean()) ** 2
        )
        r2 = 1 - ss_res / ss_tot
        assert r2 > 0.9

    def test_early_stopping_active(self, synthetic_df: pd.DataFrame) -> None:
        """Early stopping should stop before max n_estimators."""
        model = train_model(features=synthetic_df, params={"n_estimators": 1000})
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

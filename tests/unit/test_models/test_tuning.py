"""Tests for pricepoint.models.tuning."""

from __future__ import annotations

import pandas as pd
import pytest

from pricepoint.models.tuning import TuningResult, tune_hyperparameters


class TestTuneHyperparameters:
    """Tests for the tune_hyperparameters function."""

    def test_returns_tuning_result(self, synthetic_df: pd.DataFrame) -> None:
        result = tune_hyperparameters(
            features=synthetic_df, n_trials=2, timeout=120, log_to_mlflow=False
        )
        assert isinstance(result, TuningResult)

    def test_best_params_contain_search_space_keys(self, synthetic_df: pd.DataFrame) -> None:
        result = tune_hyperparameters(
            features=synthetic_df, n_trials=2, timeout=120, log_to_mlflow=False
        )
        expected_keys = {
            "n_estimators",
            "max_depth",
            "learning_rate",
            "subsample",
            "colsample_bytree",
            "min_child_weight",
            "reg_alpha",
            "reg_lambda",
            "gamma",
            "random_state",
            "n_jobs",
        }
        assert expected_keys.issubset(result.best_params.keys())

    def test_param_values_within_bounds(self, synthetic_df: pd.DataFrame) -> None:
        result = tune_hyperparameters(
            features=synthetic_df, n_trials=3, timeout=120, log_to_mlflow=False
        )
        p = result.best_params
        assert 200 <= p["n_estimators"] <= 1500
        assert 3 <= p["max_depth"] <= 10
        assert 0.01 <= p["learning_rate"] <= 0.3
        assert 0.5 <= p["subsample"] <= 1.0
        assert 0.3 <= p["colsample_bytree"] <= 1.0
        assert 1 <= p["min_child_weight"] <= 10
        assert 1e-3 <= p["reg_alpha"] <= 10.0
        assert 1e-3 <= p["reg_lambda"] <= 10.0
        assert 0.0 <= p["gamma"] <= 5.0

    def test_best_score_is_positive(self, synthetic_df: pd.DataFrame) -> None:
        result = tune_hyperparameters(
            features=synthetic_df, n_trials=2, timeout=120, log_to_mlflow=False
        )
        assert result.best_score > 0

    def test_n_trials_recorded(self, synthetic_df: pd.DataFrame) -> None:
        result = tune_hyperparameters(
            features=synthetic_df, n_trials=3, timeout=120, log_to_mlflow=False
        )
        assert result.n_trials >= 1
        assert result.n_trials <= 3

    def test_all_trials_populated(self, synthetic_df: pd.DataFrame) -> None:
        result = tune_hyperparameters(
            features=synthetic_df, n_trials=3, timeout=120, log_to_mlflow=False
        )
        assert len(result.all_trials) >= 1
        trial = result.all_trials[0]
        assert "number" in trial
        assert "params" in trial
        assert "state" in trial

    def test_custom_cv_folds(self, synthetic_df: pd.DataFrame) -> None:
        result = tune_hyperparameters(
            features=synthetic_df,
            n_trials=2,
            timeout=120,
            n_cv_folds=2,
            log_to_mlflow=False,
        )
        assert isinstance(result, TuningResult)

    def test_missing_target_raises(self, synthetic_df: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="Target column"):
            tune_hyperparameters(
                features=synthetic_df,
                target_col="nonexistent",
                n_trials=2,
                timeout=60,
                log_to_mlflow=False,
            )

    def test_timeout_respected(self, synthetic_df: pd.DataFrame) -> None:
        """With a very short timeout, tuning should complete quickly."""
        result = tune_hyperparameters(
            features=synthetic_df,
            n_trials=1000,
            timeout=3,
            log_to_mlflow=False,
        )
        # Should complete far fewer than 1000 trials
        assert result.n_trials < 1000

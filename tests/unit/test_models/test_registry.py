"""Tests for pricepoint.models.registry."""

from unittest.mock import MagicMock, patch

from pricepoint.models.registry import (
    MODEL_NAME,
    _is_candidate_better,
    compare_and_promote,
    log_model,
    promote_model,
)


class TestLogModel:
    """Tests for log_model."""

    @patch("mlflow.sklearn.log_model")
    @patch("mlflow.log_metrics")
    @patch("mlflow.log_params")
    @patch("mlflow.start_run")
    def test_log_model_returns_run_id(
        self,
        mock_start_run: MagicMock,
        mock_log_params: MagicMock,
        mock_log_metrics: MagicMock,
        mock_log_xgb: MagicMock,
    ) -> None:
        mock_run = MagicMock()
        mock_run.info.run_id = "test-run-123"
        mock_start_run.return_value.__enter__ = MagicMock(return_value=mock_run)
        mock_start_run.return_value.__exit__ = MagicMock(return_value=False)

        model = MagicMock()
        model.get_params.return_value = {"n_estimators": 100}

        run_id = log_model(
            model=model,
            metrics={"mae": 1000.0, "r2": 0.95},
            run_name="test-run",
        )
        assert run_id == "test-run-123"

    @patch("mlflow.sklearn.log_model")
    @patch("mlflow.log_metrics")
    @patch("mlflow.log_params")
    @patch("mlflow.start_run")
    def test_log_model_logs_metrics(
        self,
        mock_start_run: MagicMock,
        mock_log_params: MagicMock,
        mock_log_metrics: MagicMock,
        mock_log_xgb: MagicMock,
    ) -> None:
        mock_run = MagicMock()
        mock_run.info.run_id = "run-456"
        mock_start_run.return_value.__enter__ = MagicMock(return_value=mock_run)
        mock_start_run.return_value.__exit__ = MagicMock(return_value=False)

        model = MagicMock()
        model.get_params.return_value = {}
        metrics = {"mae": 500.0, "r2": 0.98, "feature_importance_top20": {"sqft": 0.5}}

        log_model(model=model, metrics=metrics)
        mock_log_metrics.assert_called_once_with({"mae": 500.0, "r2": 0.98})

    @patch("mlflow.sklearn.log_model")
    @patch("mlflow.log_metrics")
    @patch("mlflow.log_params")
    @patch("mlflow.start_run")
    def test_log_model_logs_params(
        self,
        mock_start_run: MagicMock,
        mock_log_params: MagicMock,
        mock_log_metrics: MagicMock,
        mock_log_xgb: MagicMock,
    ) -> None:
        mock_run = MagicMock()
        mock_run.info.run_id = "run-789"
        mock_start_run.return_value.__enter__ = MagicMock(return_value=mock_run)
        mock_start_run.return_value.__exit__ = MagicMock(return_value=False)

        model = MagicMock()
        model.get_params.return_value = {"n_estimators": 100, "max_depth": 6, "gpu_id": None}

        log_model(model=model, metrics={})
        logged_params = mock_log_params.call_args[0][0]
        assert "n_estimators" in logged_params
        assert "gpu_id" not in logged_params


class TestPromoteModel:
    """Tests for promote_model."""

    @patch("mlflow.tracking.MlflowClient")
    def test_promote_model_sets_alias(self, mock_client_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        promote_model(model_name="test-model", version=3, alias="challenger")
        mock_client.set_registered_model_alias.assert_called_once_with(
            name="test-model", alias="challenger", version="3"
        )

    @patch("mlflow.tracking.MlflowClient")
    def test_promote_model_default_alias(self, mock_client_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        promote_model(version=1)
        mock_client.set_registered_model_alias.assert_called_once_with(
            name=MODEL_NAME, alias="champion", version="1"
        )


class TestIsCandidateBetter:
    """Tests for _is_candidate_better."""

    def test_lower_mae_is_better(self) -> None:
        assert _is_candidate_better(900.0, 1000.0, "mae") is True

    def test_higher_mae_is_worse(self) -> None:
        assert _is_candidate_better(1100.0, 1000.0, "mae") is False

    def test_lower_rmse_is_better(self) -> None:
        assert _is_candidate_better(50.0, 100.0, "rmse") is True

    def test_higher_r2_is_better(self) -> None:
        assert _is_candidate_better(0.96, 0.93, "r2") is True

    def test_lower_r2_is_worse(self) -> None:
        assert _is_candidate_better(0.90, 0.93, "r2") is False


def _make_mock_client(
    *,
    candidate_run_id: str = "candidate-run-1",
    candidate_version: int = 5,
    candidate_metrics: dict[str, float] | None = None,
    champion_run_id: str | None = "champion-run-1",
    champion_version: int | None = 3,
    champion_metrics: dict[str, float] | None = None,
) -> MagicMock:
    """Build a mock MlflowClient for compare_and_promote tests."""
    from mlflow.exceptions import MlflowException

    client = MagicMock()

    # search_model_versions → candidate version
    candidate_mv = MagicMock()
    candidate_mv.version = str(candidate_version)
    client.search_model_versions.return_value = [candidate_mv]

    # get_model_version_by_alias → champion (or raise if None)
    if champion_run_id is not None:
        champion_mv = MagicMock()
        champion_mv.version = str(champion_version)
        champion_mv.run_id = champion_run_id
        client.get_model_version_by_alias.return_value = champion_mv
    else:
        client.get_model_version_by_alias.side_effect = MlflowException("No champion alias")

    # get_run → metrics
    if candidate_metrics is None:
        candidate_metrics = {"mae": 900.0, "rmse": 1200.0, "r2": 0.95}
    if champion_metrics is None:
        champion_metrics = {"mae": 1000.0, "rmse": 1300.0, "r2": 0.93}

    def _get_run(rid: str) -> MagicMock:
        run = MagicMock()
        if rid == candidate_run_id:
            run.data.metrics = candidate_metrics
        elif rid == champion_run_id:
            run.data.metrics = champion_metrics
        else:
            run.data.metrics = {}
        return run

    client.get_run.side_effect = _get_run
    return client


class TestCompareAndPromote:
    """Tests for compare_and_promote."""

    @patch("mlflow.tracking.MlflowClient")
    def test_promotes_when_no_champion(self, mock_client_cls: MagicMock) -> None:
        client = _make_mock_client(champion_run_id=None)
        mock_client_cls.return_value = client

        result = compare_and_promote(run_id="candidate-run-1")

        assert result["promoted"] is True
        reason = result["reason"].lower()
        assert "first model" in reason or "no existing" in reason
        client.set_registered_model_alias.assert_called_once()

    @patch("mlflow.tracking.MlflowClient")
    def test_promotes_when_candidate_mae_lower(self, mock_client_cls: MagicMock) -> None:
        client = _make_mock_client(
            candidate_metrics={"mae": 800.0, "r2": 0.96},
            champion_metrics={"mae": 1000.0, "r2": 0.93},
        )
        mock_client_cls.return_value = client

        result = compare_and_promote(run_id="candidate-run-1", primary_metric="mae")

        assert result["promoted"] is True
        client.set_registered_model_alias.assert_called_once()

    @patch("mlflow.tracking.MlflowClient")
    def test_does_not_promote_when_candidate_mae_higher(self, mock_client_cls: MagicMock) -> None:
        client = _make_mock_client(
            candidate_metrics={"mae": 1200.0, "r2": 0.90},
            champion_metrics={"mae": 1000.0, "r2": 0.93},
        )
        mock_client_cls.return_value = client

        result = compare_and_promote(run_id="candidate-run-1", primary_metric="mae")

        assert result["promoted"] is False
        assert "still better" in result["reason"].lower() or "champion" in result["reason"].lower()
        client.set_registered_model_alias.assert_not_called()

    @patch("mlflow.tracking.MlflowClient")
    def test_promotes_when_candidate_r2_higher(self, mock_client_cls: MagicMock) -> None:
        client = _make_mock_client(
            candidate_metrics={"mae": 1100.0, "r2": 0.97},
            champion_metrics={"mae": 1000.0, "r2": 0.93},
        )
        mock_client_cls.return_value = client

        result = compare_and_promote(run_id="candidate-run-1", primary_metric="r2")

        assert result["promoted"] is True

    @patch("mlflow.tracking.MlflowClient")
    def test_does_not_promote_when_auto_promote_false(self, mock_client_cls: MagicMock) -> None:
        client = _make_mock_client(
            candidate_metrics={"mae": 800.0},
            champion_metrics={"mae": 1000.0},
        )
        mock_client_cls.return_value = client

        result = compare_and_promote(
            run_id="candidate-run-1", primary_metric="mae", auto_promote=False
        )

        assert result["promoted"] is False
        assert "auto_promote" in result["reason"].lower()
        client.set_registered_model_alias.assert_not_called()

    @patch("mlflow.tracking.MlflowClient")
    def test_logs_comparison_tags(self, mock_client_cls: MagicMock) -> None:
        client = _make_mock_client(champion_run_id=None)
        mock_client_cls.return_value = client

        compare_and_promote(run_id="candidate-run-1")

        tag_calls = {call.args[1]: call.args[2] for call in client.set_tag.call_args_list}
        assert tag_calls["promotion.promoted"] == "True"
        assert tag_calls["promotion.primary_metric"] == "mae"

    @patch("mlflow.tracking.MlflowClient")
    def test_handles_missing_primary_metric(self, mock_client_cls: MagicMock) -> None:
        client = _make_mock_client(
            candidate_metrics={"rmse": 1200.0},  # no "mae"
            champion_metrics={"mae": 1000.0},
        )
        mock_client_cls.return_value = client

        result = compare_and_promote(run_id="candidate-run-1", primary_metric="mae")

        assert result["promoted"] is False
        assert "missing" in result["reason"].lower()

    @patch("mlflow.tracking.MlflowClient")
    def test_returns_serializable_dict(self, mock_client_cls: MagicMock) -> None:
        client = _make_mock_client(champion_run_id=None)
        mock_client_cls.return_value = client

        result = compare_and_promote(run_id="candidate-run-1")

        assert isinstance(result, dict)
        assert "promoted" in result
        assert "reason" in result
        assert "candidate_version" in result
        assert "candidate_metrics" in result

    @patch("mlflow.tracking.MlflowClient")
    def test_raises_when_no_model_version(self, mock_client_cls: MagicMock) -> None:
        client = MagicMock()
        client.search_model_versions.return_value = []
        mock_client_cls.return_value = client

        import pytest

        with pytest.raises(ValueError, match="No model version found"):
            compare_and_promote(run_id="nonexistent-run")

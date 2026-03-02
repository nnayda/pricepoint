"""Tests for pricepoint.models.registry."""

from unittest.mock import MagicMock, patch

from pricepoint.models.registry import MODEL_NAME, log_model, promote_model


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

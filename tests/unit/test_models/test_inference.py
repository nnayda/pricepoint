"""Tests for pricepoint.models.inference."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd


class TestLoadProductionModel:
    """Tests for load_production_model."""

    @patch("mlflow.xgboost.load_model")
    @patch("mlflow.tracking.MlflowClient")
    def test_returns_model_when_production_exists(
        self,
        mock_client_cls: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.version = "3"
        mock_client.get_latest_versions.return_value = [mock_version]
        mock_client_cls.return_value = mock_client

        sentinel_model = MagicMock()
        mock_load.return_value = sentinel_model

        from pricepoint.models.inference import load_production_model

        result = load_production_model()

        assert result is sentinel_model
        mock_client.get_latest_versions.assert_called_once_with(
            "pricepoint-home-value", stages=["Production"]
        )
        mock_load.assert_called_once_with("models:/pricepoint-home-value/3")

    @patch("mlflow.tracking.MlflowClient")
    def test_returns_none_when_no_production_model(
        self,
        mock_client_cls: MagicMock,
    ) -> None:
        mock_client = MagicMock()
        mock_client.get_latest_versions.return_value = []
        mock_client_cls.return_value = mock_client

        from pricepoint.models.inference import load_production_model

        result = load_production_model()
        assert result is None

    @patch("mlflow.xgboost.load_model")
    @patch("mlflow.tracking.MlflowClient")
    def test_custom_model_name(
        self,
        mock_client_cls: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.version = "1"
        mock_client.get_latest_versions.return_value = [mock_version]
        mock_client_cls.return_value = mock_client
        mock_load.return_value = MagicMock()

        from pricepoint.models.inference import load_production_model

        load_production_model(model_name="custom-model")
        mock_client.get_latest_versions.assert_called_once_with(
            "custom-model", stages=["Production"]
        )


class TestPredictBatch:
    """Tests for predict_batch."""

    def test_returns_predictions_array(self) -> None:
        from pricepoint.models.inference import predict_batch

        model = MagicMock()
        model.predict.return_value = np.array([100000.0, 200000.0, 300000.0])

        features = pd.DataFrame(
            {"sqft": [1200, 1800, 2500], "bedrooms": [2, 3, 4]},
            index=[1, 2, 3],
        )

        result = predict_batch(model, features)

        assert isinstance(result, np.ndarray)
        assert len(result) == 3
        np.testing.assert_array_equal(result, [100000.0, 200000.0, 300000.0])

    def test_drops_non_numeric_columns(self) -> None:
        from pricepoint.models.inference import predict_batch

        model = MagicMock()
        model.predict.return_value = np.array([150000.0])

        features = pd.DataFrame(
            {"sqft": [1500], "city": ["Raleigh"], "bedrooms": [3]},
            index=[1],
        )

        predict_batch(model, features)

        # Model should only receive numeric columns
        called_df = model.predict.call_args[0][0]
        assert "city" not in called_df.columns
        assert "sqft" in called_df.columns
        assert "bedrooms" in called_df.columns


class TestScoreAllProperties:
    """Tests for score_all_properties."""

    @patch("pricepoint.models.inference.load_production_model")
    def test_returns_zero_when_no_model(
        self,
        mock_load: MagicMock,
    ) -> None:
        mock_load.return_value = None
        db = MagicMock()

        from pricepoint.models.inference import score_all_properties

        result = score_all_properties(db)
        assert result == 0
        db.execute.assert_not_called()

    @patch("pricepoint.models.inference.assemble_features")
    @patch("pricepoint.models.inference.load_production_model")
    def test_returns_zero_when_no_properties(
        self,
        mock_load: MagicMock,
        mock_assemble: MagicMock,
    ) -> None:
        mock_load.return_value = MagicMock()
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = []

        from pricepoint.models.inference import score_all_properties

        result = score_all_properties(db)
        assert result == 0
        mock_assemble.assert_not_called()

    @patch("pricepoint.models.inference.assemble_features")
    @patch("pricepoint.models.inference.load_production_model")
    def test_scores_properties_and_commits(
        self,
        mock_load: MagicMock,
        mock_assemble: MagicMock,
    ) -> None:
        model = MagicMock()
        model.predict.return_value = np.array([250000.0, 350000.0])
        mock_load.return_value = model

        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [(1,), (2,)]

        # No existing valuations
        db.query.return_value.filter.return_value.first.return_value = None

        features = pd.DataFrame(
            {"sqft": [1500, 2200], "bedrooms": [3, 4]},
            index=pd.Index([1, 2], name="property_id"),
        )
        mock_assemble.return_value = features

        from pricepoint.models.inference import score_all_properties

        result = score_all_properties(db)

        assert result == 2
        assert db.add.call_count == 2
        db.commit.assert_called_once()

    @patch("pricepoint.models.inference.assemble_features")
    @patch("pricepoint.models.inference.load_production_model")
    def test_updates_existing_valuations(
        self,
        mock_load: MagicMock,
        mock_assemble: MagicMock,
    ) -> None:
        model = MagicMock()
        model.predict.return_value = np.array([300000.0])
        mock_load.return_value = model

        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [(5,)]

        existing_val = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = existing_val

        features = pd.DataFrame(
            {"sqft": [2000]},
            index=pd.Index([5], name="property_id"),
        )
        mock_assemble.return_value = features

        from pricepoint.models.inference import score_all_properties

        result = score_all_properties(db)

        assert result == 1
        assert existing_val.value == 300000.0
        db.add.assert_not_called()
        db.commit.assert_called_once()

    @patch("pricepoint.models.inference.assemble_features")
    @patch("pricepoint.models.inference.load_production_model")
    def test_returns_zero_when_features_empty(
        self,
        mock_load: MagicMock,
        mock_assemble: MagicMock,
    ) -> None:
        mock_load.return_value = MagicMock()
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [(1,)]
        mock_assemble.return_value = pd.DataFrame()

        from pricepoint.models.inference import score_all_properties

        result = score_all_properties(db)
        assert result == 0

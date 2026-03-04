"""Tests for pricepoint.features.store."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd


class TestFeatureHash:
    """Tests for _feature_hash determinism."""

    def test_deterministic_for_same_columns(self) -> None:
        from pricepoint.features.store import _feature_hash

        h1 = _feature_hash(["sqft", "bedrooms", "lot_size"])
        h2 = _feature_hash(["sqft", "bedrooms", "lot_size"])
        assert h1 == h2

    def test_order_independent(self) -> None:
        from pricepoint.features.store import _feature_hash

        h1 = _feature_hash(["sqft", "bedrooms", "lot_size"])
        h2 = _feature_hash(["lot_size", "sqft", "bedrooms"])
        assert h1 == h2

    def test_different_columns_different_hash(self) -> None:
        from pricepoint.features.store import _feature_hash

        h1 = _feature_hash(["sqft", "bedrooms"])
        h2 = _feature_hash(["sqft", "lot_size"])
        assert h1 != h2

    def test_returns_hex_string(self) -> None:
        from pricepoint.features.store import _feature_hash

        h = _feature_hash(["a", "b"])
        assert len(h) == 64  # SHA-256 hex digest
        assert all(c in "0123456789abcdef" for c in h)


class TestSanitizeValue:
    """Tests for _sanitize_value."""

    def test_nan_becomes_none(self) -> None:
        from pricepoint.features.store import _sanitize_value

        assert _sanitize_value(float("nan")) is None

    def test_inf_becomes_none(self) -> None:
        from pricepoint.features.store import _sanitize_value

        assert _sanitize_value(float("inf")) is None
        assert _sanitize_value(float("-inf")) is None

    def test_normal_float_unchanged(self) -> None:
        from pricepoint.features.store import _sanitize_value

        assert _sanitize_value(42.5) == 42.5

    def test_non_float_unchanged(self) -> None:
        from pricepoint.features.store import _sanitize_value

        assert _sanitize_value(42) == 42
        assert _sanitize_value("hello") == "hello"


class TestSaveFeatureMatrix:
    """Tests for save_feature_matrix."""

    @patch("pricepoint.features.store.pg_insert")
    def test_saves_rows_and_commits(self, mock_pg_insert: MagicMock) -> None:
        from pricepoint.features.store import save_feature_matrix

        df = pd.DataFrame(
            {"sqft": [1500.0, 2200.0], "bedrooms": [3.0, 4.0]},
            index=pd.Index([10, 20], name="property_id"),
        )

        mock_stmt = MagicMock()
        mock_stmt.on_conflict_do_update.return_value = mock_stmt
        mock_pg_insert.return_value = mock_stmt

        db = MagicMock()
        result = save_feature_matrix(db, df)

        assert result == 2
        db.execute.assert_called_once()
        db.commit.assert_called_once()

    @patch("pricepoint.features.store.pg_insert")
    def test_converts_nan_to_none(self, mock_pg_insert: MagicMock) -> None:
        from pricepoint.features.store import save_feature_matrix

        df = pd.DataFrame(
            {"sqft": [1500.0], "bedrooms": [float("nan")]},
            index=pd.Index([10], name="property_id"),
        )

        captured_values: list = []
        mock_insert_obj = MagicMock()

        def capture_values(*args: object) -> MagicMock:
            return mock_insert_obj

        mock_insert_obj.values.side_effect = lambda rows: (
            captured_values.extend(rows) or mock_insert_obj
        )
        mock_insert_obj.on_conflict_do_update.return_value = mock_insert_obj
        mock_insert_obj.excluded = MagicMock()
        mock_pg_insert.side_effect = capture_values

        db = MagicMock()
        save_feature_matrix(db, df)

        assert captured_values[0]["features"]["bedrooms"] is None
        assert captured_values[0]["features"]["sqft"] == 1500.0

    def test_empty_dataframe_returns_zero(self) -> None:
        from pricepoint.features.store import save_feature_matrix

        db = MagicMock()
        result = save_feature_matrix(db, pd.DataFrame())

        assert result == 0
        db.execute.assert_not_called()
        db.commit.assert_not_called()

    @patch("pricepoint.features.store.pg_insert")
    def test_includes_sold_price_in_features(self, mock_pg_insert: MagicMock) -> None:
        from pricepoint.features.store import save_feature_matrix

        df = pd.DataFrame(
            {"sqft": [1500.0], "sold_price": [300000.0]},
            index=pd.Index([10], name="property_id"),
        )

        captured_values: list = []
        mock_insert_obj = MagicMock()

        mock_insert_obj.values.side_effect = lambda rows: (
            captured_values.extend(rows) or mock_insert_obj
        )
        mock_insert_obj.on_conflict_do_update.return_value = mock_insert_obj
        mock_insert_obj.excluded = MagicMock()
        mock_pg_insert.return_value = mock_insert_obj

        db = MagicMock()
        save_feature_matrix(db, df)

        assert captured_values[0]["features"]["sold_price"] == 300000.0
        assert captured_values[0]["features"]["sqft"] == 1500.0

    @patch("pricepoint.features.store.pg_insert")
    def test_excludes_sold_price_from_feature_hash(self, mock_pg_insert: MagicMock) -> None:
        """Feature hash should not change when sold_price values differ."""
        from pricepoint.features.store import _feature_hash, save_feature_matrix

        df = pd.DataFrame(
            {"sqft": [1500.0], "sold_price": [300000.0]},
            index=pd.Index([10], name="property_id"),
        )

        captured_values: list = []
        mock_insert_obj = MagicMock()

        mock_insert_obj.values.side_effect = lambda rows: (
            captured_values.extend(rows) or mock_insert_obj
        )
        mock_insert_obj.on_conflict_do_update.return_value = mock_insert_obj
        mock_insert_obj.excluded = MagicMock()
        mock_pg_insert.return_value = mock_insert_obj

        db = MagicMock()
        save_feature_matrix(db, df)

        expected_hash = _feature_hash(["sqft"])
        assert captured_values[0]["feature_hash"] == expected_hash


class TestLoadFeatureMatrix:
    """Tests for load_feature_matrix."""

    def test_returns_dataframe_indexed_by_property_id(self) -> None:
        from pricepoint.features.store import load_feature_matrix

        rec1 = MagicMock()
        rec1.property_id = 10
        rec1.features = {"sqft": 1500.0, "bedrooms": 3.0}

        rec2 = MagicMock()
        rec2.property_id = 20
        rec2.features = {"sqft": 2200.0, "bedrooms": 4.0}

        db = MagicMock()
        db.query.return_value.all.return_value = [rec1, rec2]

        result = load_feature_matrix(db)

        assert list(result.index) == [10, 20]
        assert result.index.name == "property_id"
        assert result.loc[10, "sqft"] == 1500.0
        assert result.loc[20, "bedrooms"] == 4.0

    def test_casts_categorical_columns(self) -> None:
        from pricepoint.features.store import load_feature_matrix

        rec = MagicMock()
        rec.property_id = 10
        rec.features = {"sqft": 1500.0, "parking_type": "Attached", "facade_type": "Brick"}

        db = MagicMock()
        db.query.return_value.all.return_value = [rec]

        result = load_feature_matrix(db)

        assert result["parking_type"].dtype.name == "category"
        assert result["facade_type"].dtype.name == "category"

    def test_filters_by_property_ids(self) -> None:
        from pricepoint.features.store import load_feature_matrix

        db = MagicMock()
        query_mock = MagicMock()
        db.query.return_value = query_mock
        filter_mock = MagicMock()
        query_mock.filter.return_value = filter_mock
        filter_mock.all.return_value = []

        result = load_feature_matrix(db, property_ids=[10, 20])

        assert result.empty
        query_mock.filter.assert_called_once()

    def test_returns_empty_when_no_records(self) -> None:
        from pricepoint.features.store import load_feature_matrix

        db = MagicMock()
        db.query.return_value.all.return_value = []

        result = load_feature_matrix(db)
        assert result.empty


class TestLoadSinglePropertyFeatures:
    """Tests for load_single_property_features."""

    def test_returns_single_row(self) -> None:
        from pricepoint.features.store import load_single_property_features

        rec = MagicMock()
        rec.property_id = 42
        rec.features = {"sqft": 1800.0, "bedrooms": 3.0}

        db = MagicMock()
        query_mock = MagicMock()
        db.query.return_value = query_mock
        filter_mock = MagicMock()
        query_mock.filter.return_value = filter_mock
        filter_mock.all.return_value = [rec]

        result = load_single_property_features(db, 42)

        assert len(result) == 1
        assert result.index[0] == 42
        assert result.loc[42, "sqft"] == 1800.0

    def test_returns_empty_when_not_found(self) -> None:
        from pricepoint.features.store import load_single_property_features

        db = MagicMock()
        query_mock = MagicMock()
        db.query.return_value = query_mock
        filter_mock = MagicMock()
        query_mock.filter.return_value = filter_mock
        filter_mock.all.return_value = []

        result = load_single_property_features(db, 999)
        assert result.empty


class TestDeletePropertyFeatures:
    """Tests for delete_property_features."""

    def test_deletes_and_commits(self) -> None:
        from pricepoint.features.store import delete_property_features

        db = MagicMock()
        db.execute.return_value.rowcount = 3

        result = delete_property_features(db, [1, 2, 3])

        assert result == 3
        db.execute.assert_called_once()
        db.commit.assert_called_once()

    def test_empty_list_returns_zero(self) -> None:
        from pricepoint.features.store import delete_property_features

        db = MagicMock()
        result = delete_property_features(db, [])

        assert result == 0
        db.execute.assert_not_called()

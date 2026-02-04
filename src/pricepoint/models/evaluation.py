"""Model evaluation — compute metrics on held-out test data."""

import pandas as pd


def evaluate_model(
    *, model: object, test_features: pd.DataFrame, target_col: str = "assessed_value"
) -> dict:
    """Evaluate a trained model on test data.

    Returns a dict of metric names to values (MAE, RMSE, R², MAPE).
    """
    raise NotImplementedError

"""Model training pipeline.

Trains a home-value forecasting model on the assembled feature matrix.
"""

import pandas as pd


def train_model(*, features: pd.DataFrame, target_col: str = "assessed_value") -> object:
    """Train a forecasting model on the given feature matrix.

    Returns a fitted model object.
    """
    raise NotImplementedError

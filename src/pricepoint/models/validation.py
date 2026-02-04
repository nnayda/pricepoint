"""Model validation — cross-validation and holdout evaluation."""

import pandas as pd


def cross_validate(*, features: pd.DataFrame, target_col: str = "assessed_value") -> dict:
    """Run k-fold cross-validation and return aggregated metrics.

    Returns a dict of metric names to values.
    """
    raise NotImplementedError

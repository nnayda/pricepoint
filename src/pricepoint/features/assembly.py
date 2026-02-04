"""Feature assembly — combine all feature sets into a single training matrix."""

import pandas as pd


def assemble_features(*, property_ids: list[int] | None = None) -> pd.DataFrame:
    """Join geospatial, housing, and economic features into a unified feature matrix.

    Returns a DataFrame indexed by property ID, ready for model training.
    """
    raise NotImplementedError

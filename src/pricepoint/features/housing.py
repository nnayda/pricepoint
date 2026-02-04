"""Housing feature engineering.

Transforms raw housing data into model-ready features:
price per sqft, days on market, listing premium over assessment, etc.
"""

import pandas as pd


def build_housing_features(*, property_ids: list[int] | None = None) -> pd.DataFrame:
    """Compute housing features for the given properties.

    Returns a DataFrame indexed by property ID.
    """
    raise NotImplementedError

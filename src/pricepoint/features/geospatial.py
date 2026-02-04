"""Geospatial feature engineering.

Transforms raw geospatial data into model-ready features:
distance to nearest school, crime density within radius, nearby amenity counts, etc.
"""

import pandas as pd


def build_geospatial_features(*, property_ids: list[int] | None = None) -> pd.DataFrame:
    """Compute geospatial features for the given properties.

    Returns a DataFrame indexed by property ID.
    """
    raise NotImplementedError

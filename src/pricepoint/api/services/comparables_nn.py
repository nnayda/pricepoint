"""Nearest-neighbour comparables ranking using the assembled feature matrix.

Pure function — no database dependency. Operates on a pandas DataFrame
produced by ``assemble_features``.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.metrics import pairwise_distances
from sklearn.preprocessing import StandardScaler

from pricepoint.features.housing import CATEGORICAL_COLUMNS

logger = logging.getLogger(__name__)


def find_nearest_comparables(
    feature_df: pd.DataFrame,
    subject_id: int,
    n: int = 5,
) -> list[tuple[int, float]]:
    """Rank candidate properties by Euclidean distance to the subject.

    Parameters
    ----------
    feature_df:
        Feature matrix indexed by ``property_id``.  Must include the subject.
    subject_id:
        The property_id of the subject property.
    n:
        Number of nearest neighbours to return.

    Returns
    -------
    list of (property_id, distance) tuples sorted ascending by distance.
    The subject itself is excluded from results.
    """
    if subject_id not in feature_df.index:
        logger.warning("Subject %d not in feature matrix", subject_id)
        return []

    df = feature_df.copy()

    # Drop target / identifier columns that shouldn't influence similarity
    drop_cols = [c for c in ("sold_price", "census_tract_geoid") if c in df.columns]
    if drop_cols:
        df = df.drop(columns=drop_cols)

    # One-hot encode categoricals present in the dataframe
    cat_cols = [c for c in CATEGORICAL_COLUMNS if c in df.columns]
    if cat_cols:
        df = pd.get_dummies(df, columns=cat_cols, dummy_na=False)

    # Separate numeric and boolean/one-hot columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    bool_cols = df.select_dtypes(include=["bool"]).columns.tolist()

    # Convert booleans to float
    for col in bool_cols:
        df[col] = df[col].astype(float)

    # Impute NaN: column median for numeric, 0 for one-hot / boolean
    for col in df.columns:
        if df[col].isna().any():
            if col in numeric_cols:
                median = df[col].median()
                df[col] = df[col].fillna(median if pd.notna(median) else 0.0)
            else:
                df[col] = df[col].fillna(0.0)

    # Ensure all columns are numeric after processing
    df = df.apply(pd.to_numeric, errors="coerce").fillna(0.0)

    # Standardise
    scaler = StandardScaler()
    scaled = scaler.fit_transform(df)

    # Compute distances from the subject row
    subject_idx = df.index.get_loc(subject_id)
    subject_row = scaled[subject_idx].reshape(1, -1)
    distances = pairwise_distances(subject_row, scaled, metric="euclidean").flatten()

    # Build (property_id, distance) pairs, excluding the subject
    results: list[tuple[int, float]] = []
    for idx, pid in enumerate(df.index):
        if pid == subject_id:
            continue
        results.append((int(pid), float(distances[idx])))

    results.sort(key=lambda x: x[1])
    return results[:n]

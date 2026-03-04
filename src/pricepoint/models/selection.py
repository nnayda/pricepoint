"""Automatic feature selection.

Two-stage pipeline:
1. Correlation threshold filter — drops one of each highly-correlated pair.
2. Permutation importance filter — drops features with zero or negative
   contribution (optional, runs post-training).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

CORRELATION_THRESHOLD = 0.90
MIN_PERMUTATION_IMPORTANCE = 0.0


def drop_correlated(x: pd.DataFrame, threshold: float = CORRELATION_THRESHOLD) -> pd.DataFrame:
    """Drop one feature from each highly-correlated pair.

    For every pair with |Pearson r| > *threshold*, the feature with lower
    variance is removed (it carries less information).

    Parameters
    ----------
    x : pd.DataFrame
        Numeric feature matrix.
    threshold : float
        Absolute correlation above which one feature is dropped.

    Returns
    -------
    pd.DataFrame
        Feature matrix with correlated columns removed.
    """
    numeric = x.select_dtypes(include="number")
    if numeric.shape[1] < 2:
        return x

    corr = numeric.corr().abs()
    upper = corr.where(np.triu(np.ones(corr.shape, dtype=bool), k=1))

    to_drop: set[str] = set()
    for col in upper.columns:
        correlated = upper.index[upper[col] > threshold].tolist()
        for other in correlated:
            if other in to_drop or col in to_drop:
                continue
            # Drop the feature with lower variance
            if numeric[col].var() >= numeric[other].var():
                to_drop.add(other)
                logger.info(
                    "Dropping '%s' (corr=%.3f with '%s', lower variance)",
                    other,
                    corr.loc[other, col],
                    col,
                )
            else:
                to_drop.add(col)
                logger.info(
                    "Dropping '%s' (corr=%.3f with '%s', lower variance)",
                    col,
                    corr.loc[other, col],
                    other,
                )

    if to_drop:
        logger.info("Correlation filter removed %d features: %s", len(to_drop), sorted(to_drop))
        x = x.drop(columns=list(to_drop))

    return x


def drop_unimportant(
    model: object,
    x: pd.DataFrame,
    y: pd.Series,
    *,
    min_importance: float = MIN_PERMUTATION_IMPORTANCE,
    n_repeats: int = 5,
    random_state: int = 42,
) -> list[str]:
    """Identify features with negligible permutation importance.

    Parameters
    ----------
    model : fitted estimator
        A model that implements ``predict``.
    x : pd.DataFrame
        Test features.
    y : pd.Series
        Test target.
    min_importance : float
        Features with mean importance <= this are flagged for removal.
    n_repeats : int
        Number of permutation repeats.
    random_state : int
        Random seed for reproducibility.

    Returns
    -------
    list[str]
        Column names to drop.
    """
    from sklearn.inspection import permutation_importance

    result = permutation_importance(
        model,
        x,
        y,
        n_repeats=n_repeats,
        random_state=random_state,
        scoring="neg_mean_absolute_error",
    )

    drop_cols: list[str] = []
    for i, col in enumerate(x.columns):
        mean_imp = float(result.importances_mean[i])
        if mean_imp <= min_importance:
            drop_cols.append(col)
            logger.info(
                "Permutation importance of '%s' is %.4f (<= %.4f) — flagged for removal",
                col,
                mean_imp,
                min_importance,
            )

    if drop_cols:
        logger.info("Permutation filter flagged %d features: %s", len(drop_cols), sorted(drop_cols))

    return drop_cols


def select_features(
    x: pd.DataFrame,
    *,
    correlation_threshold: float = CORRELATION_THRESHOLD,
) -> pd.DataFrame:
    """Run correlation-based feature selection.

    Parameters
    ----------
    x : pd.DataFrame
        Feature matrix (no target column).
    correlation_threshold : float
        Threshold for the correlation filter.

    Returns
    -------
    pd.DataFrame
        Filtered feature matrix.
    """
    return drop_correlated(x, threshold=correlation_threshold)

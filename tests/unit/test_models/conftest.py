"""Shared fixtures for model tests."""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture()
def synthetic_df() -> pd.DataFrame:
    """Create a synthetic feature DataFrame for testing.

    Generates 200 rows with numeric features that have a rough linear
    relationship to the target, plus some noise.  Includes a categorical
    column (parking_type) to exercise XGBoost categorical support.
    """
    rng = np.random.RandomState(42)
    n = 200
    sqft = rng.uniform(800, 4000, n)
    bedrooms = rng.randint(1, 6, n).astype(float)
    bathrooms = rng.randint(1, 4, n).astype(float)
    lot_size = rng.uniform(2000, 20000, n)
    year_built = rng.randint(1950, 2023, n).astype(float)
    noise = rng.normal(0, 10000, n)

    sold_price = 50000 + 150 * sqft + 5000 * bedrooms + 8000 * bathrooms + noise

    parking_choices = ["Attached", "Detached", "Carport", "None"]
    parking_type = pd.Categorical(rng.choice(parking_choices, n))

    return pd.DataFrame(
        {
            "sqft": sqft,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "lot_size": lot_size,
            "year_built": year_built,
            "parking_type": parking_type,
            "sold_price": sold_price,
        }
    )


@pytest.fixture()
def synthetic_df_with_nan(synthetic_df: pd.DataFrame) -> pd.DataFrame:
    """Synthetic DataFrame with some NaN values and a high-NaN column."""
    df = synthetic_df.copy()
    rng = np.random.RandomState(99)
    # Add a column that's >95% NaN (should be dropped)
    mostly_nan = np.full(len(df), np.nan)
    mostly_nan[: len(df) // 25] = rng.uniform(0, 1, len(df) // 25)  # 4% non-null → 96% NaN
    df["mostly_nan_col"] = mostly_nan

    # Add a structural-null column at ~50% NaN to test indicator generation
    assoc_fee = np.full(len(df), np.nan)
    assoc_fee[: len(df) // 2] = rng.uniform(50, 500, len(df) // 2)
    df["association_fee"] = assoc_fee

    # Sprinkle a few NaN values in existing columns
    mask = rng.random(len(df)) < 0.05
    df.loc[mask, "lot_size"] = np.nan
    return df


@pytest.fixture()
def synthetic_df_with_strings(synthetic_df: pd.DataFrame) -> pd.DataFrame:
    """Synthetic DataFrame with a raw string column that should be dropped.

    The 'parking_type' column (category dtype) should be kept, while the
    raw 'city' string column should be dropped.
    """
    df = synthetic_df.copy()
    df["city"] = "Raleigh"
    return df

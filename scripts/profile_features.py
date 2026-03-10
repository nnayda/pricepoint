"""Generate an interactive YData-Profiling EDA report from the feature matrix."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an interactive HTML profiling report for the feature matrix."
    )
    parser.add_argument(
        "-o",
        "--output",
        default="reports/eda_profile.html",
        help="Output HTML path (default: reports/eda_profile.html)",
    )
    parser.add_argument(
        "--minimal",
        action="store_true",
        help="Skip expensive computations (interactions, tail analysis)",
    )
    parser.add_argument(
        "--title",
        default="PricePoint Feature Matrix — EDA Profile",
        help="Report title",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Random sample N rows for faster profiling",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    import pandas as pd
    from ydata_profiling import ProfileReport

    from pricepoint.db.engine import SessionLocal
    from pricepoint.features.housing import CATEGORICAL_COLUMNS
    from pricepoint.features.store import load_feature_matrix
    from pricepoint.models.training import prepare_features

    # Load feature matrix from DB
    db = SessionLocal()
    try:
        df = load_feature_matrix(db)
    finally:
        db.close()

    # Drop rows without a target value
    df = df.dropna(subset=["sold_price"])

    if len(df) == 0:
        print("No rows with sold_price found in feature matrix.", file=sys.stderr)
        sys.exit(1)

    # Optional random sampling
    if args.sample is not None and args.sample < len(df):
        df = df.sample(n=args.sample, random_state=42)

    # Clean columns using the same pipeline as training (but raw values)
    x, y = prepare_features(df, "sold_price", log_transform_target=False, filter_outliers=False)

    # Recombine so profiler sees feature-target correlations
    df = pd.concat([x, y], axis=1)

    # Build type schema for known categorical columns
    type_schema = {col: "categorical" for col in CATEGORICAL_COLUMNS if col in df.columns}

    report = ProfileReport(df, title=args.title, minimal=args.minimal, type_schema=type_schema)

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report.to_file(output_path)
    print(f"Report saved to {output_path}")


if __name__ == "__main__":
    main()

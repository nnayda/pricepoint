"""Dump OpenAPI schema JSON from the FastAPI app.

Usage:
    uv run python scripts/dump_openapi.py               # prints to stdout
    uv run python scripts/dump_openapi.py -o schema.json # writes to file
"""

from __future__ import annotations

import argparse
import json
import sys
from unittest.mock import MagicMock, patch


def main() -> None:
    parser = argparse.ArgumentParser(description="Dump OpenAPI schema as JSON")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Output file path (default: stdout)",
    )
    args = parser.parse_args()

    # Mock out the database engine module so it doesn't try to connect
    mock_engine_module = MagicMock()
    mock_engine_module.engine = MagicMock()
    mock_engine_module.SessionLocal = MagicMock()

    with patch.dict(
        "sys.modules",
        {"pricepoint.db.engine": mock_engine_module},
    ):
        from pricepoint.api.main import create_app

        app = create_app()

    schema = app.openapi()
    json_str = json.dumps(schema, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(json_str)
            f.write("\n")
        print(f"OpenAPI schema written to {args.output}", file=sys.stderr)
    else:
        print(json_str)


if __name__ == "__main__":
    main()

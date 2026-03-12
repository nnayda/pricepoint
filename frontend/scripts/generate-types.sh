#!/usr/bin/env bash
# Generate TypeScript types from the FastAPI OpenAPI schema.
#
# Usage:
#   ./frontend/scripts/generate-types.sh          # generate types
#   ./frontend/scripts/generate-types.sh --check   # check for drift (CI mode)
#
# Requires: uv (Python), npx (Node.js)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_DIR="$(cd "$FRONTEND_DIR/.." && pwd)"

OUTPUT_FILE="$FRONTEND_DIR/src/types/api.generated.ts"
SCHEMA_FILE="$PROJECT_DIR/.openapi-schema.json"

# Step 1: Dump OpenAPI schema from FastAPI app
echo "Dumping OpenAPI schema..."
(cd "$PROJECT_DIR" && uv run python scripts/dump_openapi.py -o "$SCHEMA_FILE") 2>/dev/null

# Step 2: Generate TypeScript types from the schema
echo "Generating TypeScript types..."
npx --prefix "$FRONTEND_DIR" openapi-typescript "$SCHEMA_FILE" -o "$OUTPUT_FILE" 2>/dev/null

# Clean up temp schema file
rm -f "$SCHEMA_FILE"

# Step 2b: Format with Prettier so output matches committed style
npx --prefix "$FRONTEND_DIR" prettier --write "$OUTPUT_FILE" > /dev/null 2>&1

# Step 3: Check mode — fail if generated types differ from committed version
if [[ "${1:-}" == "--check" ]]; then
    echo "Checking for API contract drift..."
    if git -C "$PROJECT_DIR" diff --exit-code -- "$OUTPUT_FILE" > /dev/null 2>&1; then
        echo "API contract is in sync."
    else
        echo ""
        echo "ERROR: API contract drift detected!"
        echo "The generated types differ from the committed version."
        echo ""
        echo "To fix, run:"
        echo "  ./frontend/scripts/generate-types.sh"
        echo "  git add frontend/src/types/api.generated.ts"
        echo "  git commit"
        echo ""
        git -C "$PROJECT_DIR" diff -- "$OUTPUT_FILE"
        exit 1
    fi
else
    echo "Types generated at: $OUTPUT_FILE"
fi

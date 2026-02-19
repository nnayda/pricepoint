#!/usr/bin/env bash
# Run all k6 performance tests sequentially and print a summary.
#
# Usage:
#   ./run_all.sh                              # default: http://localhost:8000
#   BASE_URL=http://staging:8000 ./run_all.sh  # override target URL

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_URL="${BASE_URL:-http://localhost:8000}"

# Verify k6 is installed
if ! command -v k6 &>/dev/null; then
  echo "ERROR: k6 is not installed. Install it from https://k6.io/docs/get-started/installation/"
  exit 1
fi

TESTS=(
  "geocode.js:Geocode endpoint"
  "property.js:Property details endpoint"
  "spatial.js:Spatial queries (crime/POIs)"
  "forecast.js:ML forecast endpoint"
  "spike.js:Spike test (all endpoints)"
)

PASSED=0
FAILED=0
RESULTS=()

echo "============================================"
echo " PricePoint Performance Tests"
echo " Target: ${BASE_URL}"
echo " Started: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "============================================"
echo ""

for entry in "${TESTS[@]}"; do
  IFS=":" read -r file label <<< "${entry}"
  echo "--------------------------------------------"
  echo " Running: ${label} (${file})"
  echo "--------------------------------------------"

  if k6 run --env "BASE_URL=${BASE_URL}" "${SCRIPT_DIR}/${file}"; then
    RESULTS+=("PASS  ${label}")
    PASSED=$((PASSED + 1))
  else
    RESULTS+=("FAIL  ${label}")
    FAILED=$((FAILED + 1))
  fi

  echo ""
done

echo "============================================"
echo " Summary"
echo "============================================"
for result in "${RESULTS[@]}"; do
  echo "  ${result}"
done
echo ""
echo "  Total: $((PASSED + FAILED))  Passed: ${PASSED}  Failed: ${FAILED}"
echo "  Finished: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "============================================"

# Exit with non-zero if any test failed
if [ "${FAILED}" -gt 0 ]; then
  exit 1
fi

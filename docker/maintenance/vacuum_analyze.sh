#!/bin/bash
# PostGIS maintenance: VACUUM ANALYZE + REINDEX for tables with spatial indexes
set -euo pipefail

PGHOST="${PGHOST:-postgres}"
PGUSER="${PGUSER:-pricepoint}"
PGDATABASE="${PGDATABASE:-pricepoint}"

echo "Running VACUUM ANALYZE on all tables..."
psql -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" -c "VACUUM ANALYZE;"

echo "Reindexing spatial indexes..."
psql -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" -c "REINDEX DATABASE $PGDATABASE;"

echo "Maintenance complete."

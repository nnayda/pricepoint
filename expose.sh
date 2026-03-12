#!/bin/bash

# Configuration
NAMESPACE="claude-sandbox"
LABEL_SELECTOR="app=claude-dev"

# 1. Find the Pod Name automatically
echo "🔍 Looking for pod in namespace '$NAMESPACE'..."
POD_NAME=$(kubectl get pods -n "$NAMESPACE" -l "$LABEL_SELECTOR" -o jsonpath="{.items[0].metadata.name}")

if [ -z "$POD_NAME" ]; then
  echo "❌ Error: No pod found with label '$LABEL_SELECTOR' in namespace '$NAMESPACE'."
  exit 1
fi

echo "✅ Found pod: $POD_NAME"

# 2. Set up Port Forwarding
echo "🚀 Forwarding ports..."
echo "   - Frontend:      http://localhost:3000"
echo "   - API:           http://localhost:8000"
echo "   - MLFlow:        http://localhost:5001"
echo "   - PgAdmin:       http://localhost:5050"
echo "   - Minio Console: http://localhost:9001"
echo "   - Airflow:       http://localhost:8080"
echo "   - Postgis:       http://localhost:5432"
echo "   - Valkey (Redis): localhost:6379"

# The command that does the work
kubectl port-forward -n "$NAMESPACE" "$POD_NAME" \
  3000:3000 \
  8000:8000 \
  5001:5001 \
  5050:5050 \
  5432:5432 \
  9000:9000 \
  9001:9001 \
  8080:8080 \
  3001:8787 \
  3002:5173 \
  6379:6379
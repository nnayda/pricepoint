FROM python:3.12-slim

# Split heavy installs into separate layers to reduce peak memory during commit
RUN pip install --no-cache-dir psycopg2-binary boto3
RUN pip install --no-cache-dir mlflow

EXPOSE 5000

# Use shell form so environment variables are expanded at runtime
CMD mlflow server \
    --host 0.0.0.0 \
    --port 5000 \
    --backend-store-uri "${MLFLOW_BACKEND_STORE_URI:-sqlite:///mlflow.db}" \
    --default-artifact-root "${MLFLOW_ARTIFACT_ROOT:-./mlruns}"

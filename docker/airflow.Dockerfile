FROM apache/airflow:3.0.2-python3.12

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*
USER airflow

COPY pyproject.toml /opt/airflow/
COPY src/ /opt/airflow/src/

ARG AIRFLOW_CONSTRAINTS=https://raw.githubusercontent.com/apache/airflow/constraints-3.0.2/constraints-3.12.txt
RUN pip install --no-cache-dir "apache-airflow-providers-fab" --constraint "${AIRFLOW_CONSTRAINTS}" && \
    pip install --no-cache-dir --no-deps -e "/opt/airflow"

COPY dags/ /opt/airflow/dags/

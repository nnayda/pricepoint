FROM apache/airflow:3.0.2-python3.12

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*
USER airflow

COPY pyproject.toml /opt/airflow/
COPY src/ /opt/airflow/src/

RUN pip install --no-cache-dir apache-airflow-providers-fab && \
    pip install --no-cache-dir --no-deps -e "/opt/airflow"

COPY dags/ /opt/airflow/dags/

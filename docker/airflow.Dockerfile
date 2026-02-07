FROM apache/airflow:3.0.2-python3.12

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*
USER airflow

ARG AIRFLOW_CONSTRAINTS=https://raw.githubusercontent.com/apache/airflow/constraints-3.0.2/constraints-3.12.txt
RUN pip install --no-cache-dir "apache-airflow-providers-fab" --constraint "${AIRFLOW_CONSTRAINTS}"

COPY src/ /opt/airflow/src/
COPY dags/ /opt/airflow/dags/

# Make pricepoint importable via PYTHONPATH instead of pip install to avoid
# SQLAlchemy version conflicts (Airflow 3.0 pins SQLAlchemy 1.4, pricepoint
# requires 2.0+).  DAGs use deferred imports inside @task functions, so the
# scheduler can parse them without loading pricepoint's dependencies.
ENV PYTHONPATH="/opt/airflow/src:${PYTHONPATH}"

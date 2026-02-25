FROM apache/airflow:3.1.7-python3.12

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    # GeoPandas system dependencies
    gdal-bin libgdal-dev libgeos-dev libproj-dev && \
    rm -rf /var/lib/apt/lists/*
USER airflow

ARG AIRFLOW_CONSTRAINTS=https://raw.githubusercontent.com/apache/airflow/constraints-3.1.7/constraints-3.12.txt
RUN pip install --no-cache-dir "apache-airflow-providers-fab" --constraint "${AIRFLOW_CONSTRAINTS}"

# Install pricepoint dependencies (excluding packages that conflict with Airflow's pinned versions)
# Note: SQLAlchemy and FastAPI are already provided by Airflow, skip those to avoid conflicts
RUN pip install --no-cache-dir \
    "geopandas>=1.0,<2" \
    "shapely>=2.0,<3" \
    "geoalchemy2>=0.15,<1" \
    "psycopg2-binary>=2.9,<3" \
    "httpx>=0.27,<1" \
    "odsclient>=0.8,<1" \
    "redis[hiredis]>=5.0,<6" \
    "boto3>=1.34,<2" \
    "pydantic-settings>=2.3,<3" \
    "mlflow>=2.14,<3" \
    "beautifulsoup4>=4.12,<5" \
    "lxml>=5.0,<6" \
    "fredapi>=0.5,<1" \
    "duckdb>=1.0,<2"

COPY src/ /opt/airflow/src/
COPY dags/ /opt/airflow/dags/

# Make pricepoint importable via PYTHONPATH instead of pip install to avoid
# SQLAlchemy version conflicts (Airflow 3.0 pins SQLAlchemy 1.4, pricepoint
# requires 2.0+).  DAGs use deferred imports inside @task functions, so the
# scheduler can parse them without loading pricepoint's dependencies.
ENV PYTHONPATH="/opt/airflow/src:${PYTHONPATH}"

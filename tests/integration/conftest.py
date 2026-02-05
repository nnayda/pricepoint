"""Integration test fixtures using testcontainers."""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from pricepoint.db.models import Base

_docker_available = True
try:
    from testcontainers.minio import MinioContainer
    from testcontainers.postgres import PostgresContainer
except Exception:
    _docker_available = False

skip_no_docker = pytest.mark.skipif(
    not _docker_available,
    reason="testcontainers not available",
)


# ---------------------------------------------------------------------------
# PostGIS
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def postgis_container():
    """Start a PostGIS container for the test session."""
    try:
        container = PostgresContainer(
            image="postgis/postgis:17-3.5",
            username="test",
            password="test",
            dbname="test",
        )
        with container:
            yield container
    except Exception as exc:
        pytest.skip(f"Could not start PostGIS container: {exc}")


@pytest.fixture(scope="session")
def db_engine(postgis_container):
    """Create a SQLAlchemy engine connected to the test PostGIS container."""
    url = postgis_container.get_connection_url()
    engine = create_engine(url, pool_pre_ping=True)

    # Enable PostGIS extension
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.commit()

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Provide a transactional database session that rolls back after each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# MinIO / S3
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def minio_container():
    """Start a MinIO container for the test session."""
    try:
        container = MinioContainer()
        with container:
            yield container
    except Exception as exc:
        pytest.skip(f"Could not start MinIO container: {exc}")


@pytest.fixture
def s3_client(minio_container):
    """Provide a boto3 S3 client connected to the MinIO testcontainer."""
    import boto3

    client = boto3.client(
        "s3",
        endpoint_url=f"http://{minio_container.get_container_host_ip()}:{minio_container.get_exposed_port(9000)}",
        aws_access_key_id=minio_container.access_key,
        aws_secret_access_key=minio_container.secret_key,
        region_name="us-east-1",
    )
    return client

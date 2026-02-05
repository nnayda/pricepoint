"""Integration tests for Settings with S3 endpoint configuration."""

from pricepoint.config.settings import Settings


def test_settings_accepts_custom_s3_endpoint(minio_container):
    """Settings should accept a custom s3_endpoint_url pointing at MinIO."""
    endpoint = (
        f"http://{minio_container.get_container_host_ip()}:{minio_container.get_exposed_port(9000)}"
    )
    settings = Settings(
        _env_file=None,
        database_url="postgresql://test:test@localhost:5432/test",
        s3_endpoint_url=endpoint,
    )
    assert settings.s3_endpoint_url == endpoint

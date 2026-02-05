"""Tests for application configuration."""

from pricepoint.config.settings import Settings


def test_settings_defaults():
    """Settings should have sensible defaults when no env vars are set."""
    settings = Settings(
        _env_file=None,
        database_url="postgresql://pricepoint:pricepoint@localhost:5432/pricepoint",
    )
    assert "postgresql" in settings.database_url
    assert settings.api_port == 8000
    assert settings.s3_bucket == "pricepoint-data"


def test_settings_override(monkeypatch):
    """Settings should read from environment variables."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@db:5432/testdb")
    monkeypatch.setenv("API_PORT", "9000")
    settings = Settings(_env_file=None)
    assert settings.database_url == "postgresql://test:test@db:5432/testdb"
    assert settings.api_port == 9000

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


def test_settings_valkey_url_defaults_to_none(monkeypatch):
    """valkey_url should default to None when not set."""
    monkeypatch.delenv("VALKEY_URL", raising=False)
    settings = Settings(
        _env_file=None,
        database_url="postgresql://pricepoint:pricepoint@localhost:5432/pricepoint",
    )
    assert settings.valkey_url is None


def test_settings_valkey_url_from_env(monkeypatch):
    """valkey_url should be read from the VALKEY_URL env var."""
    monkeypatch.setenv("VALKEY_URL", "redis://valkey:6379/0")
    settings = Settings(_env_file=None)
    assert settings.valkey_url == "redis://valkey:6379/0"


def test_settings_override(monkeypatch):
    """Settings should read from environment variables."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@db:5432/testdb")
    monkeypatch.setenv("API_PORT", "9000")
    settings = Settings(_env_file=None)
    assert settings.database_url == "postgresql://test:test@db:5432/testdb"
    assert settings.api_port == 9000


def test_tiger_settings_defaults():
    """TIGER/Line settings should have correct defaults for NC/Wake County."""
    settings = Settings(
        _env_file=None,
        database_url="postgresql://pricepoint:pricepoint@localhost:5432/pricepoint",
    )
    assert settings.tiger_base_url == "https://www2.census.gov/geo/tiger"
    assert settings.tiger_year == 2025
    assert settings.tiger_state_fips == "37"
    assert settings.tiger_county_fips == "183"

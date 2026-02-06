"""Tests for .env and .env.example configuration files."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE_FILE = PROJECT_ROOT / ".env.example"


def _parse_env(path: Path) -> dict[str, str]:
    """Parse a .env file into a dict of key-value pairs (ignoring comments)."""
    result: dict[str, str] = {}
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, _, value = stripped.partition("=")
        result[key] = value
    return result


class TestValkeyUrl:
    """Verify VALKEY_URL is present in env files."""

    def test_valkey_url_in_env_example(self):
        env = _parse_env(ENV_EXAMPLE_FILE)
        assert "VALKEY_URL" in env
        assert env["VALKEY_URL"] == "redis://valkey:6379/0"

    def test_valkey_url_in_env(self):
        env = _parse_env(ENV_FILE)
        assert "VALKEY_URL" in env
        assert env["VALKEY_URL"] == "redis://valkey:6379/0"

    def test_env_and_example_valkey_url_match(self):
        env = _parse_env(ENV_FILE)
        example = _parse_env(ENV_EXAMPLE_FILE)
        assert env["VALKEY_URL"] == example["VALKEY_URL"]

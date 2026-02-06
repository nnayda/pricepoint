"""Tests for docker-compose.yml service definitions."""

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"


def _load_compose() -> dict:
    return yaml.safe_load(COMPOSE_FILE.read_text())


class TestValkeyService:
    """Verify the Valkey service is correctly configured."""

    def test_valkey_service_exists(self):
        compose = _load_compose()
        assert "valkey" in compose["services"]

    def test_valkey_image(self):
        svc = _load_compose()["services"]["valkey"]
        assert svc["image"] == "valkey/valkey:8-alpine"

    def test_valkey_port_mapping(self):
        svc = _load_compose()["services"]["valkey"]
        assert "6379:6379" in svc["ports"]

    def test_valkey_profile_infra(self):
        svc = _load_compose()["services"]["valkey"]
        assert "infra" in svc["profiles"]

    def test_valkey_healthcheck(self):
        svc = _load_compose()["services"]["valkey"]
        hc = svc["healthcheck"]
        assert hc["test"] == ["CMD", "valkey-cli", "ping"]
        assert "interval" in hc
        assert "timeout" in hc
        assert "retries" in hc

    def test_valkey_on_pricepoint_network(self):
        svc = _load_compose()["services"]["valkey"]
        assert "pricepoint" in svc["networks"]

    def test_valkey_volume_defined(self):
        compose = _load_compose()
        assert "valkeydata" in compose["volumes"]
        svc = compose["services"]["valkey"]
        assert any("valkeydata" in v for v in svc["volumes"])

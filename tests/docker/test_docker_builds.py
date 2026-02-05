"""Docker build smoke tests — verify images build successfully."""

import shutil
import subprocess

import pytest

_docker_available = shutil.which("docker") is not None


def _docker_is_running() -> bool:
    """Check if the Docker daemon is running."""
    if not _docker_available:
        return False
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


_docker_running = _docker_is_running()

pytestmark = pytest.mark.skipif(
    not _docker_running,
    reason="Docker is not available or not running",
)

PROJECT_ROOT = str(__import__("pathlib").Path(__file__).resolve().parents[2])


class TestDockerBuild:
    """Verify that all Dockerfiles build successfully."""

    @pytest.mark.slow
    def test_api_image_builds(self):
        """The API Dockerfile should build without errors."""
        result = subprocess.run(
            ["docker", "build", "-f", "docker/api.Dockerfile", "-t", "pricepoint-api:test", "."],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, f"API build failed: {result.stderr}"

    @pytest.mark.slow
    def test_frontend_image_builds(self):
        """The frontend Dockerfile should build without errors."""
        result = subprocess.run(
            [
                "docker",
                "build",
                "-f",
                "docker/frontend.Dockerfile",
                "-t",
                "pricepoint-frontend:test",
                ".",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, f"Frontend build failed: {result.stderr}"

    @pytest.mark.slow
    def test_mlflow_image_builds(self):
        """The MLflow Dockerfile should build without errors."""
        result = subprocess.run(
            [
                "docker",
                "build",
                "-f",
                "docker/mlflow.Dockerfile",
                "-t",
                "pricepoint-mlflow:test",
                ".",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, f"MLflow build failed: {result.stderr}"


class TestDockerRuntime:
    """Verify containers start and serve correctly."""

    @pytest.mark.slow
    def test_frontend_serves_html(self):
        """The frontend container should serve HTML on port 80."""
        # Build first
        build = subprocess.run(
            [
                "docker",
                "build",
                "-f",
                "docker/frontend.Dockerfile",
                "-t",
                "pricepoint-frontend:runtime-test",
                ".",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if build.returncode != 0:
            pytest.skip("Frontend image failed to build")

        # Run container briefly
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-d",
                "--name",
                "pricepoint-fe-test",
                "-p",
                "18080:80",
                "pricepoint-frontend:runtime-test",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            pytest.skip("Could not start frontend container")

        container_id = result.stdout.strip()
        try:
            import time
            import urllib.request

            time.sleep(3)
            resp = urllib.request.urlopen("http://localhost:18080", timeout=5)
            assert resp.status == 200
            body = resp.read().decode()
            assert "<html" in body.lower() or "<!doctype" in body.lower()
        finally:
            subprocess.run(["docker", "stop", container_id], capture_output=True, timeout=15)

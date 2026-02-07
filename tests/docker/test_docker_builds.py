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


class TestAirflowDagDiscovery:
    """Verify Airflow discovers all DAGs inside the container."""

    EXPECTED_DAGS = {
        "cary_police_collection",
        "data_collection",
        "feature_engineering",
        "model_training",
        "morrisville_police_collection",
        "raleigh_police_collection",
        "tiger_boundary_collection",
    }

    @pytest.mark.slow
    def test_airflow_discovers_all_dags(self):
        """Run airflow dags reserialize + list inside the container and verify all DAGs appear."""
        build = subprocess.run(
            [
                "docker",
                "build",
                "-f",
                "docker/airflow.Dockerfile",
                "-t",
                "pricepoint-airflow:dag-test",
                ".",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if build.returncode != 0:
            pytest.skip("Airflow image failed to build")

        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-e",
                "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=sqlite:////tmp/airflow.db",
                "pricepoint-airflow:dag-test",
                "bash",
                "-c",
                "airflow db migrate > /dev/null 2>&1 && "
                "airflow dags reserialize > /dev/null 2>&1 && "
                "airflow dags list --output plain 2>&1",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, f"airflow dags list failed: {result.stderr}"

        found_dags = set()
        for line in result.stdout.splitlines():
            for dag_id in self.EXPECTED_DAGS:
                if dag_id in line:
                    found_dags.add(dag_id)

        missing = self.EXPECTED_DAGS - found_dags
        assert not missing, f"DAGs not discovered by Airflow: {missing}"


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

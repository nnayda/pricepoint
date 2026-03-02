"""AST-based tests for DAG structure — validates task count, dag_id, sensors."""

import ast
from pathlib import Path


def _parse_dag(dags_dir: Path, filename: str) -> ast.Module:
    """Parse a DAG file and return its AST."""
    return ast.parse((dags_dir / filename).read_text())


def _count_task_decorators(tree: ast.Module) -> int:
    """Count functions decorated with @task()."""
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                # @task or @task()
                if isinstance(decorator, ast.Name) and decorator.id == "task":
                    count += 1
                elif isinstance(decorator, ast.Call):
                    func = decorator.func
                    if isinstance(func, ast.Name) and func.id == "task":
                        count += 1
    return count


def _find_dag_decorator_kwargs(tree: ast.Module) -> dict:
    """Extract keyword arguments from the @dag() decorator."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    func = decorator.func
                    if isinstance(func, ast.Name) and func.id == "dag":
                        kwargs = {}
                        for kw in decorator.keywords:
                            if isinstance(kw.value, ast.Constant):
                                kwargs[kw.arg] = kw.value.value
                        return kwargs
    return {}


def _has_external_task_sensor(tree: ast.Module) -> bool:
    """Check if the DAG contains an ExternalTaskSensor instantiation."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "ExternalTaskSensor":
                return True
    return False


def _get_sensor_external_dag_id(tree: ast.Module) -> str | None:
    """Extract the external_dag_id from an ExternalTaskSensor call."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "ExternalTaskSensor":
                for kw in node.keywords:
                    if kw.arg == "external_dag_id" and isinstance(kw.value, ast.Constant):
                        return kw.value.value
    return None


class TestFeatureEngineeringDag:
    """Validate the feature_engineering DAG structure."""

    def test_dag_id(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_feature_engineering.py")
        kwargs = _find_dag_decorator_kwargs(tree)
        assert kwargs["dag_id"] == "feature_engineering"

    def test_task_count(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_feature_engineering.py")
        assert _count_task_decorators(tree) == 4

    def test_no_sensor(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_feature_engineering.py")
        assert not _has_external_task_sensor(tree)


class TestModelTrainingDag:
    """Validate the model_training DAG structure."""

    def test_dag_id(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_model_training.py")
        kwargs = _find_dag_decorator_kwargs(tree)
        assert kwargs["dag_id"] == "model_training"

    def test_task_count(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_model_training.py")
        assert _count_task_decorators(tree) == 4

    def test_uses_dataset_schedule_not_sensor(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_model_training.py")
        assert not _has_external_task_sensor(tree)


class TestCaryPoliceCollectionDag:
    """Validate the cary_police_collection DAG structure."""

    def test_dag_id(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_cary_police_collection.py")
        kwargs = _find_dag_decorator_kwargs(tree)
        assert kwargs["dag_id"] == "cary_police_collection"

    def test_schedule(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_cary_police_collection.py")
        kwargs = _find_dag_decorator_kwargs(tree)
        assert kwargs["schedule"] == "@weekly"

    def test_task_count(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_cary_police_collection.py")
        assert _count_task_decorators(tree) == 2

    def test_no_sensor(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_cary_police_collection.py")
        assert not _has_external_task_sensor(tree)


class TestRaleighPoliceCollectionDag:
    """Validate the raleigh_police_collection DAG structure."""

    def test_dag_id(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_raleigh_police_collection.py")
        kwargs = _find_dag_decorator_kwargs(tree)
        assert kwargs["dag_id"] == "raleigh_police_collection"

    def test_schedule(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_raleigh_police_collection.py")
        kwargs = _find_dag_decorator_kwargs(tree)
        assert kwargs["schedule"] == "@daily"

    def test_task_count(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_raleigh_police_collection.py")
        assert _count_task_decorators(tree) == 2

    def test_no_sensor(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_raleigh_police_collection.py")
        assert not _has_external_task_sensor(tree)


class TestMorrisvillePoliceCollectionDag:
    """Validate the morrisville_police_collection DAG structure."""

    def test_dag_id(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_morrisville_police_collection.py")
        kwargs = _find_dag_decorator_kwargs(tree)
        assert kwargs["dag_id"] == "morrisville_police_collection"

    def test_schedule(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_morrisville_police_collection.py")
        kwargs = _find_dag_decorator_kwargs(tree)
        assert kwargs["schedule"] == "@weekly"

    def test_task_count(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_morrisville_police_collection.py")
        assert _count_task_decorators(tree) == 2

    def test_no_sensor(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_morrisville_police_collection.py")
        assert not _has_external_task_sensor(tree)


class TestTigerBoundaryCollectionDag:
    """Validate the tiger_boundary_collection DAG structure."""

    def test_dag_id(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_tiger_boundary_collection.py")
        kwargs = _find_dag_decorator_kwargs(tree)
        assert kwargs["dag_id"] == "tiger_boundary_collection"

    def test_schedule_is_none(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_tiger_boundary_collection.py")
        kwargs = _find_dag_decorator_kwargs(tree)
        assert kwargs.get("schedule") is None

    def test_task_count(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_tiger_boundary_collection.py")
        assert _count_task_decorators(tree) == 7

    def test_no_sensor(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_tiger_boundary_collection.py")
        assert not _has_external_task_sensor(tree)


class TestWakeCountyPropertyCollectionDag:
    """Validate the wake_county_property_collection DAG structure."""

    def test_dag_id(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_wake_county_property_collection.py")
        kwargs = _find_dag_decorator_kwargs(tree)
        assert kwargs["dag_id"] == "wake_county_property_collection"

    def test_schedule(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_wake_county_property_collection.py")
        kwargs = _find_dag_decorator_kwargs(tree)
        assert kwargs["schedule"] == "0 0 */14 * *"  # Biweekly

    def test_task_count(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_wake_county_property_collection.py")
        assert _count_task_decorators(tree) == 2

    def test_no_sensor(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_wake_county_property_collection.py")
        assert not _has_external_task_sensor(tree)


class TestRedfinListingTransformDag:
    """Validate the redfin_listing_transform DAG structure."""

    def test_dag_id(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_redfin_transform.py")
        kwargs = _find_dag_decorator_kwargs(tree)
        assert kwargs["dag_id"] == "redfin_listing_transform"

    def test_task_count(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_redfin_transform.py")
        assert _count_task_decorators(tree) == 2

    def test_no_sensor(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_redfin_transform.py")
        assert not _has_external_task_sensor(tree)


class TestRiskBoundaryBuildDag:
    """Validate the risk_boundary_build DAG structure."""

    def test_dag_id(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_risk_boundary_build.py")
        kwargs = _find_dag_decorator_kwargs(tree)
        assert kwargs["dag_id"] == "risk_boundary_build"

    def test_task_count(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_risk_boundary_build.py")
        assert _count_task_decorators(tree) == 2

    def test_no_sensor(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_risk_boundary_build.py")
        assert not _has_external_task_sensor(tree)


class TestWakeSubdivisionCollectionDag:
    """Validate the wake_subdivision_collection DAG structure."""

    def test_dag_id(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_wake_subdivision_collection.py")
        kwargs = _find_dag_decorator_kwargs(tree)
        assert kwargs["dag_id"] == "wake_subdivision_collection"

    def test_schedule_is_none(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_wake_subdivision_collection.py")
        kwargs = _find_dag_decorator_kwargs(tree)
        assert kwargs.get("schedule") is None

    def test_task_count(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_wake_subdivision_collection.py")
        assert _count_task_decorators(tree) == 2

    def test_no_sensor(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_wake_subdivision_collection.py")
        assert not _has_external_task_sensor(tree)


class TestSubdivisionCollectionDag:
    """Validate the subdivision_collection DAG structure."""

    def test_dag_id(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_subdivision_collection.py")
        kwargs = _find_dag_decorator_kwargs(tree)
        assert kwargs["dag_id"] == "subdivision_collection"

    def test_schedule_is_none(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_subdivision_collection.py")
        kwargs = _find_dag_decorator_kwargs(tree)
        assert kwargs.get("schedule") is None

    def test_task_count(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_subdivision_collection.py")
        assert _count_task_decorators(tree) == 2

    def test_no_sensor(self, dags_dir):
        tree = _parse_dag(dags_dir, "dag_subdivision_collection.py")
        assert not _has_external_task_sensor(tree)

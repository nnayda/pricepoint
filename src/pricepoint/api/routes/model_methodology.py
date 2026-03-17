"""Model methodology endpoints — proxy MLflow data to the frontend."""

from __future__ import annotations

import logging
import re
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from pricepoint.api.schemas.model_methodology import (
    FeatureCatalogEntry,
    FeatureCatalogResponse,
    FeatureImportanceItem,
    ModelMetadata,
    ModelMethodologyResponse,
    ModelMetrics,
)
from pricepoint.models.registry import MODEL_NAME

logger = logging.getLogger(__name__)

router = APIRouter(tags=["model"])

# Module-level cache for feature catalog (static file, never changes at runtime)
_feature_catalog_cache: FeatureCatalogResponse | None = None

# In-memory methodology cache (keyed by model version)
_methodology_cache: dict[str, tuple[float, ModelMethodologyResponse]] = {}
_METHODOLOGY_TTL = 3600  # 1 hour


def _get_mlflow_client() -> Any:
    """Lazy-import and return an MlflowClient."""
    import mlflow

    return mlflow.tracking.MlflowClient()


def _get_champion_info(client: Any) -> tuple[str, str]:
    """Return (run_id, version) for the champion model.

    Raises HTTPException(404) when no champion exists.
    """
    import mlflow.exceptions

    try:
        mv = client.get_model_version_by_alias(MODEL_NAME, "champion")
    except mlflow.exceptions.MlflowException:
        raise HTTPException(status_code=404, detail="No champion model registered") from None
    return mv.run_id, mv.version


@router.get("/model/methodology", response_model=ModelMethodologyResponse)
async def get_methodology(request: Request) -> ModelMethodologyResponse:
    """Return model metadata, metrics, feature importance, and available plots."""
    import time

    try:
        client = _get_mlflow_client()
    except Exception:
        logger.exception("MLflow unreachable")
        raise HTTPException(status_code=503, detail="MLflow service unavailable") from None

    run_id, version = _get_champion_info(client)

    # Check in-memory cache
    now = time.monotonic()
    if version in _methodology_cache:
        cached_ts, cached_resp = _methodology_cache[version]
        if now - cached_ts < _METHODOLOGY_TTL:
            return cached_resp

    # Also check Valkey if available
    valkey_pool = getattr(request.app.state, "valkey_pool", None)
    cache_key = f"model:methodology:{version}"
    if valkey_pool is not None:
        try:
            cached_json = await valkey_pool.get(cache_key)
            if cached_json is not None:
                resp = ModelMethodologyResponse.model_validate_json(cached_json)
                _methodology_cache[version] = (now, resp)
                return resp
        except Exception:
            logger.debug("Valkey cache miss/error for %s", cache_key)

    run = client.get_run(run_id)
    metrics_dict = run.data.metrics
    params_dict = run.data.params

    # Available plots
    available_plots: list[str] = []
    try:
        for artifact in client.list_artifacts(run_id, "plots"):
            if artifact.path.endswith(".png"):
                available_plots.append(artifact.path)
    except Exception:
        logger.debug("No plots directory for run %s", run_id)

    available_eda_plots: list[str] = []
    try:
        for artifact in client.list_artifacts(run_id, "eda"):
            if artifact.path.endswith(".png"):
                available_eda_plots.append(artifact.path)
    except Exception:
        logger.debug("No eda directory for run %s", run_id)

    # Feature importance from metrics (logged as feature_importance_top20_<name>)
    fi_prefix = "feature_importance_top20_"
    feature_importance = [
        FeatureImportanceItem(feature=k[len(fi_prefix) :], gain=float(v))
        for k, v in metrics_dict.items()
        if k.startswith(fi_prefix)
    ]
    feature_importance.sort(key=lambda x: x.gain, reverse=True)

    # Training date from run start time
    start_time = run.info.start_time
    training_date = ""
    if start_time:
        from datetime import UTC, datetime

        training_date = datetime.fromtimestamp(start_time / 1000, tz=UTC).isoformat()

    metadata = ModelMetadata(
        model_name=MODEL_NAME,
        model_version=version,
        run_id=run_id,
        training_date=training_date,
        n_features=int(metrics_dict.get("n_features", 0)),
        n_training_samples=int(metrics_dict.get("n_training_samples", 0)),
        algorithm=params_dict.get("objective", "reg:squarederror"),
        hyperparameters={k: v for k, v in params_dict.items()},
    )

    model_metrics = ModelMetrics(
        mae=metrics_dict.get("mae"),
        rmse=metrics_dict.get("rmse"),
        mape=metrics_dict.get("mape"),
        r2=metrics_dict.get("r2"),
        median_ae=metrics_dict.get("median_ae"),
        mae_mean=metrics_dict.get("mae_mean"),
        mae_std=metrics_dict.get("mae_std"),
        rmse_mean=metrics_dict.get("rmse_mean"),
        rmse_std=metrics_dict.get("rmse_std"),
        r2_mean=metrics_dict.get("r2_mean"),
        r2_std=metrics_dict.get("r2_std"),
        data_n_rows=_safe_int(metrics_dict.get("data_n_rows")),
        data_n_features=_safe_int(metrics_dict.get("data_n_features")),
        data_target_mean=metrics_dict.get("data_target_mean"),
        data_target_median=metrics_dict.get("data_target_median"),
        data_target_std=metrics_dict.get("data_target_std"),
    )

    resp = ModelMethodologyResponse(
        metadata=metadata,
        metrics=model_metrics,
        feature_importance=feature_importance,
        available_plots=available_plots,
        available_eda_plots=available_eda_plots,
    )

    # Cache in memory
    _methodology_cache[version] = (now, resp)

    # Cache in Valkey
    if valkey_pool is not None:
        try:
            await valkey_pool.set(cache_key, resp.model_dump_json(), ex=_METHODOLOGY_TTL)
        except Exception:
            logger.debug("Failed to cache methodology in Valkey")

    return resp


@router.get("/model/artifact/{artifact_path:path}")
async def get_artifact(artifact_path: str, request: Request) -> StreamingResponse:
    """Stream an MLflow artifact (plot image) to the frontend."""
    # Validate path — only allow plots/ and eda/ directories
    if not artifact_path.startswith(("plots/", "eda/")):
        raise HTTPException(status_code=400, detail="Invalid artifact path")

    # Prevent directory traversal
    if ".." in artifact_path:
        raise HTTPException(status_code=400, detail="Invalid artifact path")

    try:
        client = _get_mlflow_client()
    except Exception:
        raise HTTPException(status_code=503, detail="MLflow service unavailable") from None

    run_id, _ = _get_champion_info(client)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = client.download_artifacts(run_id, artifact_path, dst_path=tmpdir)
            local_file = Path(local_path)
            if not local_file.exists() or not local_file.is_file():
                raise HTTPException(status_code=404, detail="Artifact not found")

            content = local_file.read_bytes()
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to download artifact %s", artifact_path)
        raise HTTPException(status_code=404, detail="Artifact not found") from None

    return StreamingResponse(
        iter([content]),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/model/features", response_model=FeatureCatalogResponse)
async def get_features() -> FeatureCatalogResponse:
    """Parse and return the feature catalog from FEATURE_CATALOG.md."""
    global _feature_catalog_cache  # noqa: PLW0603
    if _feature_catalog_cache is not None:
        return _feature_catalog_cache

    catalog_path = Path(__file__).resolve().parents[4] / "docs" / "FEATURE_CATALOG.md"
    if not catalog_path.exists():
        raise HTTPException(status_code=404, detail="Feature catalog not found")

    text = catalog_path.read_text(encoding="utf-8")
    features, categories = _parse_feature_catalog(text)

    _feature_catalog_cache = FeatureCatalogResponse(
        features=features,
        categories=categories,
    )
    return _feature_catalog_cache


def _safe_int(value: Any) -> int | None:
    """Convert a value to int, returning None on failure."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _parse_feature_catalog(text: str) -> tuple[list[FeatureCatalogEntry], list[str]]:
    """Parse the markdown feature catalog into structured entries."""
    features: list[FeatureCatalogEntry] = []
    categories: list[str] = []

    # Match category headings like "## 1. Location & Address"
    category_pattern = re.compile(r"^## \d+\.\s+(.+)$", re.MULTILINE)

    # Split into sections by category heading
    sections = category_pattern.split(text)
    # sections alternates: [preamble, cat_name_1, cat_body_1, cat_name_2, cat_body_2, ...]
    for i in range(1, len(sections), 2):
        category_name = sections[i].strip()
        if i + 1 >= len(sections):
            break
        body = sections[i + 1]

        categories.append(category_name)

        # Parse pipe-delimited table rows (skip header and separator)
        table_rows = re.findall(r"^\|(.+)\|$", body, re.MULTILINE)
        if len(table_rows) < 2:
            continue

        # Skip header row and separator row
        data_rows = table_rows[2:]  # header, separator, then data
        for row in data_rows:
            cols = [c.strip() for c in row.split("|")]
            if len(cols) < 6:
                continue

            # Columns: name, sql_type, source, derivation, example, default
            name = cols[0].strip("`").strip()
            sql_type = cols[1].strip("`").strip()
            source = cols[2].strip("`").strip()
            derivation = cols[3].strip()
            example = cols[4].strip("`").strip()
            default = cols[5].strip("`").strip()

            if not name or name.startswith("---"):
                continue

            features.append(
                FeatureCatalogEntry(
                    name=name,
                    category=category_name,
                    sql_type=sql_type,
                    source=source,
                    derivation=derivation,
                    example=example,
                    default=default,
                )
            )

    return features, categories

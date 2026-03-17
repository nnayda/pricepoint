"""Pydantic models for the model methodology endpoints."""

from pydantic import BaseModel


class ModelMetadata(BaseModel):
    """Core metadata about the production model."""

    model_name: str
    model_version: str
    run_id: str
    training_date: str
    n_features: int
    n_training_samples: int
    algorithm: str
    hyperparameters: dict[str, str | int | float | None]


class ModelMetrics(BaseModel):
    """Performance metrics from the production model."""

    mae: float | None = None
    rmse: float | None = None
    mape: float | None = None
    r2: float | None = None
    median_ae: float | None = None
    # Cross-validation statistics
    mae_mean: float | None = None
    mae_std: float | None = None
    rmse_mean: float | None = None
    rmse_std: float | None = None
    r2_mean: float | None = None
    r2_std: float | None = None
    # EDA statistics
    data_n_rows: int | None = None
    data_n_features: int | None = None
    data_target_mean: float | None = None
    data_target_median: float | None = None
    data_target_std: float | None = None


class FeatureImportanceItem(BaseModel):
    """A single feature's importance score."""

    feature: str
    gain: float


class ModelMethodologyResponse(BaseModel):
    """Full model methodology response."""

    metadata: ModelMetadata
    metrics: ModelMetrics
    feature_importance: list[FeatureImportanceItem]
    available_plots: list[str]
    available_eda_plots: list[str]


class FeatureCatalogEntry(BaseModel):
    """A single feature from the feature catalog."""

    name: str
    category: str
    sql_type: str
    source: str
    derivation: str
    example: str
    default: str


class FeatureCatalogResponse(BaseModel):
    """Parsed feature catalog response."""

    features: list[FeatureCatalogEntry]
    categories: list[str]

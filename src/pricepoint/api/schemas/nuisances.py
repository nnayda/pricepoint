"""Pydantic models for the nuisances endpoint."""

from pydantic import BaseModel


class NoiseProperties(BaseModel):
    """Properties for a single noise polygon feature."""

    noise_band: str
    noise_min_db: int
    noise_max_db: int | None = None
    source_layer: str
    area_sq_m: float | None = None


class NoiseFeature(BaseModel):
    """A single GeoJSON Feature representing a noise polygon."""

    type: str = "Feature"
    geometry: dict
    properties: NoiseProperties


class NoiseResponse(BaseModel):
    """GeoJSON FeatureCollection of noise polygons."""

    type: str = "FeatureCollection"
    features: list[NoiseFeature]

"""Pydantic models for the nuisances endpoint."""

from pydantic import BaseModel


class NuisanceSource(BaseModel):
    """A single nuisance source near the property."""

    id: str
    name: str
    source_type: str  # "aviation" | "road" | "rail"
    severity: str  # "Caution" | "Concern"
    distance_miles: float
    lat: float | None = None
    lon: float | None = None
    detail: str
    noise_min_db: int | None = None
    noise_band: str | None = None


class NuisanceSourcesResponse(BaseModel):
    """List of nuisance sources near a property."""

    sources: list[NuisanceSource]


class InfrastructureFeature(BaseModel):
    """A GeoJSON Feature representing an infrastructure geometry (road, airport, railroad)."""

    type: str = "Feature"
    geometry: dict
    properties: dict


class InfrastructureGeometriesResponse(BaseModel):
    """GeoJSON FeatureCollection of infrastructure geometries."""

    type: str = "FeatureCollection"
    features: list[InfrastructureFeature]


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

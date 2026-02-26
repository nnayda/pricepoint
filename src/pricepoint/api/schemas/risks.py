"""Pydantic models for the risks endpoint."""

from typing import Any

from pydantic import BaseModel


class RiskFeature(BaseModel):
    """A single infrastructure risk feature with severity assessment."""

    id: str
    name: str
    infrastructure_type: str
    severity: str
    distance_miles: float
    lat: float
    lon: float
    detail: str


class RisksResponse(BaseModel):
    """Response body for infrastructure risks lookup."""

    features: list[RiskFeature]
    boundary_geojson: dict[str, Any]

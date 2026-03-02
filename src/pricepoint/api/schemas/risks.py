"""Pydantic models for the risks endpoint.

Boundary polygon geometry and infrastructure line geometry are now served
via Martin vector tiles.  This schema only contains risk assessment data
for the sidebar card list.
"""

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
    metadata: dict[str, str | float | None] = {}


class RisksResponse(BaseModel):
    """Response body for infrastructure risks lookup."""

    features: list[RiskFeature]

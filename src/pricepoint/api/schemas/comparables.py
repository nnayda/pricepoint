"""Pydantic models for the comparables endpoint."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ComparablesQuery(BaseModel):
    """Query parameters for the comparables search."""

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    address: str = Field(min_length=1)
    time_period_months: Literal[3, 6, 9, 12] = 3
    distance_miles: float = Field(default=1.0, ge=0.5, le=5.0)
    same_schools: bool = True
    sqft_pct: int = Field(default=10, ge=0, le=40)
    lot_pct: int = Field(default=10, ge=0, le=40)
    same_beds: bool = True
    same_baths: bool = True
    year_built_diff: int = Field(default=10, ge=0, le=20)


class FeatureGroup(BaseModel):
    """A group of ML features under one category."""

    category: str
    features: dict[str, float | str | bool | None]


class CompNuisance(BaseModel):
    """Nuisance source for a comparable property."""

    name: str
    source_type: str
    severity: str
    distance_miles: float
    detail: str


class CompRisk(BaseModel):
    """Infrastructure risk for a comparable property."""

    name: str
    infrastructure_type: str
    severity: str
    distance_miles: float
    detail: str


class CompProperty(BaseModel):
    """A single comparable (or subject) property with full details."""

    listing_id: int
    address: str
    city: str
    state: str
    zip_code: str
    lat: float
    lon: float
    sold_price: float | None = None
    sold_date: str | None = None
    listing_price: float | None = None
    beds: int
    baths: float
    sqft: int | None = None
    lot_size: float | None = None
    year_built: int | None = None
    garage_spaces: int = 0
    price_per_sqft: float | None = None
    photos: list[str] = []
    description_score: int | None = None
    photo_score: int | None = None
    feature_groups: list[FeatureGroup] = []
    nuisances: list[CompNuisance] = []
    risks: list[CompRisk] = []
    similarity_distance: float | None = None


class ComparablesResponse(BaseModel):
    """Response body for the comparables endpoint."""

    subject: CompProperty
    comparables: list[CompProperty]
    total_candidates: int

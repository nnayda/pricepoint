"""Pydantic response models for the neighborhood valuation endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class NeighborhoodValuationResponse(BaseModel):
    tract_geoid: str
    median_value: float | None
    max_value: float | None
    sample_size: int


class NeighborhoodMedianPoint(BaseModel):
    date: str
    median_value: float


class NeighborhoodValuationHistoryResponse(BaseModel):
    tract_geoid: str
    sample_size: int
    monthly_medians: list[NeighborhoodMedianPoint]

"""Pydantic response models for the demographics endpoint."""

from __future__ import annotations

from pydantic import BaseModel


class LabelValue(BaseModel):
    label: str
    value: float


class PopulationTrendPoint(BaseModel):
    year: int
    population: int


class RaceEthnicityTrendPoint(BaseModel):
    year: int
    white: float
    black: float
    hispanic: float
    asian: float
    other: float


class AgeDistributionTrendPoint(BaseModel):
    year: int
    under18: float
    age18_22: float
    age23_29: float
    age30_39: float
    age40_49: float
    age50_64: float
    age65plus: float


class IncomeTrendPoint(BaseModel):
    year: int
    median_income: int


class HomeOwnershipTrendPoint(BaseModel):
    year: int
    ownership_rate: float


class MedianAgeTrendPoint(BaseModel):
    year: int
    median_age: float


class AgeBucket(BaseModel):
    range: str
    male: float
    female: float


class RaceSubgroup(BaseModel):
    label: str
    value: int  # population count
    percentage: float  # % within parent race


class RaceDetailedBreakdown(BaseModel):
    race_category: str
    total: int
    subgroups: list[RaceSubgroup]


class DemographicContextData(BaseModel):
    """Snapshot + trend data for a single geographic context."""

    race_ethnicity: list[LabelValue]
    age_distribution: list[AgeBucket]
    median_income: int
    income_brackets: list[LabelValue]
    home_ownership_rate: float
    median_home_value: int
    population: int
    population_trend: list[PopulationTrendPoint]
    race_ethnicity_trend: list[RaceEthnicityTrendPoint]
    age_distribution_trend: list[AgeDistributionTrendPoint]
    income_trend: list[IncomeTrendPoint]
    home_ownership_trend: list[HomeOwnershipTrendPoint]
    median_age_trend: list[MedianAgeTrendPoint]
    race_detailed: dict[str, RaceDetailedBreakdown] | None = None


class DemographicsResponse(BaseModel):
    """Full demographics response with multiple geographic contexts.

    Boundary geometry and choropleth map data are now served via Martin
    vector tiles and are no longer included in this response.
    """

    contexts: dict[str, DemographicContextData]
    benchmarks: dict[str, DemographicContextData]

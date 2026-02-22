"""Pydantic models for the property endpoint."""

from pydantic import BaseModel


class PropertyImage(BaseModel):
    """A single property image."""

    url: str
    alt: str
    is_primary: bool = False


class PropertyDetails(BaseModel):
    """Core property details."""

    address: str
    city: str
    state: str
    zip_code: str
    lat: float
    lon: float
    bedrooms: int
    bathrooms: float
    sqft: int
    lot_size_sqft: int
    year_built: int
    property_type: str
    stories: int
    garage_spaces: int
    description: str
    highlights: list[str]
    images: list[PropertyImage]
    listing_status: str | None = None
    price_per_sqft: float | None = None
    days_on_market: int | None = None
    listed_date: str | None = None
    hoa_monthly: float | None = None


class ValuationData(BaseModel):
    """Property valuation and prediction data."""

    listed_price: float | None = None
    last_sold_price: float | None = None
    last_sold_date: str | None = None
    redfin_estimate: float | None = None
    predicted_value: float | None = None
    confidence_interval_low: float | None = None
    confidence_interval_high: float | None = None
    model_version: str | None = None
    prediction_date: str | None = None


class InteriorFeatures(BaseModel):
    """Interior feature details."""

    flooring: list[str]
    appliances: list[str]
    heating: str
    cooling: str
    fireplace: bool
    basement: str | None = None


class ExteriorFeatures(BaseModel):
    """Exterior feature details."""

    roof: str
    siding: str
    foundation: str
    parking: str
    pool: bool
    fence: str


class FinancialDetails(BaseModel):
    """Financial information about the property."""

    hoa_monthly: float | None = None
    tax_annual: float
    tax_year: int
    assessed_value: float


class SchoolNearby(BaseModel):
    """A nearby school."""

    name: str
    address: str | None = None
    school_type: str
    school_level: str | None = None
    rating: int
    grades: str | None = None
    distance_miles: float
    drive_minutes: int
    walk_minutes: int | None = None
    student_teacher_ratio: float | None = None
    enrollment: int | None = None
    assigned: bool = False
    lat: float | None = None
    lon: float | None = None


class SaleHistoryEntry(BaseModel):
    """A single sale history event."""

    date: str
    price: float
    event_type: str


class TaxHistoryEntry(BaseModel):
    """A single tax history record."""

    year: int
    assessed_value: float
    tax_amount: float


class ClimateRisk(BaseModel):
    """Climate risk assessment."""

    flood_risk: str
    flood_score: int
    fire_risk: str
    fire_score: int


class ComparableProperty(BaseModel):
    """A comparable property for comparison."""

    id: int
    address: str
    sale_price: float
    sold_date: str
    beds: int
    baths: float
    sqft: int
    price_per_sqft: float
    lat: float
    lon: float


class ListingQuality(BaseModel):
    """LLM-generated listing quality scores."""

    description_score: int | None = None
    quality_reasoning: str | None = None


class PropertyResponse(BaseModel):
    """Response body for property lookup."""

    property: PropertyDetails
    valuation: ValuationData
    interior: InteriorFeatures
    exterior: ExteriorFeatures
    financial: FinancialDetails
    schools: list[SchoolNearby]
    sale_history: list[SaleHistoryEntry]
    tax_history: list[TaxHistoryEntry]
    climate_risk: ClimateRisk
    listing_quality: ListingQuality | None = None

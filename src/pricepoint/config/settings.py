"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for the Home Value Forecast application.

    All values are read from environment variables (or a .env file).
    """

    # Database
    database_url: str = "postgresql://pricepoint:pricepoint@localhost:5432/pricepoint"

    # S3-compatible object storage
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "pricepoint-data"

    # MLflow
    mlflow_tracking_uri: str = "http://localhost:5000"

    # Town of Cary Open Data
    cary_opendata_platform_id: str = "data.townofcary.org"

    # City of Raleigh ArcGIS
    raleigh_arcgis_base_url: str = (
        "https://services.arcgis.com/v400IkDOw1ad7Yad/arcgis/rest/services"
    )

    # Town of Morrisville Open Data
    morrisville_opendata_platform_id: str = "opendata.townofmorrisville.org"

    # US Census TIGER/Line Shapefiles
    tiger_base_url: str = "https://www2.census.gov/geo/tiger"
    tiger_year: int = 2025
    tiger_state_fips: str = "37"  # North Carolina
    tiger_county_fips: str = "183"  # Wake County

    # Wake County Property Data
    wake_county_data_url: str = (
        "https://services.wake.gov/realdata_extracts/RealEstData02082026.zip"
    )

    # NCES School Data (EDGE ArcGIS REST API)
    nces_edge_base_url: str = (
        "https://nces.ed.gov/opengis/rest/services/K12_School_Locations"
        "/EDGE_ADMINDATA_PUBLICSCH_2223/MapServer/0"
    )

    # OSRM routing
    osrm_base_url: str = "https://router.project-osrm.org"
    osrm_rate_limit_seconds: float = 1.0

    # Redfin listing HTML collector
    redfin_html_dir: str = "/data/raw/redfin"
    redfin_s3_archive_prefix: str = "redfin/archive"
    redfin_s3_photos_prefix: str = "redfin/photos"

    # Valkey (Redis-compatible cache)
    valkey_url: str | None = None

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_cors_origins: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()

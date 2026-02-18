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
    wake_county_extracts_url: str = "https://services.wake.gov/realdata_extracts/"

    # NCES School Data (EDGE ArcGIS REST API)
    nces_edge_base_url: str = (
        "https://nces.ed.gov/opengis/rest/services/K12_School_Locations"
        "/EDGE_ADMINDATA_PUBLICSCH_2223/MapServer/0"
    )

    # OSRM routing
    osrm_base_url: str = "https://router.project-osrm.org"
    osrm_rate_limit_seconds: float = 1.0

    # Wake County Subdivisions (ArcGIS MapServer)
    wake_subdivisions_base_url: str = (
        "https://maps.wake.gov/arcgis/rest/services/Planning/Subdivisions/MapServer/0"
    )

    # Wake County Geospatial Collectors (ArcGIS)
    wake_farmers_markets_base_url: str = (
        "https://services.arcgis.com/ZOyb2t4B0UYuYNYH/arcgis/rest/services"
        "/Farmers_Market/FeatureServer/0"
    )
    wake_libraries_base_url: str = (
        "https://services1.arcgis.com/a7CWfuGP5ZnLYE7I/arcgis/rest/services"
        "/Libraries/FeatureServer/0"
    )
    wake_hospitals_base_url: str = (
        "https://services.arcgis.com/ZOyb2t4B0UYuYNYH/arcgis/rest/services/Hospital/FeatureServer/0"
    )
    wake_parks_base_url: str = (
        "https://maps.wakegov.com/arcgis/rest/services/OpenSpace/OpenSpace/MapServer/0"
    )
    raleigh_parks_base_url: str = (
        "https://services.arcgis.com/v400IkDOw1ad7Yad/arcgis/rest/services/Parks/FeatureServer/0"
    )
    cary_parks_base_url: str = (
        "https://maps-apis.carync.gov/arcgis/rest/services/ParksRecreation/Parks/FeatureServer/0"
    )
    wake_greenways_base_url: str = (
        "https://maps.wakegov.com/arcgis/rest/services/OpenSpace/Greenways/MapServer/0"
    )
    raleigh_greenways_base_url: str = (
        "https://services.arcgis.com/v400IkDOw1ad7Yad/arcgis/rest/services"
        "/Greenway_Trails_All/FeatureServer/0"
    )
    cary_greenways_base_url: str = (
        "https://maps-apis.carync.gov/arcgis/rest/services/ParksRecreation/Parks/FeatureServer/2"
    )
    wake_railroads_base_url: str = (
        "https://maps.wakegov.com/arcgis/rest/services"
        "/Transportation/Transportation/FeatureServer/2"
    )
    wake_major_roads_base_url: str = (
        "https://maps.wakegov.com/arcgis/rest/services"
        "/Transportation/Transportation/FeatureServer/3"
    )
    wake_highways_base_url: str = (
        "https://maps.wakegov.com/arcgis/rest/services"
        "/Transportation/Transportation/FeatureServer/4"
    )
    wake_utility_easements_base_url: str = (
        "https://maps.wakegov.com/arcgis/rest/services/Property/Easements/MapServer/1"
    )

    # Ollama LLM (description quality scoring)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:32b"
    ollama_vision_model: str = "qwen3-vl:32b"
    ollama_max_concurrent: int = 4
    ollama_timeout_seconds: int = 120

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

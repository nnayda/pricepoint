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

    # Geocoding
    geocode_provider: str = "nominatim"  # "nominatim" or "photon"
    geocode_url: str = "https://nominatim.openstreetmap.org/search"
    geocode_timeout: float = 5.0
    geocode_rate_limit_seconds: float = 1.0  # 0 = no limit (self-hosted)

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
    wake_open_space_base_url: str = (
        "https://maps.wakegov.com/arcgis/rest/services/OpenSpace/OpenSpace/MapServer/0"
    )
    wake_greenways_base_url: str = (
        "https://maps.wakegov.com/arcgis/rest/services/OpenSpace/Greenways/MapServer/0"
    )
    raleigh_greenways_base_url: str = (
        "https://services.arcgis.com/v400IkDOw1ad7Yad/arcgis/rest/services"
        "/Greenway_Trails_All/FeatureServer/0"
    )
    cary_greenways_base_url: str = (
        "https://maps-apis.carync.gov/server/rest/services/ParksRecreation/Parks/FeatureServer/2"
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

    # HIFLD Infrastructure (ArcGIS FeatureServer)
    hifld_cell_towers_base_url: str = (
        "https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services"
        "/Cellular_Towers_in_the_United_States/FeatureServer/0"
    )
    hifld_transmission_lines_base_url: str = (
        "https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services"
        "/US_Electric_Power_Transmission_Lines/FeatureServer/0"
    )
    hifld_power_plants_base_url: str = (
        "https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services"
        "/Power_Plants_in_the_US/FeatureServer/0"
    )
    hifld_nat_gas_pipelines_base_url: str = (
        "https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services"
        "/Natural_Gas_Interstate_and_Intrastate_Pipelines_1/FeatureServer/0"
    )
    hifld_petroleum_pipelines_base_url: str = (
        "https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services"
        "/Petroleum_Products_Pipelines_1/FeatureServer/0"
    )

    # Overture Maps Places
    overture_places_s3_path: str = (
        "s3://overturemaps-us-west-2/release/2026-02-18.0/theme=places/type=place/*"
    )
    overture_places_min_confidence: float = 0.5
    overture_places_country: str = "US"

    # Ollama LLM (description quality scoring)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:32b"
    ollama_vision_model: str = "qwen3-vl:32b"
    ollama_max_concurrent: int = 4
    ollama_timeout_seconds: int = 120

    # Census ACS Demographics
    census_api_key: str = ""
    census_acs_base_url: str = "https://api.census.gov/data"
    census_acs_vintages: list[int] = [2009, 2014, 2019, 2024]
    census_acs_block_group_min_year: int = 2014

    # FRED API (economic indicators)
    fred_api_key: str = ""
    fred_series_ids: list[str] = [
        "MORTGAGE30US",
        "MORTGAGE15US",
        "CPIAUCSL",
        "UNRATE",
        "NCUR",
        "HOUST",
        "PERMIT",
        "CSUSHPISA",
        "UMCSENT",
    ]
    fred_lookback_years: int = 10

    # Redfin listing HTML collector
    redfin_html_dir: str = "/data/raw/redfin"
    redfin_s3_archive_prefix: str = "redfin/archive"
    redfin_s3_photos_prefix: str = "redfin/photos"

    # Valkey (Redis-compatible cache)
    valkey_url: str | None = None

    # Cache TTLs (seconds)
    cache_ttl_crime: int = 21600  # 6 hours
    cache_ttl_property: int = 86400  # 24 hours
    cache_ttl_pois: int = 604800  # 7 days
    cache_ttl_geocode: int = 2592000  # 30 days

    # JWT Authentication
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # OAuth (Google)
    oauth_google_client_id: str = ""
    oauth_google_client_secret: str = ""
    oauth_redirect_uri: str = "http://localhost:5173/auth/google/callback"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_cors_origins: list[str] = ["http://localhost:3000"]

    # Rate limiting
    rate_limit_default: str = "100/minute"
    rate_limit_forecast: str = "10/minute"
    rate_limit_auth: str = "5/minute"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()

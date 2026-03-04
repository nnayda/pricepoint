"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for the Home Value Forecast application.

    All values are read from environment variables (or a .env file).
    """

    # Dev mode — disables Valkey caching so data changes are reflected immediately
    dev_mode: bool = False

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

    hifld_hospitals_base_url: str = (
        "https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services"
        "/Hospitals/FeatureServer/0"
    )
    # PAD-US (Protected Areas Database of the United States)
    pad_us_download_url: str = (
        "https://www.sciencebase.gov/catalog/file/get/"
        "652d4fc5d34e44db0e2ee45e?name=PADUS4_1Geodatabase.zip"
    )
    pad_us_layer_name: str = "PADUS4_1Fee"
    trails_base_url: str = (
        "https://carto.nationalmap.gov/arcgis/rest/services/transportation/MapServer/37"
    )
    # Infrastructure (ArcGIS FeatureServer)
    cell_towers_base_url: str = (
        "https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services"
        "/Cellular_Towers_in_the_United_States/FeatureServer/0"
    )
    transmission_lines_base_url: str = (
        "https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services"
        "/US_Electric_Power_Transmission_Lines/FeatureServer/0"
    )
    power_plants_base_url: str = (
        "https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services"
        "/Power_Plants_in_the_US/FeatureServer/0"
    )
    nat_gas_pipelines_base_url: str = (
        "https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services"
        "/Natural_Gas_Interstate_and_Intrastate_Pipelines_1/FeatureServer/0"
    )
    petroleum_pipelines_base_url: str = (
        "https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services"
        "/Petroleum_Products_Pipelines_1/FeatureServer/0"
    )

    # Risk boundary distances (feet) — converted to meters at runtime
    risk_boundary_distances_ft: dict = {
        "cell_towers": {"critical": 1300, "caution": 3000},
        "transmission_lines": {"critical": 50, "caution": 300},
        "petroleum_pipelines": {"critical": 300, "caution": 1000},
        "nat_gas_pipelines": {"critical": 300, "caution": 1000},
        "power_plants": {
            "wind": {"critical": 2500, "caution": 7920},
            "solar": {"critical": 300, "caution": 1000},
            "geothermal": {"critical": 5280, "caution": 15840},
            "pumped storage": {"critical": 100, "caution": 2640},
            "petroleum": {"critical": 15840, "caution": 52800},
            "natural gas": {"critical": 10560, "caution": 26400},
            "biomass": {"critical": 10560, "caution": 26400},
            "batteries": {"critical": 500, "caution": 5280},
            "nuclear": {"critical": 52800, "caution": 264000},
            "coal": {"critical": 26400, "caution": 158400},
            "_default": {"critical": 2640, "caution": 10560},
        },
    }

    # HIFLD Railroads (ArcGIS FeatureServer)
    hifld_railroads_base_url: str = (
        "https://services.arcgis.com/xOi1kZaI0eWDREZv/arcgis/rest/services"
        "/NTAD_North_American_Rail_Network_Lines/FeatureServer/0"
    )

    # OurAirports
    ourairports_csv_url: str = "https://davidmegginson.github.io/ourairports-data/airports.csv"

    # BTS National Transportation Noise Map
    bts_noise_base_url: str = "https://geo.dot.gov/server/rest/services/Hosted"
    bts_noise_modes: list[str] = ["aviation", "road", "rail", "aviation_road_rail"]
    bts_noise_zoom: int = 12
    bts_noise_bbox_south: float = 35.5
    bts_noise_bbox_north: float = 36.1
    bts_noise_bbox_west: float = -79.1
    bts_noise_bbox_east: float = -78.4
    bts_noise_tile_rate_limit: float = 0.05
    bts_noise_simplify_tolerance: float = 0.001
    bts_noise_batch_size: int = 10
    bts_noise_min_polygon_area_sq_m: float = 500.0
    bts_noise_morphological_closing: bool = True
    bts_noise_chaikin_iterations: int = 3
    bts_noise_cluster_eps: float = 0.001  # DBSCAN eps in degrees (~100m)
    bts_noise_buffer_distance: float = 0.0005  # buffer/unbuffer gap-fill in degrees (~50m)
    bts_noise_max_hole_area_sq_m: float = 50000.0  # Fill interior holes < 50,000 m² (~5 hectares)

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

    # Airflow API
    airflow_base_url: str = "http://airflow-api-server:8080"
    airflow_username: str = "admin"
    airflow_password: str = "admin"

    # Redfin listing HTML collector
    redfin_html_dir: str = "/data/raw/redfin"
    redfin_s3_archive_prefix: str = "redfin/archive"
    redfin_s3_photos_prefix: str = "redfin/photos"

    # Hyperparameter tuning
    tuning_enabled: bool = True
    tuning_n_trials: int = 50
    tuning_cv_folds: int = 5
    tuning_timeout_seconds: int = 3600
    tuning_early_stopping_rounds: int = 50

    # Model promotion
    model_auto_promote: bool = True
    model_primary_metric: str = "mae"  # "mae", "rmse", "mape", "r2"

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

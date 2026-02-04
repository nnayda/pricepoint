# src/pricepoint/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # These are defaults. They can be overridden by env vars like APP_TABLE_NAME
    TABLE_NAME: str = "staging_police_incidents_cary"
    ODS_BASE_URL: str = "https://data.townofcary.org/"
    
    # You can group specific dataset IDs here or keep them in the collector
    # depending on if they are shared.
    
    class Config:
        # Pydantic will look for env vars starting with this prefix
        env_prefix = "PRICEPOINT_" 

settings = Settings()
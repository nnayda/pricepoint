import sys
from pricepoint.utils.logger import setup_logger
import os
import pandas as pd
from sqlalchemy import create_engine, text
from odsclient import ODSClient
"""
test:
# src/pricepoint/collectors/police_incidents/police_incidents_cary.py
from pricepoint.config import settings

def collect_cary_data():
    print(f"Fetching from {settings.ODS_BASE_URL}")
    print(f"Writing to {settings.TABLE_NAME}")
"""

logger = setup_logger(__name__)

# Read config from Environment Variables
DB_CONNECTION = os.getenv('DB_CONNECTION')

# Settings
TABLE_NAME = "staging_police_incidents_cary"
ODS_BASE_URL = "https://data.townofcary.org/"
ODS_DATASET_ID = "cpd-incidents"

def download_and_extract_incidents():
    
    # Download the data
    logger.info("Downloading the data...")
    ods_client = ODSClient(base_url=ODS_BASE_URL)
    df = ods_client.get_whole_dataframe(dataset_id=ODS_DATASET_ID)
    logger.info(f"Downloaded {df.shape[0]} records.")

    # Load the data
    logger.info("Connecting to Database...")
    engine = create_engine(DB_CONNECTION)

    logger.info(f"Dropping and recreating table '{TABLE_NAME}'...")
    df.to_sql(
        name=TABLE_NAME,
        con=engine,
        if_exists="replace",
        index=False,
        chunksize=10000
    )

    logger.info("✅ Full reload complete.")

if __name__ == "__main__":
    download_and_extract_incidents()
"""Cary police incident collector."""

import sys
from typing import TYPE_CHECKING

from odsclient import ODSClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from pricepoint.config import settings
from pricepoint.utils.logger import setup_logger

# Use forward references for type checking to avoid runtime import overhead
if TYPE_CHECKING:
    from pandas import DataFrame

logger = setup_logger(__name__)

# Constants
TABLE_NAME = "staging_police_incidents_cary"
ODS_BASE_URL = "https://data.townofcary.org/"
ODS_DATASET_ID = "cpd-incidents"


def extract_incidents(client: ODSClient) -> "DataFrame":
    """
    Download incident data and return as a dataframe.

    Args:
        client: An instance of ODSClient.

    Returns
    -------
        DataFrame: The downloaded data.
    """
    logger.info(f"Downloading data from dataset: {ODS_DATASET_ID}...")
    try:
        # Assuming get_whole_dataframe handles pagination internally
        df = client.get_whole_dataframe(dataset_id=ODS_DATASET_ID)

        if df.empty:
            logger.warning("Downloaded dataset is empty.")
        else:
            logger.info(f"Downloaded {len(df)} records.")

        return df

    except Exception as e:
        logger.error(f"Failed to extract incidents from ODS: {e}")
        raise


def load_incidents(df: "DataFrame", engine: Engine) -> None:
    """
    Load data into the db using a Truncate-Load strategy.

    Args:
        df: The pandas DataFrame to load.
        engine: The SQLAlchemy Engine instance.
    """
    if df.empty:
        logger.info("No data to load. Skipping DB operations.")
        return

    logger.info(f"Loading data into table '{TABLE_NAME}'...")

    # Open a connection to handle transactions manually
    with engine.begin() as connection:
        try:
            # 1. Truncate (Wipe) the staging table first
            connection.execute(text(f"TRUNCATE TABLE {TABLE_NAME}"))
            logger.info(f"Table '{TABLE_NAME}' truncated.")

            # 2. Append new data
            df.to_sql(
                name=TABLE_NAME,
                con=connection,
                if_exists="append",  # Append because we just truncated
                index=False,
                chunksize=10000,  # Keep memory usage low during write
                method="multi",  # Usually faster for multiple inserts
            )
            logger.info("Data insertion complete.")

        except Exception as e:
            logger.error(f"Failed to load data into DB: {e}")
            # The context manager 'engine.begin()' automatically rolls back on error
            raise


def extract_and_load_incidents() -> None:
    """Orchestrate the ETL process."""
    logger.info("Starting ETL of Cary police incidents.")

    try:
        # Initialize resources
        ods_client = ODSClient(base_url=ODS_BASE_URL)
        db_engine = create_engine(settings.database_url)

        # Execute Pipeline
        df = extract_incidents(client=ods_client)
        load_incidents(df=df, engine=db_engine)

        logger.info("✅ Full reload complete.")

    except Exception as e:
        logger.critical(f"ETL Job Failed: {e}")
        # Exit with error code 1 so orchestrators (Airflow/Cron) know it failed
        sys.exit(1)
    finally:
        # Clean up engine if necessary (dispose connection pool)
        if "db_engine" in locals():
            db_engine.dispose()


if __name__ == "__main__":
    extract_and_load_incidents()

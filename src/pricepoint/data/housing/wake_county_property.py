"""Wake County property assessment data collector.

Downloads and parses Wake County's daily property extract (fixed-width format)
into staging_wake_county_property_data table. Truncate-and-reload pattern.
"""

import io
import logging
import re
import zipfile

import httpx
import pandas as pd
from sqlalchemy import delete

from pricepoint.config.settings import get_settings
from pricepoint.db import SessionLocal
from pricepoint.db.models import StagingWakeCountyPropertyData

logger = logging.getLogger(__name__)

_ZIP_LINK_PATTERN = re.compile(r"RealEstData\d{8}\.zip")

# Column specification from read_data_example.py (94 columns, fixed-width format)
COLUMN_MAP = {
    "Owner 1": 35,
    "Owner 2": 35,
    "Address 1": 35,
    "Address 2": 35,
    "Address 3": 35,
    "REID": 7,
    "Card #": 3,
    "# of Cards": 3,
    "Street #": 6,
    "Street Prefix": 2,
    "Street Name": 25,
    "Street Type": 4,
    "Street Suffix": 2,
    "Planning Jurisdiction": 2,
    "Street Misc": 2,
    "Township": 2,
    "Fire District": 2,
    "Land Sale Price": 12,
    "Land Sale Date": 10,
    "Zoning": 5,
    "Deeded Acreage": 8,
    "Total Sale Price": 11,
    "Total Sale Date": 10,
    "Assessed Building Value": 11,
    "Assessed Land Value": 11,
    "Parcel Identification": 19,
    "Special District 1": 3,
    "Special District 2": 3,
    "Special District 3": 3,
    "Billing Class": 1,
    "Property Description": 40,
    "Land Classification": 1,
    "Deed Book": 6,
    "Deed Page": 6,
    "Deed Date": 10,
    "VCS": 7,
    "Property Index": 40,
    "Year Built": 4,
    "# Rooms": 6,
    "Units": 6,
    "Heated Area": 11,
    "Utilities": 3,
    "Street Pavement": 1,
    "Topography": 1,
    "Year of Addition": 4,
    "Effective Year": 4,
    "Remodeled Year": 4,
    "Unused": 2,
    "Special Write In": 8,
    "Story Height": 1,
    "Design Style": 1,
    "Foundation Basement": 1,
    "Foundation Basement %": 2,
    "Exterior Wall": 1,
    "Common Wall": 1,
    "Roof": 1,
    "Roof Floor System": 1,
    "Floor Finish": 1,
    "Interior Finish": 1,
    "Interior Finish 1": 1,
    "Interior Finish 1 %": 2,
    "Interior Finish 2": 1,
    "Interior Finish 2 %": 2,
    "Heat": 1,
    "Heat %": 2,
    "Air": 1,
    "Air %": 2,
    "Bath": 1,
    "Bath Fixtures": 3,
    "Built In 1 Description": 15,
    "Built In 2 Description": 15,
    "Built In 3 Description": 15,
    "Built In 4 Description": 15,
    "Built In 5 Description": 15,
    "City": 3,
    "Grade": 5,
    "Assessed Grade Difference": 3,
    "Accrued Assessed Condition %": 3,
    "Land Deferred Code": 1,
    "Land Deferred Amount": 9,
    "Historic Deferred Code": 1,
    "Historic Deferred Amount": 9,
    "Recycled Units": 6,
    "Disqualifying & Qualifying Flags": 1,
    "Land Disqualify & Qaulify Flag": 1,
    "Type & Use": 3,
    "Physical City": 50,
    "Physical Zip Code": 5,
}

_DOWNLOAD_TIMEOUT = 300  # 5 minutes for large 318MB file


def _discover_zip_url(extracts_url: str) -> str:
    """Discover the current RealEstData ZIP URL from the extracts page.

    Fetches the directory listing and finds the RealEstDataMMDDYYYY.zip link.

    Args:
        extracts_url: URL of the Wake County real data extracts page

    Returns:
        Full URL to the RealEstData ZIP file

    Raises:
        ValueError: If no matching ZIP link found on the page
        httpx.HTTPError: If page fetch fails
    """
    logger.info("Discovering ZIP URL from %s", extracts_url)
    with httpx.Client(timeout=30) as client:
        response = client.get(extracts_url)
        response.raise_for_status()

    matches = _ZIP_LINK_PATTERN.findall(response.text)
    if not matches:
        raise ValueError(f"No RealEstData ZIP link found on {extracts_url}")

    filename = matches[-1]  # Use the last match (most recent)
    url = extracts_url.rstrip("/") + "/" + filename
    logger.info("Discovered ZIP URL: %s", url)
    return url


def _download_zip(url: str) -> bytes:
    """Download ZIP file from Wake County website.

    Args:
        url: Full URL to ZIP file

    Returns:
        ZIP file content as bytes

    Raises:
        httpx.HTTPError: If download fails
    """
    logger.info("Downloading Wake County property data from %s", url)
    with httpx.Client(timeout=_DOWNLOAD_TIMEOUT) as client:
        response = client.get(url)
        response.raise_for_status()
    logger.info("Downloaded %d bytes", len(response.content))
    return response.content


def _extract_txt_from_zip(zip_bytes: bytes) -> str:
    """Extract .txt file from ZIP archive.

    Args:
        zip_bytes: ZIP file content

    Returns:
        Text file content as string

    Raises:
        ValueError: If no .txt file found or multiple .txt files
    """
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        # Find the .txt file (should be only one)
        txt_files = [name for name in zf.namelist() if name.endswith(".txt")]
        if not txt_files:
            raise ValueError("No .txt file found in ZIP archive")
        if len(txt_files) > 1:
            logger.warning("Multiple .txt files in ZIP, using first: %s", txt_files[0])

        txt_filename = txt_files[0]
        logger.info("Extracting %s from ZIP", txt_filename)
        return zf.read(txt_filename).decode("latin1")


def _parse_fwf_data(txt_content: str) -> pd.DataFrame:
    """Parse fixed-width format text into DataFrame.

    Args:
        txt_content: Fixed-width format text content

    Returns:
        DataFrame with parsed records
    """
    logger.info("Parsing fixed-width format data")

    # Build colspecs from widths (start, end positions for each column)
    colspecs = []
    start = 0
    for width in COLUMN_MAP.values():
        end = start + width
        colspecs.append((start, end))
        start = end

    # Parse all columns as strings to preserve leading zeros and prevent type conversion
    df = pd.read_fwf(
        io.StringIO(txt_content),
        colspecs=colspecs,
        names=list(COLUMN_MAP.keys()),
        dtype=str,
        encoding="latin1",
    )
    logger.info("Parsed %d records", len(df))
    return df


def _csv_val(value: str | float) -> str | None:
    """Convert CSV/DataFrame value to string or None.

    Args:
        value: Value from DataFrame

    Returns:
        String value or None if empty/missing
    """
    if pd.isna(value):
        return None
    s = str(value).strip()
    return s if s else None


def _csv_int(value: str | float) -> int | None:
    """Convert CSV/DataFrame value to integer or None.

    Args:
        value: Value from DataFrame

    Returns:
        Integer value or None if empty/missing/invalid
    """
    if pd.isna(value):
        return None
    try:
        # Handle string representations
        s = str(value).strip()
        if not s or s == "0":
            return None
        return int(float(s))  # Handle "1234.0" format
    except (ValueError, TypeError):
        return None


def _csv_float(value: str | float) -> float | None:
    """Convert CSV/DataFrame value to float or None.

    Args:
        value: Value from DataFrame

    Returns:
        Float value or None if empty/missing/invalid
    """
    if pd.isna(value):
        return None
    try:
        s = str(value).strip()
        if not s or s == "0" or s == "0.0":
            return None
        return float(s)
    except (ValueError, TypeError):
        return None


def _map_record(row: pd.Series) -> StagingWakeCountyPropertyData:
    """Map DataFrame row to StagingWakeCountyPropertyData model.

    Args:
        row: DataFrame row

    Returns:
        Model instance
    """
    return StagingWakeCountyPropertyData(
        owner_1=_csv_val(row["Owner 1"]),
        owner_2=_csv_val(row["Owner 2"]),
        address_1=_csv_val(row["Address 1"]),
        address_2=_csv_val(row["Address 2"]),
        address_3=_csv_val(row["Address 3"]),
        reid=_csv_val(row["REID"]),
        card_num=_csv_val(row["Card #"]),
        num_cards=_csv_val(row["# of Cards"]),
        street_num=_csv_val(row["Street #"]),
        street_prefix=_csv_val(row["Street Prefix"]),
        street_name=_csv_val(row["Street Name"]),
        street_type=_csv_val(row["Street Type"]),
        street_suffix=_csv_val(row["Street Suffix"]),
        street_misc=_csv_val(row["Street Misc"]),
        planning_jurisdiction=_csv_val(row["Planning Jurisdiction"]),
        township=_csv_val(row["Township"]),
        fire_district=_csv_val(row["Fire District"]),
        physical_city=_csv_val(row["Physical City"]),
        physical_zip_code=_csv_val(row["Physical Zip Code"]),
        city=_csv_val(row["City"]),
        parcel_identification=_csv_val(row["Parcel Identification"]),
        billing_class=_csv_val(row["Billing Class"]),
        land_classification=_csv_val(row["Land Classification"]),
        zoning=_csv_val(row["Zoning"]),
        deeded_acreage=_csv_float(row["Deeded Acreage"]),
        special_district_1=_csv_val(row["Special District 1"]),
        special_district_2=_csv_val(row["Special District 2"]),
        special_district_3=_csv_val(row["Special District 3"]),
        land_sale_price=_csv_float(row["Land Sale Price"]),
        land_sale_date=_csv_val(row["Land Sale Date"]),
        total_sale_price=_csv_float(row["Total Sale Price"]),
        total_sale_date=_csv_val(row["Total Sale Date"]),
        assessed_building_value=_csv_float(row["Assessed Building Value"]),
        assessed_land_value=_csv_float(row["Assessed Land Value"]),
        deed_book=_csv_val(row["Deed Book"]),
        deed_page=_csv_val(row["Deed Page"]),
        deed_date=_csv_val(row["Deed Date"]),
        property_description=_csv_val(row["Property Description"]),
        vcs=_csv_val(row["VCS"]),
        property_index=_csv_val(row["Property Index"]),
        type_use=_csv_val(row["Type & Use"]),
        year_built=_csv_int(row["Year Built"]),
        num_rooms=_csv_int(row["# Rooms"]),
        units=_csv_int(row["Units"]),
        heated_area=_csv_float(row["Heated Area"]),
        utilities=_csv_val(row["Utilities"]),
        street_pavement=_csv_val(row["Street Pavement"]),
        topography=_csv_val(row["Topography"]),
        year_of_addition=_csv_int(row["Year of Addition"]),
        effective_year=_csv_int(row["Effective Year"]),
        remodeled_year=_csv_int(row["Remodeled Year"]),
        unused=_csv_val(row["Unused"]),
        special_write_in=_csv_val(row["Special Write In"]),
        story_height=_csv_val(row["Story Height"]),
        design_style=_csv_val(row["Design Style"]),
        foundation_basement=_csv_val(row["Foundation Basement"]),
        foundation_basement_pct=_csv_val(row["Foundation Basement %"]),
        exterior_wall=_csv_val(row["Exterior Wall"]),
        common_wall=_csv_val(row["Common Wall"]),
        roof=_csv_val(row["Roof"]),
        roof_floor_system=_csv_val(row["Roof Floor System"]),
        floor_finish=_csv_val(row["Floor Finish"]),
        interior_finish=_csv_val(row["Interior Finish"]),
        interior_finish_1=_csv_val(row["Interior Finish 1"]),
        interior_finish_1_pct=_csv_val(row["Interior Finish 1 %"]),
        interior_finish_2=_csv_val(row["Interior Finish 2"]),
        interior_finish_2_pct=_csv_val(row["Interior Finish 2 %"]),
        heat=_csv_val(row["Heat"]),
        heat_pct=_csv_val(row["Heat %"]),
        air=_csv_val(row["Air"]),
        air_pct=_csv_val(row["Air %"]),
        bath=_csv_val(row["Bath"]),
        bath_fixtures=_csv_val(row["Bath Fixtures"]),
        builtin_1_description=_csv_val(row["Built In 1 Description"]),
        builtin_2_description=_csv_val(row["Built In 2 Description"]),
        builtin_3_description=_csv_val(row["Built In 3 Description"]),
        builtin_4_description=_csv_val(row["Built In 4 Description"]),
        builtin_5_description=_csv_val(row["Built In 5 Description"]),
        grade=_csv_val(row["Grade"]),
        assessed_grade_difference=_csv_val(row["Assessed Grade Difference"]),
        accrued_assessed_condition_pct=_csv_val(row["Accrued Assessed Condition %"]),
        land_deferred_code=_csv_val(row["Land Deferred Code"]),
        land_deferred_amount=_csv_float(row["Land Deferred Amount"]),
        historic_deferred_code=_csv_val(row["Historic Deferred Code"]),
        historic_deferred_amount=_csv_float(row["Historic Deferred Amount"]),
        recycled_units=_csv_int(row["Recycled Units"]),
        disqualifying_qualifying_flags=_csv_val(row["Disqualifying & Qualifying Flags"]),
        land_disqualify_qualify_flag=_csv_val(row["Land Disqualify & Qaulify Flag"]),
    )


def fetch_wake_county_property_data() -> None:
    """Fetch Wake County property data and load into staging table.

    Downloads ZIP file, extracts fixed-width text file, parses into DataFrame,
    and loads into staging_wake_county_property_data table (truncate-and-reload).

    Raises:
        Exception: On download, parse, or database errors (logged before raising)
    """
    settings = get_settings()
    session = SessionLocal()

    try:
        # Discover current ZIP URL and download
        zip_url = _discover_zip_url(settings.wake_county_extracts_url)
        zip_bytes = _download_zip(zip_url)
        txt_content = _extract_txt_from_zip(zip_bytes)

        # Parse
        df = _parse_fwf_data(txt_content)

        # Truncate existing data
        logger.info("Truncating staging_wake_county_property_data table")
        session.execute(delete(StagingWakeCountyPropertyData))
        session.commit()

        # Map and insert
        logger.info("Mapping %d records to model instances", len(df))
        records = [_map_record(row) for _, row in df.iterrows()]

        logger.info("Inserting %d records into staging table", len(records))
        session.add_all(records)
        session.commit()

        logger.info("Wake County property data load complete: %d records", len(records))

    except Exception:
        session.rollback()
        logger.exception("Failed to fetch Wake County property data")
        raise
    finally:
        session.close()

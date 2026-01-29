import sys
import os
import geopandas as gpd
from sqlalchemy import create_engine, text

# Read config from Environment Variables (injected by n8n)
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME', 'pricepoint')
TABLE_NAME = "police_incidents"

def full_reload(file_path):
    # Construct Connection String
    db_url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"
    
    print(f"Connecting to DB...")
    engine = create_engine(db_url)

    print(f"Reading {file_path}...")
    gdf = gpd.read_file(file_path)

    # --- DATA CLEANING ---
    print("Cleaning data...")

    # 1. FIX COLUMN NAMES (The Solution to your Error)
    # Rename 'GlobalID' to 'global_id' to match your SQL expectation
    gdf.rename(columns={'GlobalID': 'global_id'}, inplace=True)
    
    # Optional: Force all other columns to lowercase to avoid quoting issues in Postgres
    # e.g. 'CaseNumber' becomes 'casenumber'
    gdf.columns = gdf.columns.str.lower()
    
    # Ensure CRS is WGS84 (EPSG:4326)
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        print("Reprojecting to EPSG:4326...")
        gdf = gdf.to_crs(epsg=4326)
    
    # 3. CRITICAL FIX: Drop rows that are STILL missing geometry
    # These are rows with no Lat/Lon and no Geometry (approx 109 rows)
    # GeoPandas cannot upload 'NaN' to PostGIS
    initial_count = len(gdf)
    gdf = gdf.dropna(subset=['geometry'])
    dropped_count = initial_count - len(gdf)
    
    if dropped_count > 0:
        print(f"⚠️ Dropped {dropped_count} un-mappable rows (no coords or geometry).")

    # 4. Drop & Recreate Table (The "Replace" Logic)
    # if_exists='replace' drops the table if it exists and creates a new one
    # based on the current columns in the dataframe.
    print(f"Dropping and recreating table '{TABLE_NAME}'...")
    gdf.to_postgis(
        name=TABLE_NAME,
        con=engine,
        if_exists="replace",
        index=False,
        dtype={'geometry': 'Geometry(POINT, 4326)'}, # Forces strict PostGIS type
        chunksize=10000  # Loads in chunks to save memory
    )

    # 5. Re-Apply Indexes and Constraints
    # Since we dropped the table, we lost the Primary Key and custom indexes.
    # We must add them back manually.
    print("Re-applying indexes and constraints...")
    
    with engine.begin() as conn:
        # A. Set Primary Key (Critical for performance/integrity)
        conn.execute(text(f"ALTER TABLE {TABLE_NAME} ADD PRIMARY KEY (global_id);"))
        
        # B. Create Spatial Index (Crucial for map queries)
        # Note: to_postgis sometimes adds this, but explicit creation is safer
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_geom ON {TABLE_NAME} USING GIST (geometry);"))
        
        # C. Create Standard Indexes (For filtering)
        # Check if columns exist before indexing to avoid errors if you removed them
        if 'reported_date' in gdf.columns:
            conn.execute(text(f"CREATE INDEX idx_{TABLE_NAME}_date ON {TABLE_NAME} (reported_date);"))
        
        if 'crime_category' in gdf.columns:
            conn.execute(text(f"CREATE INDEX idx_{TABLE_NAME}_category ON {TABLE_NAME} (crime_category);"))

    print("✅ Full reload complete. Table structure matches current file.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to the geodata file")
    args = parser.parse_args()

    # DB credentials should be read from Environment Variables
    # which we will inject via Kubernetes later.
    full_reload(args.file)
"""
NeerNiti — Data Ingestion Layer: CGWB & UP Ground Water Department Telemetry
Parses real exported CSV files from India-WRIS / National Water Data Portal (NWDP),
populates `well_telemetry` in PostGIS, and logs execution into `data_refresh_log`.
"""

import os
import sys
import glob
import logging
from datetime import datetime, timezone
import pandas as pd
from sqlalchemy import text

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend"))
sys.path.append(backend_dir)

from app.db.session import SessionLocal
from app.db.models import Region, DataRefreshLog

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def ensure_telemetry_schema(db):
    """Ensures PostGIS tables exist for raw well telemetry."""
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS well_telemetry (
            id SERIAL PRIMARY KEY,
            station_name VARCHAR(120),
            district VARCHAR(60),
            location GEOMETRY(Point, 4326),
            reading_date DATE,
            water_level_m_bgl FLOAT,
            source VARCHAR(80),
            UNIQUE (station_name, reading_date)
        );
        CREATE INDEX IF NOT EXISTS idx_well_telemetry_geom ON well_telemetry USING GIST (location);
    """))
    db.commit()


def locate_csv_files() -> list[str]:
    """Finds all candidate groundwater telemetry CSVs in data directories."""
    search_dirs = [
        os.path.join(backend_dir, "data", "raw"),
        os.path.join(backend_dir, "data"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../data")),
    ]
    files = []
    for d in search_dirs:
        if os.path.exists(d):
            files.extend(glob.glob(os.path.join(d, "*.csv")))
    return list(set(files))


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalizes variations in India-WRIS / UP Ground Water export headers."""
    col_map = {}
    for col in df.columns:
        c_clean = col.strip().lower().replace("_", " ")
        if any(k in c_clean for k in ["station", "site name", "well name", "location"]):
            col_map[col] = "station_name"
        elif "district" in c_clean:
            col_map[col] = "district"
        elif any(k in c_clean for k in ["latitude", "lat"]):
            col_map[col] = "latitude"
        elif any(k in c_clean for k in ["longitude", "long", "lon"]):
            col_map[col] = "longitude"
        elif any(k in c_clean for k in ["date", "time", "timestamp"]):
            col_map[col] = "reading_date"
        elif any(k in c_clean for k in ["level", "depth", "water level", "mbgl", "m bgl"]):
            col_map[col] = "water_level_m_bgl"

    return df.rename(columns=col_map)


def ingest_groundwater_telemetry(csv_source_path: str | None = None) -> None:
    """Main CSV ingestion routine for real telemetry data."""
    db = SessionLocal()
    ensure_telemetry_schema(db)
    
    csv_files = [csv_source_path] if csv_source_path and os.path.exists(csv_source_path) else locate_csv_files()

    if not csv_files:
        logger.warning("⚠️ No telemetry CSV files found in backend/data/raw or backend/data.")
        logger.info("ℹ️ Place exported CSVs (e.g., cgwb_wells_prayagraj.csv) in backend/data/raw/")
        db.close()
        return

    logger.info(f"📂 Found {len(csv_files)} telemetry CSV files to process.")
    total_records = 0

    for file_path in csv_files:
        filename = os.path.basename(file_path)
        logger.info(f"⏳ Ingesting: {filename}...")
        try:
            df = pd.read_csv(file_path, low_memory=False)
            df = standardize_columns(df)

            required = {"station_name", "latitude", "longitude", "reading_date", "water_level_m_bgl"}
            if not required.issubset(df.columns):
                logger.warning(f"⚠️ Skipping {filename}: Missing columns. Found: {list(df.columns)}")
                continue

            upsert_query = text("""
                INSERT INTO well_telemetry (station_name, district, location, reading_date, water_level_m_bgl, source)
                VALUES (:stn, :dist, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), :dt, :val, :src)
                ON CONFLICT (station_name, reading_date) 
                DO UPDATE SET water_level_m_bgl = EXCLUDED.water_level_m_bgl;
            """)

            records_in_file = 0
            for _, row in df.iterrows():
                try:
                    lat = float(row["latitude"])
                    lng = float(row["longitude"])
                    val = float(row["water_level_m_bgl"])
                    dt_val = pd.to_datetime(row["reading_date"]).date()
                    district = str(row.get("district", "Uttar Pradesh")).strip()
                    stn = str(row["station_name"]).strip()

                    # Basic spatial bounding box filter for UP region
                    if 20.0 <= lat <= 30.0 and 75.0 <= lng <= 88.0 and not pd.isna(val):
                        db.execute(upsert_query, {
                            "stn": stn,
                            "dist": district,
                            "lat": lat,
                            "lng": lng,
                            "dt": dt_val,
                            "val": val,
                            "src": filename
                        })
                        records_in_file += 1
                except Exception:
                    continue

            db.commit()
            total_records += records_in_file
            logger.info(f"✅ Ingested {records_in_file} readings from {filename}.")

            db.add(DataRefreshLog(
                region_id=None,
                source_name=f"India-WRIS / NWDP ({filename})",
                fetched_at=datetime.now(timezone.utc),
                status="success",
                error_message=f"Ingested {records_in_file} well level records."
            ))
            db.commit()

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to process {filename}: {e}")

    logger.info(f"🎉 Completed telemetry ingestion. Total records persisted: {total_records}")
    db.close()


if __name__ == "__main__":
    ingest_groundwater_telemetry()
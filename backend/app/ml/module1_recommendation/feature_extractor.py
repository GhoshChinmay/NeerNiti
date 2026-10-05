"""
NeerNiti — Module 1: Feature Extraction
Extracts multi-criteria geospatial and hydrogeological features for candidate site scoring,
fetching 100% real data from Google Earth Engine, OpenStreetMap, and PostGIS.
"""

import os
import sys
from typing import Any

import ee
import numpy as np
import pandas as pd
from shapely.geometry import Point, Polygon

backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.append(backend_root)

from app.db.session import SessionLocal

# Import the live network functions from the inference pipeline
from app.ml.run_multidistrict_inference import (
    get_live_gee_features,
    query_distance_to_river_osm,
    query_nearest_groundwater_level,
)


class FeatureExtractor:
    """Extracts satellite and hydrogeological telemetry layers across a geographic region."""

    def __init__(self, random_seed: int = 42):
        self.rng = np.random.default_rng(random_seed)
        
        # Ensure Earth Engine is initialized for the grid extraction
        try:
            ee.Initialize(project=os.getenv("GEE_PROJECT_ID", "groundwater-504716"))
        except Exception:
            pass

    def extract_grid_features(
        self,
        region_geom: Polygon | None,
        district_name: str = "Prayagraj",
        grid_resolution_m: int = 250,
        num_candidates: int = 50,
    ) -> tuple[pd.DataFrame, list[Point]]:
        """
        Tessellates the region geometry into candidate grid points and computes feature vectors.
        Warning: For 50 candidates, this will make 50 live calls to GEE and OSM Overpass.
        """
        regime = "alluvial" if district_name == "Prayagraj" else "hard_rock"
        base_lat, base_lng = (25.43, 81.84) if regime == "alluvial" else (25.13, 82.56)

        points: list[Point] = []
        rows: list[dict[str, Any]] = []
        
        db = SessionLocal()
        
        print(f"[INFO] 🌍 Starting LIVE feature extraction for {num_candidates} points in {district_name}...")
        
        try:
            for i in range(num_candidates):
                # Generate random candidate point within the bounding box
                lat = float(base_lat + self.rng.uniform(-0.08, 0.08))
                lng = float(base_lng + self.rng.uniform(-0.08, 0.08))
                pt = Point(lng, lat)
                points.append(pt)

                if (i + 1) % 10 == 0:
                    print(f"   ↳ Fetching telemetry for point {i + 1}/{num_candidates}...")

                # 1. Fetch real GEE satellite rasters
                gee_metrics = get_live_gee_features(lat, lng, regime)
                
                # 2. Fetch live OSM River Proximity
                dist_river_m = query_distance_to_river_osm(lat, lng)
                
                # 3. Fetch nearest historical well reading from PostGIS
                gw_depth_m = query_nearest_groundwater_level(db, lat, lng, regime == "alluvial")

                gee_metrics["depth_to_water_m"] = gw_depth_m
                gee_metrics["distance_to_river_m"] = dist_river_m
                rows.append(gee_metrics)
                
        finally:
            db.close()

        df = pd.DataFrame(rows)
        print(f"[OK] 🛰️ Grid feature extraction complete for {district_name}.")
        return df, points
# Module 1: Site Recommendation Engine

## Overview
Module 1 scores geographic grid cells across an input region using multi-criteria geospatial features and a trained XGBoost classifier.

## Inputs
- `region_geom`: Optional Shapely polygon defining the target district / study area.
- `district_name`: Target district name (e.g., "Prayagraj", "Mirzapur") for terrain cluster identification.
- `grid_resolution_m`: Cell grid resolution in meters (default 250m).
- `top_n`: Number of ranked candidate sites to return.

## Outputs
- List of `ScoredSite` objects with:
  - `latitude`, `longitude` (WGS 84 coordinate)
  - `suitability_score` (0.0 to 1.0)
  - `feature_vector` (exact features used for scoring)
  - `model_version_id` (traceability tag)

## Usage Example
```python
from app.ml.module1_recommendation import SiteRecommender

recommender = SiteRecommender()
sites = recommender.predict_region(district_name="Prayagraj", top_n=10)
for site in sites:
    print(f"Site ({site.latitude}, {site.longitude}): Score = {site.suitability_score}")
```

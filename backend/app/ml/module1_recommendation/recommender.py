"""
NeerNiti — Module 1: Site Recommendation Engine
Trains, loads, and executes the multi-criteria XGBoost suitability classifier.
"""

import glob
import os
from dataclasses import dataclass
from typing import Any

import joblib
from shapely.geometry import Polygon

from app.ml.module1_recommendation.feature_extractor import FeatureExtractor


@dataclass
class ScoredSite:
    latitude: float
    longitude: float
    suitability_score: float
    feature_vector: dict[str, Any]
    model_version_id: str


class RegimeEnsembleWrapper:
    def __init__(self, models_dict):
        self.models = models_dict

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        probs = np.zeros((len(X), 2))
        probs[:, 0] = 1.0  # default to 0 class
        for regime, model in self.models.items():
            regime_col = f"regime_{regime}"
            if regime_col in X.columns:
                mask = X[regime_col] == 1.0
                if mask.sum() > 0:
                    probs[mask] = model.predict_proba(X[mask])
        return probs


class SiteRecommender:
    """Multi-criteria Site Recommendation Engine powered by XGBoost / Random Forest."""

    def __init__(self, model_path: str | None = None):
        self.model: Any = None
        self.feature_names: list[str] = []
        self.model_version_id: str = "site_rec_xgb_v1.2_default"
        self.feature_extractor = FeatureExtractor()

        if model_path:
            self.load_model(model_path)
        else:
            self._load_latest_model()

    def _load_latest_model(self) -> None:
        """Finds and loads the latest trained model artifact."""
        ml_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        pkl_files = glob.glob(os.path.join(ml_dir, "neerniti_up_v5.2_*.pkl"))

        if pkl_files:
            latest_pkl = max(pkl_files, key=os.path.getctime)
            self.load_model(latest_pkl)
        else:
            # Fallback feature list
            self.feature_names = [
                "slope_deg", "drainage_density", "ndvi", "rainfall_mm",
                "depth_to_groundwater_m", "distance_to_river_m",
                "geology_hardrock", "soil_clay_pct"
            ]

    def load_model(self, path: str) -> None:
        """Loads a serialized model artifact and its feature order manifest."""
        data = joblib.load(path)
        if isinstance(data, dict):
            if data.get("algorithm") == "RegimeEnsemble":
                self.model = RegimeEnsembleWrapper(data["models"])
            else:
                self.model = data.get("model", data)
            self.feature_names = data.get("feature_names", [])
            self.model_version_id = data.get("version_id", "neerniti_up_v5.2")
        else:
            self.model = data
            self.feature_names = [
                'delta_sar_vv_vh', 'delta_ndwi', 'slope_deg', 'curvature', 'sobel_fracture',
                'monsoon_rainfall_mm', 'soil_clay_pct', 'flow_accumulation', 'grace_gw_storage_cm',
                'distance_to_river_m', 'elevation_m', 'twi'
            ]
            self.model_version_id = os.path.basename(path).replace(".pkl", "")

    def predict_region(
        self,
        region_geom: Polygon | None = None,
        district_name: str = "Prayagraj",
        grid_resolution_m: int = 250,
        top_n: int = 20,
    ) -> list[ScoredSite]:
        """Scores candidate cells across a region and returns the top_n highest suitability sites.

        Args:
            region_geom: Region boundary geometry.
            district_name: Name of district for terrain cluster identification.
            grid_resolution_m: Spatial resolution in meters.
            top_n: Number of top candidate sites to return.

        Returns:
            List of ScoredSite objects sorted descending by suitability score.
        """
        df_features, points = self.feature_extractor.extract_grid_features(
            region_geom=region_geom,
            district_name=district_name,
            grid_resolution_m=grid_resolution_m,
            num_candidates=max(50, top_n * 2),
        )

        df_aligned = df_features[self.feature_names] if self.feature_names else df_features

        if self.model is not None:
            # Execute XGBoost probabilistic prediction
            probabilities = self.model.predict_proba(df_aligned)[:, 1]
        else:
            # Domain MCDA fallback scoring
            probabilities = (
                (1.0 - (df_features["slope_deg"] / 10.0)) * 0.25 +
                (df_features["ndvi"]) * 0.25 +
                (df_features["depth_to_groundwater_m"] / 30.0) * 0.30 +
                (df_features["rainfall_mm"] / 1200.0) * 0.20
            ).clip(0.1, 0.98).to_numpy()

        scored_sites: list[ScoredSite] = []
        for i, pt in enumerate(points):
            score = float(probabilities[i])
            site = ScoredSite(
                latitude=round(float(pt.y), 5),
                longitude=round(float(pt.x), 5),
                suitability_score=round(score, 4),
                feature_vector=df_features.iloc[i].to_dict(),
                model_version_id=self.model_version_id,
            )
            scored_sites.append(site)

        # Sort descending by score and return top_n
        scored_sites.sort(key=lambda s: s.suitability_score, reverse=True)
        return scored_sites[:top_n]

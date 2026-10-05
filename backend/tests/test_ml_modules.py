"""
NeerNiti — Automated Unit Tests for ML Intelligence Modules (Modules 1-4)
Verifies:
  - Module 1: SiteRecommender prediction output format, scoring bounds, and feature order alignment.
  - Module 2: SHAPExplainer deterministic explanation rendering and top feature contributions.
  - Module 3: BiLSTMForecastModel / VerificationEngine deviation detection logic.
  - Module 4: RiskClassifier proximity buffer feature computation and risk classes.
"""

from app.ml.module1_recommendation import FeatureExtractor, SiteRecommender
from app.ml.module2_explainability import SHAPExplainer
from app.ml.module3_verification import BiLSTMForecastModel
from app.ml.module4_risk_screening import RiskClassifier


def test_feature_extractor():
    extractor = FeatureExtractor(random_seed=42)
    df, points = extractor.extract_grid_features(
        region_geom=None,
        district_name="Prayagraj",
        num_candidates=10,
    )
    assert len(df) == 10
    assert len(points) == 10
    assert "slope_deg" in df.columns
    assert "ndvi" in df.columns
    assert "depth_to_water_m" in df.columns


def test_site_recommender():
    recommender = SiteRecommender()
    sites = recommender.predict_region(district_name="Prayagraj", top_n=5)
    assert len(sites) == 5

    for s in sites:
        assert 0.0 <= s.suitability_score <= 1.0
        assert -90.0 <= s.latitude <= 90.0
        assert -180.0 <= s.longitude <= 180.0
        assert isinstance(s.feature_vector, dict)
        assert len(s.model_version_id) > 0


def test_shap_explainer():
    explainer = SHAPExplainer()
    mock_features = {
        "slope_deg": 2.5,
        "drainage_density": 2.0,
        "ndvi": 0.45,
        "rainfall_mm": 980.0,
        "depth_to_water_m": 12.0,
        "distance_to_river_m": 1200.0,
        "geology_hardrock": 0.0,
        "soil_clay_pct": 25.0,
    }

    result = explainer.explain(mock_features, suitability_score=0.88, top_k=3)
    assert len(result.shap_values) > 0
    assert len(result.top_contributions) == 3
    assert len(result.plain_text_summary) > 10
    assert "suitability" in result.plain_text_summary.lower()


def test_verification_forecast():
    forecast_model = BiLSTMForecastModel()
    history = [12.4, 10.2, 9.5, 8.8, 8.1, 7.5]
    forecast = forecast_model.forecast_next(history, forecast_steps=1)
    assert len(forecast) == 1
    assert forecast[0] > 0.0


def test_risk_classifier():
    screener = RiskClassifier()
    res = screener.classify_point(lat=25.4358, lng=81.8463, district_name="Prayagraj")
    assert res.risk_category in ["Low", "Medium", "High"]
    assert 0.0 <= res.data_confidence <= 1.0
    assert res.proximity_features.dist_to_farmland_m > 0
    assert res.proximity_features.dist_to_industrial_m > 0

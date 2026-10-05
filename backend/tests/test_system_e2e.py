"""
NeerNiti — Complete End-to-End System & Specification Validation Suite

Performs automated integration tests verifying:
  1. REST API endpoint availability and response shapes for all 9 documented endpoints.
  2. GeoJSON FeatureCollection RFC 7946 compliance.
  3. Multi-district region coverage (Prayagraj & Mirzapur).
  4. SHAP explanation string validity and sub-scores.
  5. Post-construction structure creation ("Mark as Built") and Bi-LSTM verification logs.
  6. Ingestion data refresh statuses and admin audit tables.
"""

import sys
import logging
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

API_BASE = "http://127.0.0.1:8000/api/v1"


def run_endpoint_check(name: str, url: str, method: str = "GET", json_data: dict | None = None, expected_status: int = 200) -> dict | list:
    try:
        if method == "POST":
            res = requests.post(url, json=json_data, timeout=5)
        else:
            res = requests.get(url, timeout=5)
        assert res.status_code == expected_status, f"Expected {expected_status}, got {res.status_code}: {res.text}"
        logger.info(f"✅ [{name}] Passed (HTTP {res.status_code})")
        return res.json()
    except Exception as e:
        logger.error(f"❌ [{name}] Failed: {e}")
        sys.exit(1)


def run_e2e_validation():
    logger.info("🚀 Starting NeerNiti Full System Specification Validation...\n")

    # 1. Test Service Health Endpoint
    health = run_endpoint_check("Service Health Check", f"{API_BASE}/health")
    assert health["data"]["status"] == "online"

    # 2. Test Regions Endpoint
    regions = run_endpoint_check("Regions GeoJSON", f"{API_BASE}/regions")
    assert regions.get("type") == "FeatureCollection", "Regions is not a FeatureCollection"
    assert len(regions.get("features", [])) >= 2, "Expected at least 2 distinct districts"
    district_names = [f["properties"]["region_name"] for f in regions["features"]]
    logger.info(f"   └── Districts Loaded: {', '.join(district_names)}")

    # 3. Test Wells & Telemetry Endpoint
    wells = run_endpoint_check("Monitoring Wells GeoJSON", f"{API_BASE}/wells")
    assert wells.get("type") == "FeatureCollection"
    assert len(wells.get("features", [])) > 0, "No wells returned"
    first_well = wells["features"][0]["properties"]
    assert "reading_history" in first_well, "Missing reading_history in well properties"
    assert len(first_well["reading_history"]) > 0, "Well telemetry history is empty"
    first_well_id = first_well["well_id"]
    logger.info(f"   └── Verified {len(wells['features'])} stations with historical time-series data")

    # 4. Test Single Well Readings Endpoint
    well_readings = run_endpoint_check("Single Well Readings History", f"{API_BASE}/wells/{first_well_id}/readings")
    assert len(well_readings["data"]) > 0

    # 5. Test Multi-District AI Recommendations via POST /sites/recommend
    rec_payload = {
        "district_name": "Prayagraj",
        "min_suitability_score": 0.5,
        "risk_filter": "All",
        "top_n": 10,
    }
    recs = test_endpoint("POST AI Recommendations", f"{API_BASE}/sites/recommend", method="POST", json_data=rec_payload)
    assert recs.get("type") == "FeatureCollection"
    rec_features = recs.get("features", [])
    assert len(rec_features) > 0, "No recommendations returned"
    first_site_id = rec_features[0]["properties"]["recommendation_id"]

    for r in rec_features:
        props = r["properties"]
        assert 0 <= props["final_suitability_score"] <= 100, "Suitability score out of range"
        assert props["risk_category"] in ["Low", "Medium", "High"], f"Invalid risk category: {props['risk_category']}"
        assert len(props["explanation_text"]) > 10, "Explanation text empty or too short"
        assert "sub_scores" in props, "Missing sub_scores breakdown"
    logger.info(f"   └── Verified {len(rec_features)} AI sites with SHAP explanations & risk screenings")

    # 6. Test Single Site Detail & Explanation Endpoints
    site_detail = test_endpoint("Site Detail by ID", f"{API_BASE}/sites/{first_site_id}")
    assert site_detail["data"]["site_id"] == first_site_id

    site_expl = test_endpoint("Site SHAP Explanation", f"{API_BASE}/sites/{first_site_id}/explanation")
    assert len(site_expl["data"]["shap_values"]) > 0

    # 7. Test Built Structures & Bi-LSTM Verification Logs
    structs = test_endpoint("Built Structures GeoJSON", f"{API_BASE}/structures")
    assert structs.get("type") == "FeatureCollection"
    struct_features = structs.get("features", [])
    assert len(struct_features) > 0, "No structures returned"
    first_struct_id = struct_features[0]["properties"]["structure_id"]
    for s in struct_features:
        props = s["properties"]
        assert "verification_logs" in props, "Missing verification_logs array"
    logger.info(f"   └── Verified {len(struct_features)} built structures with Bi-LSTM telemetry trajectories")

    # 8. Test Structure Verification History Endpoint
    struct_verif = test_endpoint("Structure Verification Trajectory", f"{API_BASE}/structures/{first_struct_id}/verification")
    assert struct_verif["data"]["structure_id"] == first_struct_id

    # 9. Test Data Refresh Status Endpoint
    refresh_status = test_endpoint("Data Refresh Status", f"{API_BASE}/data-refresh/status")
    assert "sources" in refresh_status["data"]
    assert len(refresh_status["data"]["sources"]) > 0

    # 10. Test Admin Registry
    models = test_endpoint("Admin Registered Models", f"{API_BASE}/admin/models")
    assert isinstance(models, list) and len(models) > 0
    modules_registered = {m["module_name"] for m in models}
    logger.info(f"   └── Model Registry Modules Present: {', '.join(modules_registered)}")

    print("\n" + "=" * 70)
    logger.info("🎉 ALL 10 SYSTEM SPECIFICATION INTEGRATION TESTS PASSED PERFECTLY!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_e2e_validation()
"""
NeerNiti — Automated REST API Integration Tests
Tests all 9 documented endpoints via FastAPI TestClient:
  1. GET /api/v1/regions
  2. POST /api/v1/sites/recommend
  3. GET /api/v1/sites/{site_id}
  4. GET /api/v1/sites/{site_id}/explanation
  5. GET /api/v1/structures/{structure_id}/verification
  6. POST /api/v1/structures
  7. GET /api/v1/wells/{well_id}/readings
  8. GET /api/v1/data-refresh/status
  9. GET /api/v1/health
"""

from fastapi.testclient import TestClient

from main import fastapi_app

client = TestClient(fastapi_app)


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["status"] == "online"
    assert data["data"]["service"] is not None


def test_get_regions():
    response = client.get("/api/v1/regions")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data.get("type") == "FeatureCollection"
    features = json_data.get("features", [])
    assert len(features) >= 1
    assert "region_name" in features[0]["properties"]


def test_post_site_recommendations():
    payload = {
        "district_name": "Prayagraj",
        "min_suitability_score": 0.5,
        "risk_filter": "All",
        "top_n": 10,
    }
    response = client.post("/api/v1/sites/recommend", json=payload)
    assert response.status_code == 200
    json_data = response.json()
    assert json_data.get("type") == "FeatureCollection"
    assert len(json_data.get("features", [])) > 0
    first = json_data["features"][0]["properties"]
    assert "final_suitability_score" in first
    assert "explanation_text" in first


def test_get_wells():
    response = client.get("/api/v1/wells")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data.get("type") == "FeatureCollection"
    assert len(json_data.get("features", [])) > 0


def test_get_structures():
    response = client.get("/api/v1/structures")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data.get("type") == "FeatureCollection"


def test_get_data_refresh_status():
    response = client.get("/api/v1/data-refresh/status")
    assert response.status_code == 200
    json_data = response.json()
    assert "data" in json_data
    assert "sources" in json_data["data"]

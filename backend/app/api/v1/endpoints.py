"""
NeerNiti — REST API Layer (v1 Endpoints)
Implements all 9 core documented REST endpoints with Pydantic validation and standard response envelopes.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from shapely import wkb
from sqlalchemy.orm import Session

from app.db.repositories import (
    DataRefreshLogRepository,
    ModelVersionRepository,
    RegionRepository,
    SiteRepository,
    StructureRepository,
    VerificationLogRepository,
    WellRepository,
)
from app.db.session import SessionLocal
from app.ml.llm_advisor import advisor
from app.ml.module2_explainability import SHAPExplainer
from app.models.schemas import (
    ApiResponse,
    DataRefreshStatusResponse,
    ExplanationDetail,
    HealthResponse,
    ModelVersionItem,
    ReadingItem,
    RefreshStatusItem,
    RegionFeature,
    RegionFeatureCollection,
    RegionProperties,
    SiteDetailResponse,
    SiteFeatureCollection,
    SiteProperties,
    SiteRecommendRequest,
    StructureCreateRequest,
    StructureFeature,
    StructureFeatureCollection,
    StructureProperties,
    StructureVerificationDetail,
    SubScores,
    VerificationLogItem,
    WellFeature,
    WellFeatureCollection,
    WellProperties,
)
from app.models.schemas import (
    SiteFeature as SiteFeatureGeoJson,
)

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def geometry_to_geojson_dict(spatial_column: Any) -> dict[str, Any] | None:
    """Converts a GeoAlchemy2 Geography/Geometry column to a GeoJSON dict using Shapely."""
    if spatial_column is None:
        return None
    try:
        shape = wkb.loads(bytes(spatial_column.data))
        return shape.__geo_interface__
    except Exception:
        return None


# -------------------------------------------------------------------------
# 1. GET /api/v1/regions
# -------------------------------------------------------------------------
@router.get("/regions", response_model=RegionFeatureCollection)
def list_regions(db: Session = Depends(get_db)):
    """List selectable regions (states/districts) as GeoJSON FeatureCollection."""
    repo = RegionRepository(db)
    regions = repo.get_all()
    features: list[RegionFeature] = []

    for r in regions:
        features.append(
            RegionFeature(
                geometry=geometry_to_geojson_dict(r.boundary_geom),
                properties=RegionProperties(
                    region_id=r.region_id,
                    region_name=r.region_name,
                    region_type=r.region_type,
                    state=r.state,
                ),
            )
        )

    return RegionFeatureCollection(features=features)


# -------------------------------------------------------------------------
# 2. POST /api/v1/sites/recommend & GET /api/v1/recommendations
# -------------------------------------------------------------------------
@router.post("/sites/recommend", response_model=SiteFeatureCollection)
def recommend_sites(
    payload: SiteRecommendRequest,
    db: Session = Depends(get_db),
):
    """Run/retrieve multi-criteria site recommendations for a given region (strictly filtered to suitability > 0.60)."""
    site_repo = SiteRepository(db)
    
    # Enforce minimum threshold >= 0.60 (policy requirement)
    req_min_score = payload.min_suitability_score if payload.min_suitability_score else 0.60
    effective_min_score = max(0.60, float(req_min_score))

    sites = site_repo.get_all(
        region_id=payload.region_id,
        min_score=effective_min_score,
        risk_category=payload.risk_filter,
        limit=payload.top_n,
    )

    features: list[SiteFeatureGeoJson] = []
    for site in sites:
        score_raw = float(site.suitability_score)
        # Strict cutoff: only recommend sites > 0.60
        if score_raw < 0.60:
            continue

        feat = site.feature
        expl = site.explanation
        score_val = round(score_raw * 100, 2)
        slope_val = round(float(feat.slope_deg), 2) if feat else 0.0

        features.append(
            SiteFeatureGeoJson(
                geometry=geometry_to_geojson_dict(site.location),
                properties=SiteProperties(
                    recommendation_id=site.site_id,
                    final_suitability_score=score_val,
                    structure_type="Check Dam" if slope_val > 3.0 else "Percolation Tank",
                    risk_category=site.risk_category or "Low",
                    explanation_text=expl.plain_text_summary if expl else "High suitability location confirmed by hydrogeological assessment.",
                    sub_scores=SubScores(
                        slope_score=slope_val,
                        ndvi_score=0.0,
                        water_level_score=0.0,
                    ),
                    model_version_id=site.model_version_id,
                    created_at=site.created_at.isoformat() if site.created_at else None,
                ),
            )
        )

    return SiteFeatureCollection(features=features)


@router.get("/recommendations", response_model=SiteFeatureCollection)
def get_recommendations_alias(
    region_id: uuid.UUID | None = Query(None),
    min_score: float = Query(0.60),
    risk: str | None = Query("All"),
    limit: int = Query(50),
    db: Session = Depends(get_db),
):
    """Legacy GET alias for frontend compatibility with strict >= 0.60 filter."""
    normalized_min = max(0.60, min_score / 100.0 if min_score > 1.0 else min_score)
    req = SiteRecommendRequest(
        region_id=region_id,
        min_suitability_score=normalized_min,
        risk_filter=risk,
        top_n=limit,
    )
    return recommend_sites(req, db)


# -------------------------------------------------------------------------
# 3. GET /api/v1/sites/{site_id}
# -------------------------------------------------------------------------
@router.get("/sites/{site_id}", response_model=ApiResponse[SiteDetailResponse])
def get_site_detail(site_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get full detail for a single candidate site, enhanced with LLM explainability."""
    repo = SiteRepository(db)
    site = repo.get_by_id(site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site {site_id} not found",
        )

    geom_dict = geometry_to_geojson_dict(site.location)
    coords = geom_dict.get("coordinates", [0.0, 0.0]) if geom_dict else [0.0, 0.0]

    feat = site.feature
    expl = site.explanation

    slope_deg = float(feat.slope_deg) if feat else 1.8
    stype = "Check Dam" if slope_deg > 3.0 else "Percolation Tank"

    features_dict = {
        "slope_deg": slope_deg,
        "soil_type": feat.soil_type if feat else "Alluvial Sandy Loam",
        "land_use": feat.land_use if feat else "Agricultural/Barren",
        "rainfall_mm": float(feat.rainfall_mm) if feat else 850.0,
        "drainage_density": float(feat.drainage_density) if feat else 1.9,
        "geology_type": feat.geology_type if feat else "Alluvial Aquifer",
        "depth_to_groundwater_m": float(feat.depth_to_groundwater_m) if feat else 9.5,
    } if feat else None

    # Invoke LLM Hydrogeological Advisor for plain-English civic summary and civil engineering specs
    llm_analysis = advisor.generate_site_explanation(
        site_id=str(site.site_id),
        lat=coords[1],
        lng=coords[0],
        suitability_score=float(site.suitability_score),
        structure_type=stype,
        features=features_dict or {},
        shap_values=expl.shap_values if expl and expl.shap_values else {},
        risk_category=site.risk_category or "Low",
    )

    civic_summary = llm_analysis.get("civic_summary", expl.plain_text_summary if expl else "High suitability candidate.")

    expl_detail = ExplanationDetail(
        site_id=site.site_id,
        shap_values=expl.shap_values if expl else {},
        top_contributions=[],
        plain_text_summary=civic_summary,
        generated_at=expl.generated_at if expl else site.created_at,
    )

    data = SiteDetailResponse(
        site_id=site.site_id,
        region_id=site.region_id,
        latitude=coords[1],
        longitude=coords[0],
        suitability_score=site.suitability_score,
        risk_category=site.risk_category or "Low",
        model_version_id=site.model_version_id,
        features=features_dict,
        explanation=expl_detail,
        created_at=site.created_at,
    )

    return ApiResponse(data=data, error=None)


# -------------------------------------------------------------------------
# 4. GET /api/v1/sites/{site_id}/explanation
# -------------------------------------------------------------------------
@router.get("/sites/{site_id}/explanation", response_model=ApiResponse[ExplanationDetail])
def get_site_explanation(site_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get SHAP-based explanation for a candidate site."""
    repo = SiteRepository(db)
    site = repo.get_by_id(site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site {site_id} not found",
        )

    expl = site.explanation
    if not expl:
        # Generate inline using SHAPExplainer if not persisted yet
        explainer = SHAPExplainer()
        features_dict = site.feature.__dict__ if site.feature else {}
        result = explainer.explain(features_dict, suitability_score=site.suitability_score)
        data = ExplanationDetail(
            site_id=site.site_id,
            shap_values=result.shap_values,
            top_contributions=result.top_contributions,
            plain_text_summary=result.plain_text_summary,
            generated_at=datetime.now(timezone.utc),
        )
    else:
        sorted_shap = sorted(expl.shap_values.items(), key=lambda kv: abs(kv[1]), reverse=True)[:3]
        top_contribs = [
            {"feature_name": k, "value": v, "direction": "positive" if v > 0 else "negative"}
            for k, v in sorted_shap
        ]
        data = ExplanationDetail(
            site_id=site.site_id,
            shap_values=expl.shap_values,
            top_contributions=top_contribs,
            plain_text_summary=expl.plain_text_summary,
            generated_at=expl.generated_at,
        )

    return ApiResponse(data=data, error=None)


# -------------------------------------------------------------------------
# 5. GET /api/v1/structures/{structure_id}/verification
# -------------------------------------------------------------------------
@router.get("/structures/{structure_id}/verification", response_model=ApiResponse[StructureVerificationDetail])
def get_structure_verification(structure_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get verification history and trend logs for a built structure."""
    struct_repo = StructureRepository(db)
    structure = struct_repo.get_by_id(structure_id)
    if not structure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Structure {structure_id} not found",
        )

    v_repo = VerificationLogRepository(db)
    logs = v_repo.get_logs_for_structure(structure_id)

    log_items = [
        VerificationLogItem(
            date=l.check_date.isoformat(),
            predicted_m=round(float(l.predicted_level_m), 2),
            actual_m=round(float(l.actual_level_m), 2),
            deviation_pct=round(float(l.deviation_pct), 2),
            status=l.status,
        )
        for l in logs
    ]

    latest_status = log_items[-1].status if log_items else structure.status

    data = StructureVerificationDetail(
        structure_id=structure.structure_id,
        structure_type=structure.structure_type,
        build_date=structure.build_date,
        status=structure.status,
        latest_status=latest_status,
        verification_logs=log_items,
    )
    return ApiResponse(data=data, error=None)


# -------------------------------------------------------------------------
# 6. POST /api/v1/structures ("Mark as Built") & GET /api/v1/structures
# -------------------------------------------------------------------------
@router.post("/structures", response_model=ApiResponse[StructureProperties], status_code=status.HTTP_201_CREATED)
def create_structure(payload: StructureCreateRequest, db: Session = Depends(get_db)):
    """Register a newly built structure against a recommended site."""
    struct_repo = StructureRepository(db)
    try:
        structure = struct_repo.create_from_site(
            site_id=payload.site_id,
            structure_type=payload.structure_type,
            build_date=payload.build_date,
            status=payload.status,
        )

        data = StructureProperties(
            structure_id=structure.structure_id,
            site_id=structure.site_id,
            structure_type=structure.structure_type,
            build_date=structure.build_date.isoformat(),
            construction_date=structure.build_date.isoformat(),
            current_status=structure.status,
            verification_logs=[],
        )
        return ApiResponse(data=data, error=None)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/structures", response_model=StructureFeatureCollection)
def list_structures(db: Session = Depends(get_db)):
    """Returns all constructed structures and their verification history as GeoJSON."""
    struct_repo = StructureRepository(db)
    structures = struct_repo.get_all()
    features: list[StructureFeature] = []

    for struct in structures:
        logs = struct.verification_logs
        log_items = [
            VerificationLogItem(
                date=l.check_date.isoformat(),
                predicted_m=round(float(l.predicted_level_m), 2),
                actual_m=round(float(l.actual_level_m), 2),
                deviation_pct=round(float(l.deviation_pct), 2),
                status=l.status,
            )
            for l in logs
        ]

        current_status = log_items[-1].status if log_items else struct.status

        features.append(
            StructureFeature(
                geometry=geometry_to_geojson_dict(struct.location),
                properties=StructureProperties(
                    structure_id=struct.structure_id,
                    site_id=struct.site_id,
                    structure_type=struct.structure_type,
                    build_date=struct.build_date.isoformat(),
                    construction_date=struct.build_date.isoformat(),
                    current_status=current_status,
                    verification_logs=log_items,
                ),
            )
        )

    return StructureFeatureCollection(features=features)


# -------------------------------------------------------------------------
# 7. GET /api/v1/wells & GET /api/v1/wells/{well_id}/readings
# -------------------------------------------------------------------------
@router.get("/wells", response_model=WellFeatureCollection)
def list_wells(db: Session = Depends(get_db)):
    """Returns monitoring wells with water level history as GeoJSON."""
    well_repo = WellRepository(db)
    wells = well_repo.get_all()
    features: list[WellFeature] = []

    for well in wells:
        readings = well.readings
        reading_items = [
            ReadingItem(
                date=r.reading_date.isoformat(),
                water_level_m=round(float(r.water_level_m), 2),
            )
            for r in readings
        ]
        latest = reading_items[-1] if reading_items else None

        features.append(
            WellFeature(
                geometry=geometry_to_geojson_dict(well.location),
                properties=WellProperties(
                    well_id=well.well_id,
                    station_code=well.cgwb_station_code,
                    source=well.source,
                    latest_water_level_m=latest.water_level_m if latest else None,
                    reading_date=latest.date if latest else None,
                    reading_history=reading_items,
                ),
            )
        )

    return WellFeatureCollection(features=features)


@router.get("/wells/{well_id}/readings", response_model=ApiResponse[list[ReadingItem]])
def get_well_readings(well_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get historical readings for a specific well."""
    well_repo = WellRepository(db)
    well = well_repo.get_by_id(well_id)
    if not well:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Well {well_id} not found",
        )

    readings = well_repo.get_readings(well_id)
    items = [
        ReadingItem(
            date=r.reading_date.isoformat(),
            water_level_m=round(float(r.water_level_m), 2),
        )
        for r in readings
    ]
    return ApiResponse(data=items, error=None)


# -------------------------------------------------------------------------
# 8. GET /api/v1/data-refresh/status
# -------------------------------------------------------------------------
@router.get("/data-refresh/status", response_model=ApiResponse[DataRefreshStatusResponse])
def get_data_refresh_status(db: Session = Depends(get_db)):
    """Get last successful ingestion timestamp per external data source."""
    repo = DataRefreshLogRepository(db)
    logs = repo.get_latest_per_source()

    items = [
        RefreshStatusItem(
            source_name=l.source_name,
            last_fetched_at=l.fetched_at,
            status=l.status,
            message=l.error_message,
        )
        for l in logs
    ]

    healthy = all(l.status == "success" for l in logs) if logs else True
    return ApiResponse(data=DataRefreshStatusResponse(sources=items, system_healthy=healthy), error=None)


# -------------------------------------------------------------------------
# 9. GET /api/v1/health & GET /api/v1/admin/models & refresh-logs
# -------------------------------------------------------------------------
@router.get("/health", response_model=ApiResponse[HealthResponse])
def get_health():
    """Service health check."""
    data = HealthResponse(
        status="online",
        service="NeerNiti Geospatial Decision Support Engine",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc),
    )
    return ApiResponse(data=data, error=None)


@router.get("/admin/models", response_model=list[ModelVersionItem])
def get_admin_models(db: Session = Depends(get_db)):
    """Returns registered ML models for admin inspection."""
    repo = ModelVersionRepository(db)
    models = repo.get_all()
    return [
        ModelVersionItem(
            model_version_id=m.model_version_id,
            module_name=m.module_name,
            algorithm=m.algorithm,
            trained_on=m.trained_on,
            hyperparameters=m.hyperparameters,
            evaluation_metrics=m.evaluation_metrics,
            training_data_snapshot=m.training_data_snapshot,
            created_at=m.created_at,
        )
        for m in models
    ]


@router.get("/admin/refresh-logs")
def get_admin_refresh_logs(db: Session = Depends(get_db)):
    """Returns recent sync audit logs."""
    repo = DataRefreshLogRepository(db)
    logs = repo.get_recent(50)
    return [
        {
            "log_id": str(log.log_id),
            "region_id": str(log.region_id) if log.region_id else None,
            "source_name": log.source_name,
            "fetched_at": log.fetched_at.isoformat() if log.fetched_at else None,
            "status": log.status,
            "error_message": log.error_message,
        }
        for log in logs
    ]
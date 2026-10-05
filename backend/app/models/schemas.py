"""
NeerNiti — Pydantic Request & Response Schemas
Provides strict type validation and standardized API response envelopes for all endpoints.
"""

import uuid
from datetime import date, datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# --- Standard Error & Envelope Models ---

class ApiError(BaseModel):
    message: str
    code: str
    details: dict[str, Any] | None = None


class ApiResponse(BaseModel, Generic[T]):
    data: T | None = None
    error: ApiError | None = None


# --- Region Schemas ---

class RegionProperties(BaseModel):
    region_id: uuid.UUID
    region_name: str
    region_type: str
    state: str


class RegionFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: dict[str, Any] | None = None
    properties: RegionProperties


class RegionFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[RegionFeature]


# --- Site & Recommendation Schemas ---

class SubScores(BaseModel):
    slope_score: float = Field(..., description="Slope terrain contribution")
    ndvi_score: float = Field(0.0, description="Vegetation index score")
    water_level_score: float = Field(0.0, description="Aquifer depth score")


class SiteRecommendRequest(BaseModel):
    region_id: uuid.UUID | None = None
    district_name: str | None = "Prayagraj"
    polygon_geojson: dict[str, Any] | None = None
    min_suitability_score: float = Field(0.0, ge=0.0, le=1.0)
    risk_filter: str | None = "All"
    top_n: int = Field(20, ge=1, le=100)


class SiteProperties(BaseModel):
    recommendation_id: uuid.UUID
    final_suitability_score: float
    structure_type: str
    risk_category: str
    explanation_text: str
    sub_scores: SubScores
    model_version_id: str | None = None
    created_at: str | None = None


class SiteFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: dict[str, Any] | None = None
    properties: SiteProperties


class SiteFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[SiteFeature]


class ExplanationDetail(BaseModel):
    site_id: uuid.UUID
    shap_values: dict[str, float]
    top_contributions: list[dict[str, Any]]
    plain_text_summary: str
    generated_at: datetime


class SiteDetailResponse(BaseModel):
    site_id: uuid.UUID
    region_id: uuid.UUID
    latitude: float
    longitude: float
    suitability_score: float
    risk_category: str
    model_version_id: str
    features: dict[str, Any] | None = None
    explanation: ExplanationDetail | None = None
    created_at: datetime


# --- Structure & Verification Schemas ---

class StructureCreateRequest(BaseModel):
    site_id: uuid.UUID
    structure_type: str = Field(..., json_schema_extra={"example": "Check Dam"})
    build_date: date = Field(default_factory=date.today)
    status: str = Field("active", json_schema_extra={"example": "active"})


class VerificationLogItem(BaseModel):
    date: str
    predicted_m: float
    actual_m: float
    deviation_pct: float
    status: str


class StructureProperties(BaseModel):
    structure_id: uuid.UUID
    site_id: uuid.UUID
    structure_type: str
    construction_date: str | None = None
    build_date: str | None = None
    current_status: str
    verification_logs: list[VerificationLogItem]


class StructureFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: dict[str, Any] | None = None
    properties: StructureProperties


class StructureFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[StructureFeature]


class StructureVerificationDetail(BaseModel):
    structure_id: uuid.UUID
    structure_type: str
    build_date: date
    status: str
    latest_status: str
    verification_logs: list[VerificationLogItem]


# --- Well & Telemetry Schemas ---

class ReadingItem(BaseModel):
    date: str
    water_level_m: float


class WellProperties(BaseModel):
    well_id: uuid.UUID
    station_code: str | None = None
    source: str
    latest_water_level_m: float | None = None
    reading_date: str | None = None
    reading_history: list[ReadingItem]


class WellFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: dict[str, Any] | None = None
    properties: WellProperties


class WellFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[WellFeature]


# --- Ingestion & Admin Schemas ---

class RefreshStatusItem(BaseModel):
    source_name: str
    last_fetched_at: datetime
    status: str
    message: str | None = None


class DataRefreshStatusResponse(BaseModel):
    sources: list[RefreshStatusItem]
    system_healthy: bool


class ModelVersionItem(BaseModel):
    model_version_id: str
    module_name: str
    algorithm: str
    trained_on: date
    hyperparameters: dict[str, Any]
    evaluation_metrics: dict[str, Any]
    training_data_snapshot: str
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime

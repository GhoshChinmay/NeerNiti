import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional

from geoalchemy2 import Geography, Geometry
from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Region(Base):
    __tablename__ = "regions"

    region_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region_name: Mapped[str] = mapped_column(String(100), nullable=False)
    region_type: Mapped[str] = mapped_column(String(20), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)

    # SRID 4326 Polygon boundary
    boundary_geom: Mapped[Any] = mapped_column(Geometry("POLYGON", srid=4326, spatial_index=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        CheckConstraint("region_type IN ('state', 'district', 'custom')", name="check_region_type"),
        Index("idx_regions_state", "state"),
    )


class ModelVersion(Base):
    __tablename__ = "model_versions"

    model_version_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    module_name: Mapped[str] = mapped_column(String(30), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(30), nullable=False)
    trained_on: Mapped[date] = mapped_column(Date, nullable=False)
    hyperparameters: Mapped[dict] = mapped_column(JSONB, nullable=False)
    evaluation_metrics: Mapped[dict] = mapped_column(JSONB, nullable=False)
    training_data_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "module_name IN ('site_recommendation', 'verification', 'risk_screening')",
            name="check_module_name",
        ),
    )


class Site(Base):
    __tablename__ = "sites"

    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regions.region_id"), nullable=False, index=True
    )
    location: Mapped[Any] = mapped_column(Geography("POINT", srid=4326, spatial_index=True), nullable=False)
    suitability_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_category: Mapped[str | None] = mapped_column(String(10), nullable=True)
    model_version_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("model_versions.model_version_id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    feature: Mapped[Optional["SiteFeature"]] = relationship("SiteFeature", back_populates="site", uselist=False, cascade="all, delete-orphan")
    explanation: Mapped[Optional["Explanation"]] = relationship("Explanation", back_populates="site", uselist=False, cascade="all, delete-orphan")
    structure: Mapped[Optional["Structure"]] = relationship("Structure", back_populates="site", uselist=False)

    __table_args__ = (
        CheckConstraint("suitability_score >= 0 AND suitability_score <= 1", name="check_suitability_score"),
        CheckConstraint("risk_category IN ('Low', 'Medium', 'High')", name="check_risk_category"),
        Index("idx_sites_score", suitability_score.desc()),
    )


class SiteFeature(Base):
    __tablename__ = "site_features"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.site_id", ondelete="CASCADE"), primary_key=True
    )
    slope_deg: Mapped[float] = mapped_column(Float, nullable=False)
    soil_type: Mapped[str] = mapped_column(String(50), nullable=False)
    land_use: Mapped[str] = mapped_column(String(50), nullable=False)
    rainfall_mm: Mapped[float] = mapped_column(Float, nullable=False)
    drainage_density: Mapped[float] = mapped_column(Float, nullable=False)
    geology_type: Mapped[str] = mapped_column(String(50), nullable=False)
    depth_to_groundwater_m: Mapped[float | None] = mapped_column(Float, nullable=True)

    site: Mapped["Site"] = relationship("Site", back_populates="feature")


class Explanation(Base):
    __tablename__ = "explanations"

    explanation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.site_id", ondelete="CASCADE"), nullable=False, unique=True
    )
    shap_values: Mapped[dict] = mapped_column(JSONB, nullable=False)
    plain_text_summary: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    site: Mapped["Site"] = relationship("Site", back_populates="explanation")


class Structure(Base):
    __tablename__ = "structures"

    structure_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.site_id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    structure_type: Mapped[str] = mapped_column(String(50), nullable=False)
    build_date: Mapped[date] = mapped_column("construction_date", Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    location: Mapped[Any | None] = mapped_column(Geography("POINT", srid=4326, spatial_index=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    site: Mapped["Site"] = relationship("Site", back_populates="structure")
    verification_logs: Mapped[list["VerificationLog"]] = relationship(
        "VerificationLog", back_populates="structure", cascade="all, delete-orphan", order_by="VerificationLog.check_date.asc()"
    )
    nearby_wells: Mapped[list["StructureWell"]] = relationship(
        "StructureWell", back_populates="structure", cascade="all, delete-orphan"
    )

    # Backward compatibility properties
    @property
    def construction_date(self) -> date:
        return self.build_date

    @construction_date.setter
    def construction_date(self, val: date) -> None:
        self.build_date = val

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'decommissioned', 'Active', 'Inactive', 'Under Construction')",
            name="check_structure_status",
        ),
    )


class StructureWell(Base):
    __tablename__ = "structure_wells"

    structure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("structures.structure_id", ondelete="CASCADE"), primary_key=True
    )
    well_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wells.well_id", ondelete="CASCADE"), primary_key=True
    )
    distance_m: Mapped[float] = mapped_column(Float, nullable=False)

    structure: Mapped["Structure"] = relationship("Structure", back_populates="nearby_wells")
    well: Mapped["Well"] = relationship("Well")

    __table_args__ = (
        Index("idx_structure_wells_structure", "structure_id"),
    )


class Well(Base):
    __tablename__ = "wells"

    well_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regions.region_id"), nullable=True, index=True
    )
    location: Mapped[Any] = mapped_column(Geography("POINT", srid=4326, spatial_index=True), nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    cgwb_station_code: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    readings: Mapped[list["WellReading"]] = relationship(
        "WellReading", back_populates="well", cascade="all, delete-orphan", order_by="WellReading.reading_date.asc()"
    )

    __table_args__ = (
        CheckConstraint("source IN ('CGWB', 'India-WRIS')", name="check_well_source"),
    )


class WellReading(Base):
    __tablename__ = "well_readings"

    reading_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    well_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wells.well_id", ondelete="CASCADE"), nullable=False, index=True
    )
    reading_date: Mapped[date] = mapped_column(Date, nullable=False)
    water_level_m: Mapped[float] = mapped_column(Float, nullable=False)
    source_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    well: Mapped["Well"] = relationship("Well", back_populates="readings")

    __table_args__ = (
        UniqueConstraint("well_id", "reading_date", name="uq_well_reading_date"),
        Index("idx_well_readings_well_date", "well_id", reading_date.desc()),
    )


class VerificationLog(Base):
    __tablename__ = "verification_logs"

    log_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    structure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("structures.structure_id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_version_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("model_versions.model_version_id"), nullable=False
    )
    check_date: Mapped[date] = mapped_column("evaluation_date", Date, nullable=False)
    predicted_level_m: Mapped[float] = mapped_column("predicted_water_level_m", Float, nullable=False)
    actual_level_m: Mapped[float] = mapped_column("actual_water_level_m", Float, nullable=False)
    deviation_pct: Mapped[float] = mapped_column("deviation_percentage", Float, nullable=False)
    status: Mapped[str] = mapped_column("performance_status", String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    structure: Mapped["Structure"] = relationship("Structure", back_populates="verification_logs")

    # Backward compatibility properties
    @property
    def evaluation_date(self) -> date:
        return self.check_date

    @property
    def predicted_water_level_m(self) -> float:
        return self.predicted_level_m

    @property
    def actual_water_level_m(self) -> float:
        return self.actual_level_m

    @property
    def deviation_percentage(self) -> float:
        return self.deviation_pct

    @property
    def performance_status(self) -> str:
        return self.status

    __table_args__ = (
        CheckConstraint(
            "performance_status IN ('OK', 'Underperforming', 'Critical')",
            name="check_performance_status",
        ),
        UniqueConstraint("structure_id", "evaluation_date", name="uq_structure_check_date"),
        Index("idx_verification_structure_date", "structure_id", "evaluation_date"),
    )


class DataRefreshLog(Base):
    __tablename__ = "data_refresh_log"

    log_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regions.region_id"), nullable=True
    )
    source_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('success', 'failure', 'partial')", name="check_refresh_status"),
        Index("idx_refresh_log_source_time", "source_name", fetched_at.desc()),
    )


class RechargeRecommendation(Base):
    """Legacy support table."""
    __tablename__ = "recharge_recommendations"

    recommendation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("regions.region_id"), nullable=False)
    location: Mapped[Any] = mapped_column(Geography("POINT", srid=4326), nullable=False)
    slope_score: Mapped[float] = mapped_column(Float, nullable=False)
    ndvi_score: Mapped[float] = mapped_column(Float, nullable=False)
    water_level_score: Mapped[float] = mapped_column(Float, nullable=False)
    final_suitability_score: Mapped[float] = mapped_column(Float, nullable=False)
    structure_type: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
"""
NeerNiti — Database Access Layer (Repository Pattern)
Isolates SQLAlchemy query logic from business logic in the ML and API layers.
"""

import uuid
from datetime import date, datetime, timezone
from typing import Any

from geoalchemy2.functions import ST_Distance, ST_DWithin
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.db.models import (
    DataRefreshLog,
    Explanation,
    ModelVersion,
    Region,
    Site,
    SiteFeature,
    Structure,
    StructureWell,
    VerificationLog,
    Well,
    WellReading,
)


class RegionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> list[Region]:
        return self.db.query(Region).all()

    def get_by_id(self, region_id: uuid.UUID) -> Region | None:
        return self.db.query(Region).filter_by(region_id=region_id).first()

    def get_by_name(self, name: str) -> Region | None:
        return self.db.query(Region).filter_by(region_name=name).first()


class SiteRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(
        self,
        region_id: uuid.UUID | None = None,
        min_score: float = 0.0,
        risk_category: str | None = None,
        exclude_built: bool = True,
        limit: int = 100,
    ) -> list[Site]:
        query = self.db.query(Site).filter(Site.suitability_score >= min_score)

        if region_id:
            query = query.filter(Site.region_id == region_id)

        if risk_category and risk_category != "All":
            query = query.filter(Site.risk_category == risk_category)

        if exclude_built:
            query = query.filter(~Site.site_id.in_(self.db.query(Structure.site_id)))

        return query.order_by(Site.suitability_score.desc()).limit(limit).all()

    def get_by_id(self, site_id: uuid.UUID) -> Site | None:
        return self.db.query(Site).filter_by(site_id=site_id).first()

    def get_feature(self, site_id: uuid.UUID) -> SiteFeature | None:
        return self.db.query(SiteFeature).filter_by(site_id=site_id).first()

    def get_explanation(self, site_id: uuid.UUID) -> Explanation | None:
        return self.db.query(Explanation).filter_by(site_id=site_id).first()

    def create(
        self,
        region_id: uuid.UUID,
        location: Any,
        suitability_score: float,
        risk_category: str,
        model_version_id: str,
    ) -> Site:
        site = Site(
            region_id=region_id,
            location=location,
            suitability_score=suitability_score,
            risk_category=risk_category,
            model_version_id=model_version_id,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(site)
        return site


class StructureRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, region_id: uuid.UUID | None = None) -> list[Structure]:
        query = self.db.query(Structure)
        if region_id:
            query = query.join(Site, Structure.site_id == Site.site_id).filter(Site.region_id == region_id)
        return query.order_by(Structure.created_at.desc()).all()

    def get_by_id(self, structure_id: uuid.UUID) -> Structure | None:
        return self.db.query(Structure).filter_by(structure_id=structure_id).first()

    def create_from_site(
        self,
        site_id: uuid.UUID,
        structure_type: str,
        build_date: date,
        status: str = "active",
    ) -> Structure:
        site = self.db.query(Site).filter_by(site_id=site_id).first()
        if not site:
            raise ValueError(f"Site {site_id} not found")

        structure = Structure(
            site_id=site_id,
            structure_type=structure_type,
            build_date=build_date,
            status=status,
            location=site.location,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(structure)
        self.db.flush()

        # Automatically link nearby monitoring wells within 3000m (per Design doc Section 3.3)
        wells_nearby = (
            self.db.query(Well, ST_Distance(Well.location, site.location).label("dist_m"))
            .filter(ST_DWithin(Well.location, site.location, 3000))
            .order_by("dist_m")
            .limit(3)
            .all()
        )

        for well, dist in wells_nearby:
            sw = StructureWell(
                structure_id=structure.structure_id,
                well_id=well.well_id,
                distance_m=float(dist),
            )
            self.db.add(sw)

        self.db.commit()
        return structure


class WellRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, region_id: uuid.UUID | None = None) -> list[Well]:
        query = self.db.query(Well)
        if region_id:
            query = query.filter(Well.region_id == region_id)
        return query.all()

    def get_by_id(self, well_id: uuid.UUID) -> Well | None:
        return self.db.query(Well).filter_by(well_id=well_id).first()

    def get_readings(self, well_id: uuid.UUID, limit: int = 100) -> list[WellReading]:
        return (
            self.db.query(WellReading)
            .filter_by(well_id=well_id)
            .order_by(WellReading.reading_date.asc())
            .limit(limit)
            .all()
        )


class VerificationLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_logs_for_structure(self, structure_id: uuid.UUID) -> list[VerificationLog]:
        return (
            self.db.query(VerificationLog)
            .filter_by(structure_id=structure_id)
            .order_by(VerificationLog.check_date.asc())
            .all()
        )

    def get_underperforming(self, region_id: uuid.UUID | None = None) -> list[VerificationLog]:
        query = (
            self.db.query(VerificationLog)
            .join(Structure, VerificationLog.structure_id == Structure.structure_id)
            .join(Site, Structure.site_id == Site.site_id)
            .filter(VerificationLog.status == "Underperforming")
        )
        if region_id:
            query = query.filter(Site.region_id == region_id)
        return query.order_by(VerificationLog.check_date.desc()).all()


class DataRefreshLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_latest_per_source(self) -> list[DataRefreshLog]:
        # Subquery for max fetched_at per source_name
        subq = (
            self.db.query(
                DataRefreshLog.source_name,
                func.max(DataRefreshLog.fetched_at).label("max_fetched"),
            )
            .group_by(DataRefreshLog.source_name)
            .subquery()
        )

        return (
            self.db.query(DataRefreshLog)
            .join(
                subq,
                and_(
                    DataRefreshLog.source_name == subq.c.source_name,
                    DataRefreshLog.fetched_at == subq.c.max_fetched,
                ),
            )
            .order_by(DataRefreshLog.fetched_at.desc())
            .all()
        )

    def get_recent(self, limit: int = 50) -> list[DataRefreshLog]:
        return self.db.query(DataRefreshLog).order_by(DataRefreshLog.fetched_at.desc()).limit(limit).all()


class ModelVersionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> list[ModelVersion]:
        return self.db.query(ModelVersion).order_by(ModelVersion.created_at.desc()).all()

    def get_latest_by_module(self, module_name: str) -> ModelVersion | None:
        return (
            self.db.query(ModelVersion)
            .filter_by(module_name=module_name)
            .order_by(ModelVersion.created_at.desc())
            .first()
        )

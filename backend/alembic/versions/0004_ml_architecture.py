"""ml_architecture

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-08 15:00:00.000000

"""
import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None

def upgrade():
    # --- BULLDOZER: Clean up any half-finished tables from previous failed runs ---
    op.execute("DROP TABLE IF EXISTS explanations CASCADE")
    op.execute("DROP TABLE IF EXISTS site_features CASCADE")
    op.execute("DROP TABLE IF EXISTS sites CASCADE")
    op.execute("DROP TABLE IF EXISTS model_versions CASCADE")
    # -------------------------------------------------------------------------------

    # 1. Model Versions
    op.create_table('model_versions',
        sa.Column('model_version_id', sa.String(50), primary_key=True),
        sa.Column('module_name', sa.String(30), nullable=False),
        sa.Column('algorithm', sa.String(30), nullable=False),
        sa.Column('trained_on', sa.Date(), nullable=False),
        sa.Column('hyperparameters', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('evaluation_metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('training_data_snapshot', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("module_name IN ('site_recommendation','verification','risk_screening')", name='check_module_name')
    )

    # 2. Sites (The official PRD equivalent of RechargeRecommendation)
    op.create_table('sites',
        sa.Column('site_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('region_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('regions.region_id'), nullable=False),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326), nullable=False),
        sa.Column('suitability_score', sa.Float(), nullable=False),
        sa.Column('risk_category', sa.String(10), nullable=True),
        sa.Column('model_version_id', sa.String(50), sa.ForeignKey('model_versions.model_version_id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('suitability_score >= 0 AND suitability_score <= 1', name='check_score_range'),
        sa.CheckConstraint("risk_category IN ('Low','Medium','High')", name='check_risk_category')
    )

    # 3. Site Features
    op.create_table('site_features',
        sa.Column('site_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sites.site_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('slope_deg', sa.Float(), nullable=False),
        sa.Column('soil_type', sa.String(50), nullable=False),
        sa.Column('land_use', sa.String(50), nullable=False),
        sa.Column('rainfall_mm', sa.Float(), nullable=False),
        sa.Column('drainage_density', sa.Float(), nullable=False),
        sa.Column('geology_type', sa.String(50), nullable=False),
        sa.Column('depth_to_groundwater_m', sa.Float(), nullable=True)
    )

    # 4. Explanations
    op.create_table('explanations',
        sa.Column('explanation_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('site_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sites.site_id', ondelete='CASCADE'), nullable=False),
        sa.Column('shap_values', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('plain_text_summary', sa.Text(), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('site_id', name='uq_explanation_site')
    )

def downgrade():
    op.drop_table('explanations')
    op.drop_table('site_features')
    op.drop_table('sites')
    op.drop_table('model_versions')
"""initial_schema

Revision ID: 0001
Revises: 
Create Date: 2026-08-07 00:00:00.000000

"""
import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 1. We MUST enable PostGIS in the database before creating spatial tables!
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis;')

    # 2. Create Regions
    op.create_table('regions',
        sa.Column('region_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('region_name', sa.String(100), nullable=False),
        sa.Column('region_type', sa.String(20), nullable=False),
        sa.Column('state', sa.String(100), nullable=False),
        sa.Column('boundary_geom', geoalchemy2.types.Geometry(geometry_type='POLYGON', srid=4326), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("region_type IN ('state', 'district', 'custom')", name='check_region_type')
    )

    # 3. Create Model Versions
    op.create_table('model_versions',
        sa.Column('model_version_id', sa.String(50), primary_key=True),
        sa.Column('module_name', sa.String(30), nullable=False),
        sa.Column('algorithm', sa.String(30), nullable=False),
        sa.Column('trained_on', sa.DateTime(), nullable=False),
        sa.Column('hyperparameters', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('evaluation_metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('training_data_snapshot', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("module_name IN ('site_recommendation', 'verification', 'risk_screening')", name='check_module_name')
    )

    # 4. Create Sites
    op.create_table('sites',
        sa.Column('site_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('region_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('regions.region_id'), nullable=False),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326), nullable=False),
        sa.Column('suitability_score', sa.Float(), nullable=False),
        sa.Column('risk_category', sa.String(10), nullable=True),
        sa.Column('model_version_id', sa.String(50), sa.ForeignKey('model_versions.model_version_id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('suitability_score >= 0 AND suitability_score <= 1', name='check_suitability_score'),
        sa.CheckConstraint("risk_category IN ('Low', 'Medium', 'High')", name='check_risk_category')
    )

def downgrade():
    op.drop_table('sites')
    op.drop_table('model_versions')
    op.drop_table('regions')
    op.execute('DROP EXTENSION IF EXISTS postgis;')
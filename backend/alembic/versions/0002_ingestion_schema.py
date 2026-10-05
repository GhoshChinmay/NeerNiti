"""ingestion_schema

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-07 01:00:00.000000

"""
import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = '0002'
down_revision = '0001'  # This tells Alembic that 0002 comes directly after 0001
branch_labels = None
depends_on = None

def upgrade():
    # 1. Create Wells Table
    op.create_table('wells',
        sa.Column('well_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('region_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('regions.region_id'), nullable=False),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326), nullable=False),
        sa.Column('source', sa.String(30), nullable=False),
        sa.Column('cgwb_station_code', sa.String(50), nullable=True, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("source IN ('CGWB', 'India-WRIS')", name='check_well_source')
    )

    # 2. Create Well Readings Table
    op.create_table('well_readings',
        sa.Column('reading_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('well_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('wells.well_id', ondelete='CASCADE'), nullable=False),
        sa.Column('reading_date', sa.Date(), nullable=False),
        sa.Column('water_level_m', sa.Float(), nullable=False),
        sa.Column('source_updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('well_id', 'reading_date', name='uq_well_reading_date')
    )

    # 3. Create Data Refresh Log Table
    op.create_table('data_refresh_log',
        sa.Column('log_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('region_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('regions.region_id'), nullable=True),
        sa.Column('source_name', sa.String(50), nullable=False),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('success', 'failure', 'partial')", name='check_refresh_status')
    )

def downgrade():
    op.drop_table('data_refresh_log')
    op.drop_table('well_readings')
    op.drop_table('wells')
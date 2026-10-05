"""ml_recommendations

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-08 12:30:00.000000

"""
import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('recharge_recommendations',
        sa.Column('recommendation_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('region_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('regions.region_id'), nullable=False),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326), nullable=False),
        sa.Column('slope_score', sa.Float(), nullable=False),
        sa.Column('ndvi_score', sa.Float(), nullable=False),
        sa.Column('water_level_score', sa.Float(), nullable=False),
        sa.Column('final_suitability_score', sa.Float(), nullable=False),
        sa.Column('structure_type', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )

def downgrade():
    op.drop_table('recharge_recommendations')
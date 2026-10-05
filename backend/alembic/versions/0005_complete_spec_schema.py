"""complete_spec_schema

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-16 02:20:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None

def upgrade():
    # Create structure_wells junction table if not exists
    op.create_table(
        'structure_wells',
        sa.Column('structure_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('structures.structure_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('well_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('wells.well_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('distance_m', sa.Float(), nullable=False),
    )
    op.create_index('idx_structure_wells_structure', 'structure_wells', ['structure_id'])

def downgrade():
    op.drop_index('idx_structure_wells_structure', table_name='structure_wells')
    op.drop_table('structure_wells')

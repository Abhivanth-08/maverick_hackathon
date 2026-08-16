"""sync trial schema with model

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("trials", sa.Column("official_title", sa.Text(), nullable=True))
    op.add_column("trials", sa.Column("healthy_volunteers", sa.Boolean(), nullable=True))
    op.add_column("trials", sa.Column("study_type", sa.String(length=50), nullable=True))
    op.add_column("trials", sa.Column("enrollment", sa.Integer(), nullable=True))
    op.add_column("trials", sa.Column("locations", sa.JSON(), nullable=True))
    op.add_column("trials", sa.Column("sponsor", sa.String(length=255), nullable=True))

def downgrade():
    op.drop_column("trials", "sponsor")
    op.drop_column("trials", "locations")
    op.drop_column("trials", "enrollment")
    op.drop_column("trials", "study_type")
    op.drop_column("trials", "healthy_volunteers")
    op.drop_column("trials", "official_title")

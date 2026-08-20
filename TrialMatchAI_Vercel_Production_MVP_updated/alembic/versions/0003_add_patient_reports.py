"""add patient_reports table

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "patient_reports",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False, index=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False, index=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=100), nullable=False),
        sa.Column("document_type", sa.String(length=100), nullable=True),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("processing_status", sa.String(length=50), nullable=False, default="UPLOADED", index=True),
        sa.Column("extraction_status", sa.String(length=50), nullable=False, default="PENDING", index=True),
        sa.Column("extracted_json", sa.JSON(), nullable=True),
        sa.Column("verified_json", sa.JSON(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("ocr_applied", sa.Boolean(), nullable=False, default=False),
        sa.Column("error_message", sa.Text(), nullable=True),
    )

def downgrade():
    op.drop_table("patient_reports")

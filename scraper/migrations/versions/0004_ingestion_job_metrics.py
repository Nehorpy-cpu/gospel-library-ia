"""add ingestion job metrics

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("ingestion_jobs"):
        return
    columns = {column["name"] for column in inspector.get_columns("ingestion_jobs")}
    if "source_id" not in columns:
        op.add_column("ingestion_jobs", sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key("fk_ingestion_jobs_source_id", "ingestion_jobs", "sources", ["source_id"], ["id"])
    if "source" not in columns:
        op.add_column("ingestion_jobs", sa.Column("source", sa.String(length=100), nullable=True))
    if "documents_found" not in columns:
        op.add_column(
            "ingestion_jobs",
            sa.Column("documents_found", sa.Integer(), nullable=False, server_default="0"),
        )
    if "documents_created" not in columns:
        op.add_column(
            "ingestion_jobs",
            sa.Column("documents_created", sa.Integer(), nullable=False, server_default="0"),
        )
    if "documents_updated" not in columns:
        op.add_column(
            "ingestion_jobs",
            sa.Column("documents_updated", sa.Integer(), nullable=False, server_default="0"),
        )
    if "errors" not in columns:
        op.add_column(
            "ingestion_jobs",
            sa.Column("errors", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        )
    op.execute("UPDATE ingestion_jobs SET errors = jsonb_build_array(error) WHERE error IS NOT NULL AND errors = '[]'::jsonb")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("ingestion_jobs"):
        return
    columns = {column["name"] for column in inspector.get_columns("ingestion_jobs")}
    for column_name in ["errors", "documents_updated", "documents_created", "documents_found", "source"]:
        if column_name in columns:
            op.drop_column("ingestion_jobs", column_name)
    if "source_id" in columns:
        op.drop_constraint("fk_ingestion_jobs_source_id", "ingestion_jobs", type_="foreignkey")
        op.drop_column("ingestion_jobs", "source_id")

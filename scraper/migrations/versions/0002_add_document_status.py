"""add document status

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("documents"):
        return
    columns = {column["name"] for column in inspector.get_columns("documents")}
    if "status" not in columns:
        op.add_column(
            "documents",
            sa.Column("status", sa.String(length=64), nullable=False, server_default="READY"),
        )
    op.execute("UPDATE documents SET status = 'READY' WHERE status IS NULL")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("documents"):
        columns = {column["name"] for column in inspector.get_columns("documents")}
        if "status" in columns:
            op.drop_column("documents", "status")

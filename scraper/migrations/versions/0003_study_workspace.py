"""add study workspace tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    if not inspector.has_table("study_workspaces"):
        op.create_table(
            "study_workspaces",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("source_filters", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("settings", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("idx_study_workspaces_user", "study_workspaces", ["user_id"])
        op.create_index("idx_study_workspaces_updated", "study_workspaces", ["updated_at"])

    if not inspector.has_table("study_workspace_sources"):
        op.create_table(
            "study_workspace_sources",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("study_workspaces.id", ondelete="CASCADE"), nullable=False),
            sa.Column("source_key", sa.String(length=100), nullable=True),
            sa.Column("language", sa.String(length=16), nullable=True),
            sa.Column("author", sa.Text(), nullable=True),
            sa.Column("category", sa.Text(), nullable=True),
            sa.Column("tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("idx_study_workspace_sources_workspace", "study_workspace_sources", ["workspace_id"])
        op.create_index("idx_study_workspace_sources_source", "study_workspace_sources", ["source_key"])

    if not inspector.has_table("study_notes"):
        op.create_table(
            "study_notes",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("study_workspaces.id", ondelete="CASCADE"), nullable=False),
            sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=True),
            sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("title", sa.Text(), nullable=True),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("color", sa.String(length=32), nullable=False, server_default="yellow"),
            sa.Column("position", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("idx_study_notes_workspace", "study_notes", ["workspace_id", "updated_at"])
        op.create_index("idx_study_notes_document", "study_notes", ["document_id"])

    if not inspector.has_table("saved_citations"):
        op.create_table(
            "saved_citations",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("study_workspaces.id", ondelete="CASCADE"), nullable=False),
            sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("quote", sa.Text(), nullable=False),
            sa.Column("citation_url", sa.Text(), nullable=True),
            sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("idx_saved_citations_workspace", "saved_citations", ["workspace_id", "created_at"])
        op.create_index("idx_saved_citations_document", "saved_citations", ["document_id"])

    if not inspector.has_table("post_its"):
        op.create_table(
            "post_its",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("study_workspaces.id", ondelete="CASCADE"), nullable=False),
            sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=True),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("color", sa.String(length=32), nullable=False, server_default="yellow"),
            sa.Column("position", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("idx_post_its_workspace", "post_its", ["workspace_id", "updated_at"])
        op.create_index("idx_post_its_document", "post_its", ["document_id"])


def downgrade() -> None:
    for table_name in [
        "post_its",
        "saved_citations",
        "study_notes",
        "study_workspace_sources",
        "study_workspaces",
    ]:
        op.drop_table(table_name)

"""extend study workspace tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _columns(inspector, table_name: str) -> set[str]:
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _indexes(inspector, table_name: str) -> set[str]:
    if not inspector.has_table(table_name):
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _add_column(table_name: str, existing: set[str], column: sa.Column) -> None:
    if column.name not in existing:
        op.add_column(table_name, column)


def _create_index(table_name: str, existing: set[str], name: str, columns: list[str]) -> None:
    if name not in existing:
        op.create_index(name, table_name, columns)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    if inspector.has_table("study_workspaces"):
        columns = _columns(inspector, "study_workspaces")
        _add_column("study_workspaces", columns, sa.Column("client_rev", sa.Integer(), nullable=False, server_default="1"))
        _add_column("study_workspaces", columns, sa.Column("server_rev", sa.Integer(), nullable=False, server_default="1"))
        _add_column("study_workspaces", columns, sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        indexes = _indexes(inspector, "study_workspaces")
        _create_index("study_workspaces", indexes, "idx_study_workspaces_user_updated", ["user_id", "updated_at"])
        _create_index("study_workspaces", indexes, "idx_study_workspaces_deleted", ["deleted_at"])

    if inspector.has_table("study_workspace_sources"):
        columns = _columns(inspector, "study_workspace_sources")
        _add_column("study_workspace_sources", columns, sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True))
        _add_column("study_workspace_sources", columns, sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
        _add_column("study_workspace_sources", columns, sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        op.execute(
            """
            UPDATE study_workspace_sources sws
            SET user_id = sw.user_id
            FROM study_workspaces sw
            WHERE sws.workspace_id = sw.id AND sws.user_id IS NULL
            """
        )
        indexes = _indexes(inspector, "study_workspace_sources")
        _create_index("study_workspace_sources", indexes, "idx_study_workspace_sources_workspace_updated", ["workspace_id", "updated_at"])
        _create_index("study_workspace_sources", indexes, "idx_study_workspace_sources_user_updated", ["user_id", "updated_at"])

    if inspector.has_table("study_notes"):
        columns = _columns(inspector, "study_notes")
        _add_column("study_notes", columns, sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True))
        _add_column("study_notes", columns, sa.Column("selected_text", sa.Text(), nullable=True))
        _add_column("study_notes", columns, sa.Column("selection_range", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))
        _add_column("study_notes", columns, sa.Column("scripture_refs", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))
        _add_column("study_notes", columns, sa.Column("client_rev", sa.Integer(), nullable=False, server_default="1"))
        _add_column("study_notes", columns, sa.Column("server_rev", sa.Integer(), nullable=False, server_default="1"))
        op.execute(
            """
            UPDATE study_notes sn
            SET user_id = sw.user_id
            FROM study_workspaces sw
            WHERE sn.workspace_id = sw.id AND sn.user_id IS NULL
            """
        )
        indexes = _indexes(inspector, "study_notes")
        _create_index("study_notes", indexes, "idx_study_notes_user_updated", ["user_id", "updated_at"])
        _create_index("study_notes", indexes, "idx_study_notes_chunk", ["chunk_id"])
        _create_index("study_notes", indexes, "idx_study_notes_deleted", ["deleted_at"])

    if not inspector.has_table("study_highlights"):
        op.create_table(
            "study_highlights",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("study_workspaces.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("note_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("study_notes.id", ondelete="SET NULL"), nullable=True),
            sa.Column("start_char", sa.Integer(), nullable=False),
            sa.Column("end_char", sa.Integer(), nullable=False),
            sa.Column("selected_text", sa.Text(), nullable=False),
            sa.Column("scripture_refs", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("color", sa.String(length=32), nullable=False, server_default="yellow"),
            sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("client_rev", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("server_rev", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("idx_study_highlights_workspace_updated", "study_highlights", ["workspace_id", "updated_at"])
        op.create_index("idx_study_highlights_user_updated", "study_highlights", ["user_id", "updated_at"])
        op.create_index("idx_study_highlights_document", "study_highlights", ["document_id"])
        op.create_index("idx_study_highlights_chunk", "study_highlights", ["chunk_id"])
        op.create_index("idx_study_highlights_note", "study_highlights", ["note_id"])
        op.create_index("idx_study_highlights_deleted", "study_highlights", ["deleted_at"])

    if inspector.has_table("saved_citations"):
        columns = _columns(inspector, "saved_citations")
        _add_column("saved_citations", columns, sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True))
        _add_column("saved_citations", columns, sa.Column("selected_text", sa.Text(), nullable=True))
        _add_column("saved_citations", columns, sa.Column("source_url", sa.Text(), nullable=True))
        _add_column("saved_citations", columns, sa.Column("source_title", sa.Text(), nullable=True))
        _add_column("saved_citations", columns, sa.Column("source_author", sa.Text(), nullable=True))
        _add_column("saved_citations", columns, sa.Column("location", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))
        _add_column("saved_citations", columns, sa.Column("scripture_refs", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))
        _add_column("saved_citations", columns, sa.Column("client_rev", sa.Integer(), nullable=False, server_default="1"))
        _add_column("saved_citations", columns, sa.Column("server_rev", sa.Integer(), nullable=False, server_default="1"))
        _add_column("saved_citations", columns, sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
        _add_column("saved_citations", columns, sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        op.execute(
            """
            UPDATE saved_citations sc
            SET user_id = sw.user_id
            FROM study_workspaces sw
            WHERE sc.workspace_id = sw.id AND sc.user_id IS NULL
            """
        )
        indexes = _indexes(inspector, "saved_citations")
        _create_index("saved_citations", indexes, "idx_saved_citations_workspace_updated", ["workspace_id", "updated_at"])
        _create_index("saved_citations", indexes, "idx_saved_citations_user_updated", ["user_id", "updated_at"])
        _create_index("saved_citations", indexes, "idx_saved_citations_chunk", ["chunk_id"])
        _create_index("saved_citations", indexes, "idx_saved_citations_deleted", ["deleted_at"])

    if inspector.has_table("post_its"):
        columns = _columns(inspector, "post_its")
        _add_column("post_its", columns, sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True))
        _add_column("post_its", columns, sa.Column("source_filters", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))
        _add_column("post_its", columns, sa.Column("client_rev", sa.Integer(), nullable=False, server_default="1"))
        _add_column("post_its", columns, sa.Column("server_rev", sa.Integer(), nullable=False, server_default="1"))
        op.execute(
            """
            UPDATE post_its pi
            SET user_id = sw.user_id
            FROM study_workspaces sw
            WHERE pi.workspace_id = sw.id AND pi.user_id IS NULL
            """
        )
        indexes = _indexes(inspector, "post_its")
        _create_index("post_its", indexes, "idx_post_its_user_updated", ["user_id", "updated_at"])
        _create_index("post_its", indexes, "idx_post_its_deleted", ["deleted_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table_name, columns in {
        "post_its": ["server_rev", "client_rev", "source_filters", "user_id"],
        "saved_citations": [
            "deleted_at",
            "updated_at",
            "server_rev",
            "client_rev",
            "scripture_refs",
            "location",
            "source_author",
            "source_title",
            "source_url",
            "selected_text",
            "user_id",
        ],
        "study_notes": ["server_rev", "client_rev", "scripture_refs", "selection_range", "selected_text", "user_id"],
        "study_workspace_sources": ["deleted_at", "updated_at", "user_id"],
        "study_workspaces": ["deleted_at", "server_rev", "client_rev"],
    }.items():
        existing = _columns(inspector, table_name)
        for column_name in columns:
            if column_name in existing:
                op.drop_column(table_name, column_name)
    if inspector.has_table("study_highlights"):
        op.drop_table("study_highlights")

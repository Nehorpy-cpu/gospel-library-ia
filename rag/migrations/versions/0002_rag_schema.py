"""rag schema

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    required_tables = {"document_chunks", "embeddings", "chat_sessions", "chat_messages"}
    if required_tables.issubset(existing_tables):
        return

    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunker_version", sa.String(length=64), nullable=False),
        sa.Column("language", sa.String(length=16)),
        sa.Column("title", sa.Text()),
        sa.Column("section_title", sa.Text()),
        sa.Column("start_char", sa.Integer(), nullable=False),
        sa.Column("end_char", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("search_vector", postgresql.TSVECTOR()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_id", "chunk_index", "chunker_version", name="uq_chunk_version"),
    )
    op.create_index("idx_chunks_document", "document_chunks", ["document_id"])
    op.create_index("idx_chunks_language", "document_chunks", ["language"])
    op.create_index("idx_chunks_metadata", "document_chunks", ["metadata"], postgresql_using="gin")
    op.create_index("idx_chunks_search_vector", "document_chunks", ["search_vector"], postgresql_using="gin")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_chunk_search_vector()
        RETURNS trigger AS $$
        BEGIN
          NEW.search_vector :=
            setweight(to_tsvector('simple', coalesce(NEW.title, '')), 'A') ||
            setweight(to_tsvector('simple', coalesce(NEW.section_title, '')), 'B') ||
            setweight(to_tsvector('simple', coalesce(NEW.text, '')), 'C');
          RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_update_chunk_search_vector
        BEFORE INSERT OR UPDATE ON document_chunks
        FOR EACH ROW EXECUTE FUNCTION update_chunk_search_vector();
        """
    )

    op.create_table(
        "embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_chunks.id"), nullable=False),
        sa.Column("qdrant_point_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("chunk_id", "model", "content_hash", name="uq_embedding_chunk_model_hash"),
    )
    op.create_index("idx_embeddings_model", "embeddings", ["model"])

    op.create_table(
        "chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("title", sa.Text()),
        sa.Column("language", sa.String(length=16)),
        sa.Column("mode", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_chat_sessions_user", "chat_sessions", ["user_id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_sessions.id"), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_chat_messages_session_created", "chat_messages", ["session_id", "created_at"])


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("embeddings")
    op.execute("DROP TRIGGER IF EXISTS trg_update_chunk_search_vector ON document_chunks")
    op.execute("DROP FUNCTION IF EXISTS update_chunk_search_vector")
    op.drop_table("document_chunks")

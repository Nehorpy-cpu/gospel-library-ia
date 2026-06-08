"""ai cost optimization

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _indexes(table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}


def upgrade() -> None:
    tables = _tables()

    if "embedding_cache" not in tables:
        op.create_table(
            "embedding_cache",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("content_hash", sa.String(length=64), nullable=False),
            sa.Column("model", sa.String(length=128), nullable=False),
            sa.Column("dimensions", sa.Integer(), nullable=False),
            sa.Column("vector", postgresql.JSONB()),
            sa.Column("vector_id", postgresql.UUID(as_uuid=True)),
            sa.Column("chunk_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_chunks.id")),
            sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("last_used_at", sa.DateTime(timezone=True)),
            sa.UniqueConstraint("content_hash", "model", name="uq_embedding_cache_hash_model"),
        )
        op.create_index("idx_embedding_cache_model", "embedding_cache", ["model"])
        op.create_index("idx_embedding_cache_chunk", "embedding_cache", ["chunk_id"])

    if "ai_usage_events" not in tables:
        op.create_table(
            "ai_usage_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("kind", sa.String(length=64), nullable=False),
            sa.Column("model", sa.String(length=128)),
            sa.Column("user_id", postgresql.UUID(as_uuid=True)),
            sa.Column("workspace_id", postgresql.UUID(as_uuid=True)),
            sa.Column("document_id", postgresql.UUID(as_uuid=True)),
            sa.Column("chunk_id", postgresql.UUID(as_uuid=True)),
            sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=64), nullable=False, server_default="ok"),
            sa.Column("error_code", sa.String(length=128)),
            sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("idx_ai_usage_created", "ai_usage_events", ["created_at"])
        op.create_index("idx_ai_usage_kind", "ai_usage_events", ["kind"])
        op.create_index("idx_ai_usage_user_created", "ai_usage_events", ["user_id", "created_at"])

    if "ai_runtime_state" not in tables:
        op.create_table(
            "ai_runtime_state",
            sa.Column("key", sa.String(length=120), primary_key=True),
            sa.Column("value", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )

    if "embeddings" in tables and "idx_embeddings_content_hash" not in _indexes("embeddings"):
        op.create_index("idx_embeddings_content_hash", "embeddings", ["content_hash"])
    if "document_chunks" in tables and "idx_chunks_text_hash" not in _indexes("document_chunks"):
        op.create_index("idx_chunks_text_hash", "document_chunks", ["text_hash"])


def downgrade() -> None:
    tables = _tables()
    if "document_chunks" in tables and "idx_chunks_text_hash" in _indexes("document_chunks"):
        op.drop_index("idx_chunks_text_hash", table_name="document_chunks")
    if "embeddings" in tables and "idx_embeddings_content_hash" in _indexes("embeddings"):
        op.drop_index("idx_embeddings_content_hash", table_name="embeddings")
    if "ai_runtime_state" in tables:
        op.drop_table("ai_runtime_state")
    if "ai_usage_events" in tables:
        op.drop_table("ai_usage_events")
    if "embedding_cache" in tables:
        op.drop_table("embedding_cache")

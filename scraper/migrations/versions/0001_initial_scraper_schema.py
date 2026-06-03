"""initial scraper schema

Revision ID: 0001
Revises:
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    required_tables = {"sources", "crawl_urls", "documents", "document_assets", "ingestion_jobs"}
    if required_tables.issubset(existing_tables):
        return

    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(length=80), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "crawl_urls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("normalized_url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("discovered_from", sa.Text()),
        sa.Column("http_status", sa.Integer()),
        sa.Column("content_type", sa.String(length=255)),
        sa.Column("content_hash", sa.String(length=64)),
        sa.Column("etag", sa.String(length=255)),
        sa.Column("last_modified", sa.String(length=255)),
        sa.Column("error", sa.Text()),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_crawled_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_id", "normalized_url", name="uq_crawl_url_source_normalized"),
    )
    op.create_index("idx_crawl_urls_status", "crawl_urls", ["status"])
    op.create_index("idx_crawl_urls_hash", "crawl_urls", ["content_hash"])

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("crawl_url_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("crawl_urls.id")),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("author", sa.Text()),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("language", sa.String(length=16)),
        sa.Column("category", sa.Text()),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("scripture_refs", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("text", sa.Text()),
        sa.Column("raw_metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="READY"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_indexed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("canonical_url", name="uq_documents_canonical_url"),
    )
    op.create_index("idx_documents_language", "documents", ["language"])
    op.create_index("idx_documents_source", "documents", ["source_id"])
    op.create_index("idx_documents_hash", "documents", ["content_hash"])

    op.create_table(
        "document_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("source_url", sa.Text()),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=255)),
        sa.Column("size_bytes", sa.Integer()),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_id", "asset_type", "source_url", name="uq_document_asset_source"),
    )
    op.create_index("idx_document_assets_hash", "document_assets", ["checksum"])

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_ingestion_jobs_status_type", "ingestion_jobs", ["status", "job_type"])


def downgrade() -> None:
    op.drop_table("ingestion_jobs")
    op.drop_table("document_assets")
    op.drop_table("documents")
    op.drop_table("crawl_urls")
    op.drop_table("sources")

"""massive source catalog

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def _columns(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _indexes(inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _add_column(table_name: str, columns: set[str], column) -> None:
    if column.name not in columns:
        op.add_column(table_name, column)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("sources"):
        columns = _columns(inspector, "sources")
        _add_column("sources", columns, sa.Column("source_type", sa.String(length=100), nullable=True))
        _add_column("sources", columns, sa.Column("language", sa.String(length=16), nullable=True))
        _add_column(
            "sources",
            columns,
            sa.Column("crawl_strategy", sa.String(length=80), nullable=False, server_default="html_discovery"),
        )
        _add_column("sources", columns, sa.Column("rate_limit", sa.Integer(), nullable=False, server_default="30"))
        _add_column("sources", columns, sa.Column("max_pages_per_run", sa.Integer(), nullable=False, server_default="25"))
        _add_column("sources", columns, sa.Column("last_crawled_at", sa.DateTime(timezone=True), nullable=True))
        _add_column("sources", columns, sa.Column("robots_policy_notes", sa.Text(), nullable=True))

        op.execute(
            """
            UPDATE sources
            SET source_type = COALESCE(source_type, config->>'sourceType', config->>'source_type', key),
                language = COALESCE(language, config->>'language'),
                crawl_strategy = COALESCE(config->>'crawlStrategy', config->>'crawl_strategy', crawl_strategy),
                rate_limit = COALESCE(NULLIF(config->>'rateLimit', '')::int, NULLIF(config->>'rate_limit', '')::int, rate_limit),
                max_pages_per_run = COALESCE(NULLIF(config->>'maxPagesPerRun', '')::int, NULLIF(config->>'max_pages_per_run', '')::int, max_pages_per_run),
                robots_policy_notes = COALESCE(robots_policy_notes, config->>'robotsPolicyNotes', config->>'robots_policy_notes')
            """
        )
        op.execute(
            """
            UPDATE sources
            SET
              name = 'BYU Speeches English',
              source_type = 'byu_speeches_en',
              language = COALESCE(language, 'en'),
              crawl_strategy = 'listing_and_talk_pages',
              rate_limit = 30,
              max_pages_per_run = LEAST(COALESCE(max_pages_per_run, 12), 25),
              robots_policy_notes = COALESCE(robots_policy_notes, 'Respetar robots.txt; crawl limitado a discursos publicos.')
            WHERE key = 'byu_speeches'
            """
        )
        indexes = _indexes(inspector, "sources")
        if "idx_sources_enabled_type" not in indexes:
            op.create_index("idx_sources_enabled_type", "sources", ["enabled", "source_type"])
        if "idx_sources_last_crawled" not in indexes:
            op.create_index("idx_sources_last_crawled", "sources", ["last_crawled_at"])

    if inspector.has_table("ingestion_jobs"):
        columns = _columns(inspector, "ingestion_jobs")
        _add_column(
            "ingestion_jobs",
            columns,
            sa.Column("documents_skipped", sa.Integer(), nullable=False, server_default="0"),
        )
        _add_column(
            "ingestion_jobs",
            columns,
            sa.Column("documents_failed", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("ingestion_jobs"):
        columns = _columns(inspector, "ingestion_jobs")
        for column_name in ["documents_failed", "documents_skipped"]:
            if column_name in columns:
                op.drop_column("ingestion_jobs", column_name)
    if inspector.has_table("sources"):
        indexes = _indexes(inspector, "sources")
        if "idx_sources_last_crawled" in indexes:
            op.drop_index("idx_sources_last_crawled", table_name="sources")
        if "idx_sources_enabled_type" in indexes:
            op.drop_index("idx_sources_enabled_type", table_name="sources")
        columns = _columns(inspector, "sources")
        for column_name in [
            "robots_policy_notes",
            "last_crawled_at",
            "max_pages_per_run",
            "rate_limit",
            "crawl_strategy",
            "language",
            "source_type",
        ]:
            if column_name in columns:
                op.drop_column("sources", column_name)

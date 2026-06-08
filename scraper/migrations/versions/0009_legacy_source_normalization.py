"""legacy source normalization

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-08
"""

import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


LEGACY_SOURCE_REPLACEMENTS = {
    "byu_speeches_en": ("byu_speeches", "byu_speeches_en"),
    "discursosud": ("discursos_sud", "discursos_sud"),
    "josephsmithpapers": ("joseph_smith_papers", "joseph_smith_papers"),
    "churchofjesuschrist": (None, "churchofjesuschrist"),
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("sources"):
        return

    if not inspector.has_table("source_legacy_cleanup_audit"):
        op.create_table(
            "source_legacy_cleanup_audit",
            sa.Column("source_id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("source_key", sa.String(length=100), nullable=False),
            sa.Column("previous_enabled", sa.Boolean(), nullable=False),
            sa.Column("previous_source_type", sa.String(length=100), nullable=True),
            sa.Column(
                "previous_config",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("replacement_key", sa.String(length=100), nullable=True),
            sa.Column("migrated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )

    for source_key, (replacement_key, canonical_type) in LEGACY_SOURCE_REPLACEMENTS.items():
        bind.execute(
            sa.text(
                """
                INSERT INTO source_legacy_cleanup_audit (
                  source_id, source_key, previous_enabled, previous_source_type,
                  previous_config, replacement_key
                )
                SELECT id, key, enabled, source_type, config, CAST(:replacement_key AS varchar)
                FROM sources
                WHERE key = :source_key
                ON CONFLICT (source_id) DO NOTHING
                """
            ),
            {"source_key": source_key, "replacement_key": replacement_key},
        )
        bind.execute(
            sa.text(
                """
                UPDATE sources
                SET enabled = false,
                    source_type = CAST(:canonical_type AS varchar),
                    config = config || CAST(:legacy_config AS jsonb),
                    updated_at = now()
                WHERE key = :source_key
                """
            ),
            {
                "source_key": source_key,
                "replacement_key": replacement_key,
                "canonical_type": canonical_type,
                "legacy_config": json.dumps(
                    {
                        "legacy": True,
                        "legacyDisabledReason": "duplicate_or_unbounded_source_catalog",
                        "replacementSourceKey": replacement_key,
                    }
                ),
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("source_legacy_cleanup_audit"):
        return

    if inspector.has_table("sources"):
        op.execute(
            """
            UPDATE sources AS source
            SET enabled = audit.previous_enabled,
                source_type = audit.previous_source_type,
                config = audit.previous_config,
                updated_at = now()
            FROM source_legacy_cleanup_audit AS audit
            WHERE source.id = audit.source_id
            """
        )
    op.drop_table("source_legacy_cleanup_audit")

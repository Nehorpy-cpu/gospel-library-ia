"""duplicate detection and reversible resolution

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("document_duplicate_relations"):
        return
    op.create_table(
        "document_duplicate_relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "canonical_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "duplicate_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("classification", sa.String(length=40), nullable=False),
        sa.Column("detection_rule", sa.String(length=80), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("review_status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "canonical_document_id <> duplicate_document_id",
            name="ck_document_duplicate_distinct",
        ),
        sa.CheckConstraint(
            "classification IN ('exact_duplicate', 'probable_duplicate', 'translation', "
            "'revised_edition', 'related_media', 'not_duplicate')",
            name="ck_document_duplicate_classification",
        ),
        sa.CheckConstraint(
            "review_status IN ('confirmed', 'pending', 'rejected')",
            name="ck_document_duplicate_review_status",
        ),
        sa.UniqueConstraint(
            "duplicate_document_id",
            name="uq_document_duplicate_relation_duplicate",
        ),
    )
    op.create_index(
        "idx_document_duplicate_canonical",
        "document_duplicate_relations",
        ["canonical_document_id"],
    )
    op.create_index(
        "idx_document_duplicate_classification_status",
        "document_duplicate_relations",
        ["classification", "review_status"],
    )


def downgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("document_duplicate_relations"):
        return
    op.drop_index(
        "idx_document_duplicate_classification_status",
        table_name="document_duplicate_relations",
    )
    op.drop_index(
        "idx_document_duplicate_canonical",
        table_name="document_duplicate_relations",
    )
    op.drop_table("document_duplicate_relations")

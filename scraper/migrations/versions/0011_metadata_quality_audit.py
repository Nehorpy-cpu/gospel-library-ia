"""metadata quality repair audit

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("document_metadata_repair_audit"):
        return
    op.create_table(
        "document_metadata_repair_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(length=40), nullable=False),
        sa.Column("previous_value", sa.Text(), nullable=True),
        sa.Column("repaired_value", sa.Text(), nullable=False),
        sa.Column("repaired_from", sa.String(length=80), nullable=False),
        sa.Column("repaired_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("reverted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("document_id", "field_name", name="uq_document_metadata_repair_field"),
    )
    op.create_index(
        "idx_document_metadata_repair_audit_document",
        "document_metadata_repair_audit",
        ["document_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("document_metadata_repair_audit"):
        return
    bind.execute(
        sa.text(
            """
            UPDATE documents AS document
            SET title = audit.previous_value,
                is_indexed = false,
                updated_at = now()
            FROM document_metadata_repair_audit AS audit
            WHERE audit.document_id = document.id
              AND audit.field_name = 'title'
              AND audit.reverted_at IS NULL
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE documents AS document
            SET author = audit.previous_value,
                is_indexed = false,
                updated_at = now()
            FROM document_metadata_repair_audit AS audit
            WHERE audit.document_id = document.id
              AND audit.field_name = 'author'
              AND audit.reverted_at IS NULL
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE documents AS document
            SET published_at = audit.previous_value::timestamptz,
                is_indexed = false,
                updated_at = now()
            FROM document_metadata_repair_audit AS audit
            WHERE audit.document_id = document.id
              AND audit.field_name = 'published_at'
              AND audit.reverted_at IS NULL
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE documents
            SET raw_metadata = COALESCE(raw_metadata, '{}'::jsonb) - 'metadata_quality_v1'
            WHERE id IN (
              SELECT DISTINCT document_id
              FROM document_metadata_repair_audit
              WHERE reverted_at IS NULL
            )
            """
        )
    )
    op.drop_index(
        "idx_document_metadata_repair_audit_document",
        table_name="document_metadata_repair_audit",
    )
    op.drop_table("document_metadata_repair_audit")

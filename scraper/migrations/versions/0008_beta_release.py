"""beta release controls

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def _indexes(inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("beta_access"):
        op.create_table(
            "beta_access",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("name", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("study_profile", sa.String(length=160), nullable=True),
            sa.Column("preferred_language", sa.String(length=16), nullable=True),
            sa.Column("preferred_sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
            sa.Column("request_message", sa.Text(), nullable=True),
            sa.Column("admin_notes", sa.Text(), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.UniqueConstraint("email", name="uq_beta_access_email"),
        )
    if not inspector.has_table("beta_feedback"):
        op.create_table(
            "beta_feedback",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("email", sa.String(length=320), nullable=True),
            sa.Column("page", sa.Text(), nullable=False),
            sa.Column("type", sa.String(length=80), nullable=False, server_default="other"),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("screenshot_url", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="new"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
    if not inspector.has_table("beta_activity_events"):
        op.create_table(
            "beta_activity_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("kind", sa.String(length=80), nullable=False),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )

    for table_name, index_name, columns in [
        ("beta_access", "idx_beta_access_status", ["status"]),
        ("beta_access", "idx_beta_access_user", ["user_id"]),
        ("beta_feedback", "idx_beta_feedback_status", ["status"]),
        ("beta_feedback", "idx_beta_feedback_type", ["type"]),
        ("beta_feedback", "idx_beta_feedback_created", ["created_at"]),
        ("beta_activity_events", "idx_beta_activity_user_created", ["user_id", "created_at"]),
        ("beta_activity_events", "idx_beta_activity_kind_created", ["kind", "created_at"]),
    ]:
        if inspector.has_table(table_name) and index_name not in _indexes(inspector, table_name):
            op.create_index(index_name, table_name, columns)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table_name in ["beta_activity_events", "beta_feedback", "beta_access"]:
        if inspector.has_table(table_name):
            op.drop_table(table_name)

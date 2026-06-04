"""add user preferences

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("user_preferences"):
        op.create_table(
            "user_preferences",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("calling_category", sa.String(length=120), nullable=True),
            sa.Column("calling_name", sa.String(length=200), nullable=True),
            sa.Column("custom_calling_name", sa.String(length=200), nullable=True),
            sa.Column("calling_focus_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("settings", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("user_preferences")}
    if "idx_user_preferences_calling" not in indexes:
        op.create_index("idx_user_preferences_calling", "user_preferences", ["calling_category", "calling_name"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("user_preferences"):
        op.drop_table("user_preferences")

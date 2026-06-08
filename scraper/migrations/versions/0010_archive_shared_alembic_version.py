"""archive the obsolete shared Alembic version table

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-08
"""

from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

SHARED_VERSION_TABLE = "alembic_version"
ARCHIVED_VERSION_TABLE = "legacy_alembic_version"


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names(schema="public"))


def upgrade() -> None:
    tables = _tables()
    if SHARED_VERSION_TABLE in tables and ARCHIVED_VERSION_TABLE not in tables:
        op.rename_table(
            SHARED_VERSION_TABLE,
            ARCHIVED_VERSION_TABLE,
            schema="public",
        )


def downgrade() -> None:
    tables = _tables()
    if ARCHIVED_VERSION_TABLE in tables and SHARED_VERSION_TABLE not in tables:
        op.rename_table(
            ARCHIVED_VERSION_TABLE,
            SHARED_VERSION_TABLE,
            schema="public",
        )

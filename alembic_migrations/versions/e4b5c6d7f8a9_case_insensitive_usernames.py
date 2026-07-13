"""make usernames case insensitive

Revision ID: e4b5c6d7f8a9
Revises: d9a8a4e7b12c
Create Date: 2026-07-13 00:00:00.000000
"""

from alembic import op


revision = "e4b5c6d7f8a9"
down_revision = "d9a8a4e7b12c"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE UNIQUE INDEX uq_users_username_lower ON users (lower(username))")


def downgrade():
    op.execute("DROP INDEX uq_users_username_lower")

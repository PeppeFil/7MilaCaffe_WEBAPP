"""add product image url

Revision ID: d9a8a4e7b12c
Revises: bc63dc5f5f98
Create Date: 2026-07-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d9a8a4e7b12c"
down_revision = "bc63dc5f5f98"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("products", sa.Column("immagine_url", sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column("products", "immagine_url")

"""add customer city and preferred compatibility

Revision ID: e1f2a3b4c5d6
Revises: c9e0f1a2b3d4
Create Date: 2026-07-20 19:00:00.000000

"""
import sqlalchemy as sa
from alembic import op


revision = "e1f2a3b4c5d6"
down_revision = "c9e0f1a2b3d4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("customers", sa.Column("citta", sa.String(length=100), nullable=True))
    op.add_column(
        "customers",
        sa.Column("compatibilita_preferita_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_customers_citta", "customers", ["citta"], unique=False)
    op.create_index(
        "ix_customers_compatibilita_preferita_id",
        "customers",
        ["compatibilita_preferita_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_customers_compatibilita_preferita_id_compatibilities",
        "customers",
        "compatibilities",
        ["compatibilita_preferita_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint(
        "fk_customers_compatibilita_preferita_id_compatibilities",
        "customers",
        type_="foreignkey",
    )
    op.drop_index("ix_customers_compatibilita_preferita_id", table_name="customers")
    op.drop_index("ix_customers_citta", table_name="customers")
    op.drop_column("customers", "compatibilita_preferita_id")
    op.drop_column("customers", "citta")

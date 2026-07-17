"""link single products to their source packages

Revision ID: c9e0f1a2b3d4
Revises: b8d9e0f1a2c3
Create Date: 2026-07-17 20:30:00.000000

"""
import re

import sqlalchemy as sa
from alembic import op


revision = "c9e0f1a2b3d4"
down_revision = "b8d9e0f1a2c3"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "products",
        "prezzo_acquisto",
        existing_type=sa.Numeric(10, 2),
        type_=sa.Numeric(14, 6),
        existing_nullable=False,
    )
    op.alter_column(
        "inventory_movements",
        "costo_unitario",
        existing_type=sa.Numeric(10, 2),
        type_=sa.Numeric(14, 6),
        existing_nullable=True,
    )
    op.alter_column(
        "sale_items",
        "costo_unitario_snapshot",
        existing_type=sa.Numeric(10, 2),
        type_=sa.Numeric(14, 6),
        existing_nullable=False,
    )
    op.add_column(
        "products",
        sa.Column("confezione_origine_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("unita_per_confezione", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_products_confezione_origine_id_products",
        "products",
        "products",
        ["confezione_origine_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_products_confezione_origine_id",
        "products",
        ["confezione_origine_id"],
        unique=True,
    )

    bind = op.get_bind()
    products = bind.execute(
        sa.text(
            "SELECT id, sku_barcode, formato_confezione FROM products "
            "ORDER BY id"
        )
    ).mappings().all()
    by_sku = {
        str(row["sku_barcode"]).strip().lower(): row
        for row in products
        if row["sku_barcode"]
    }
    by_id = {row["id"]: row for row in products}

    for single in products:
        sku = str(single["sku_barcode"] or "").strip()
        source = None
        if sku.upper().startswith("SINGOLA-"):
            raw_id = sku.split("-", 1)[1]
            if raw_id.isdigit():
                source = by_id.get(int(raw_id))
        elif sku.upper().endswith("-SINGOLA"):
            source = by_sku.get(sku[:-8].lower())

        if not source:
            continue
        match = re.search(r"(\d+)", source["formato_confezione"] or "")
        if not match or int(match.group(1)) <= 0:
            continue
        bind.execute(
            sa.text(
                "UPDATE products "
                "SET confezione_origine_id = :source_id, "
                "unita_per_confezione = :units "
                "WHERE id = :single_id"
            ),
            {
                "source_id": source["id"],
                "units": int(match.group(1)),
                "single_id": single["id"],
            },
        )

    op.create_check_constraint(
        "ck_products_single_package_link",
        "products",
        "(confezione_origine_id IS NULL AND unita_per_confezione IS NULL) OR "
        "(confezione_origine_id IS NOT NULL AND unita_per_confezione > 0)",
    )


def downgrade():
    op.drop_constraint(
        "ck_products_single_package_link", "products", type_="check"
    )
    op.drop_index("ix_products_confezione_origine_id", table_name="products")
    op.drop_constraint(
        "fk_products_confezione_origine_id_products",
        "products",
        type_="foreignkey",
    )
    op.drop_column("products", "unita_per_confezione")
    op.drop_column("products", "confezione_origine_id")
    op.alter_column(
        "sale_items",
        "costo_unitario_snapshot",
        existing_type=sa.Numeric(14, 6),
        type_=sa.Numeric(10, 2),
        existing_nullable=False,
    )
    op.alter_column(
        "inventory_movements",
        "costo_unitario",
        existing_type=sa.Numeric(14, 6),
        type_=sa.Numeric(10, 2),
        existing_nullable=True,
    )
    op.alter_column(
        "products",
        "prezzo_acquisto",
        existing_type=sa.Numeric(14, 6),
        type_=sa.Numeric(10, 2),
        existing_nullable=False,
    )

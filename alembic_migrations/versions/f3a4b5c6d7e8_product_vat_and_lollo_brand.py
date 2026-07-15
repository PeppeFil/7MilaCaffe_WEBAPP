"""add product VAT and merge Passione Mito into Lollo

Revision ID: f3a4b5c6d7e8
Revises: d2141921ec4f
Create Date: 2026-07-15 21:00:00.000000

"""
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from alembic import op
import sqlalchemy as sa


revision = "f3a4b5c6d7e8"
down_revision = "d2141921ec4f"
branch_labels = None
depends_on = None

MONEY = Decimal("0.01")


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(MONEY, rounding=ROUND_HALF_UP)


def upgrade():
    with op.batch_alter_table("products") as batch_op:
        batch_op.add_column(sa.Column("vat_rate_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_products_vat_rate", "vat_rates", ["vat_rate_id"], ["id"]
        )
        batch_op.create_index("ix_products_vat_rate_id", ["vat_rate_id"])

    with op.batch_alter_table("sale_items") as batch_op:
        batch_op.add_column(
            sa.Column("totale_netto", sa.Numeric(10, 2), nullable=True, server_default="0")
        )
        batch_op.add_column(
            sa.Column(
                "aliquota_iva_snapshot", sa.Numeric(5, 2), nullable=True, server_default="0"
            )
        )
        batch_op.add_column(
            sa.Column("totale_iva", sa.Numeric(10, 2), nullable=True, server_default="0")
        )

    bind = op.get_bind()
    for required_rate in (10, 22):
        exists = bind.execute(
            sa.text("select id from vat_rates where aliquota = :rate limit 1"),
            {"rate": required_rate},
        ).scalar()
        if exists is None:
            bind.execute(
                sa.text(
                    "insert into vat_rates "
                    "(nome, aliquota, descrizione, attiva, predefinita, data_creazione, data_aggiornamento) "
                    "values (:name, :rate, :description, true, :default_rate, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {
                    "name": f"IVA {required_rate}%",
                    "rate": required_rate,
                    "description": f"Aliquota IVA {required_rate}%",
                    "default_rate": required_rate == 22,
                },
            )

    rates = {
        int(Decimal(str(row.aliquota))): row.id
        for row in bind.execute(
            sa.text(
                "select id, aliquota from vat_rates "
                "where attiva = true and aliquota in (10, 22)"
            )
        )
    }
    if 10 not in rates or 22 not in rates:
        raise RuntimeError("Impossibile configurare le aliquote IVA 10% e 22%.")

    target_brand_id = bind.execute(
        sa.text(
            "select id from brands where lower(nome) = 'lollo' "
            "order by id limit 1"
        )
    ).scalar()
    if target_brand_id is None:
        legacy_lollo_id = bind.execute(
            sa.text(
                "select id from brands where lower(nome) = 'caffe lollo' "
                "order by id limit 1"
            )
        ).scalar()
        if legacy_lollo_id is not None:
            bind.execute(
                sa.text("update brands set nome = 'Lollo' where id = :id"),
                {"id": legacy_lollo_id},
            )
            target_brand_id = legacy_lollo_id
        else:
            bind.execute(
                sa.text(
                    "insert into brands (nome, data_creazione, data_aggiornamento) "
                    "values ('Lollo', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
            target_brand_id = bind.execute(
                sa.text("select id from brands where lower(nome) = 'lollo' order by id limit 1")
            ).scalar_one()

    wrong_brand_ids = [
        row.id
        for row in bind.execute(
            sa.text("select id from brands where lower(nome) = 'passione mito'")
        )
    ]
    for wrong_brand_id in wrong_brand_ids:
        bind.execute(
            sa.text("update products set marca_id = :target where marca_id = :wrong"),
            {"target": target_brand_id, "wrong": wrong_brand_id},
        )
        bind.execute(sa.text("delete from brands where id = :id"), {"id": wrong_brand_id})

    products = bind.execute(
        sa.text(
            "select p.id, c.nome as categoria "
            "from products p join categories c on c.id = p.categoria_id"
        )
    ).mappings()
    for product in products:
        rate = 10 if "solubil" in product["categoria"].lower() else 22
        bind.execute(
            sa.text("update products set vat_rate_id = :rate_id where id = :id"),
            {"rate_id": rates[rate], "id": product["id"]},
        )

    rows_by_sale = defaultdict(list)
    item_rows = bind.execute(
        sa.text(
            "select si.id, si.vendita_id, si.subtotale, s.totale_lordo, s.totale_netto, "
            "vr.id as vat_rate_id, vr.aliquota "
            "from sale_items si "
            "join sales s on s.id = si.vendita_id "
            "join products p on p.id = si.prodotto_id "
            "join vat_rates vr on vr.id = p.vat_rate_id "
            "order by si.vendita_id, si.id"
        )
    ).mappings()
    for row in item_rows:
        rows_by_sale[row["vendita_id"]].append(row)

    for sale_id, rows in rows_by_sale.items():
        total_gross = _money(rows[0]["totale_lordo"])
        sale_net = _money(rows[0]["totale_netto"])
        remaining = sale_net
        sale_vat = Decimal("0.00")
        rate_ids = set()
        rates_used = set()

        for index, row in enumerate(rows):
            if index == len(rows) - 1:
                line_net = remaining
            elif total_gross:
                line_net = (_money(row["subtotale"]) * sale_net / total_gross).quantize(
                    MONEY, rounding=ROUND_HALF_UP
                )
                remaining -= line_net
            else:
                line_net = Decimal("0.00")
            rate = Decimal(str(row["aliquota"]))
            line_vat = (line_net * rate / (Decimal("100") + rate)).quantize(
                MONEY, rounding=ROUND_HALF_UP
            )
            bind.execute(
                sa.text(
                    "update sale_items set totale_netto = :net, "
                    "aliquota_iva_snapshot = :rate, totale_iva = :vat where id = :id"
                ),
                {"net": line_net, "rate": rate, "vat": line_vat, "id": row["id"]},
            )
            sale_vat += line_vat
            rate_ids.add(row["vat_rate_id"])
            rates_used.add(rate)

        common_rate_id = next(iter(rate_ids)) if len(rate_ids) == 1 else None
        common_rate = next(iter(rates_used)) if len(rates_used) == 1 else Decimal("0.00")
        bind.execute(
            sa.text(
                "update sales set vat_rate_id = :rate_id, aliquota_iva_snapshot = :rate, "
                "totale_iva = :vat where id = :id"
            ),
            {
                "rate_id": common_rate_id,
                "rate": common_rate,
                "vat": sale_vat.quantize(MONEY),
                "id": sale_id,
            },
        )

    with op.batch_alter_table("products") as batch_op:
        batch_op.alter_column("vat_rate_id", existing_type=sa.Integer(), nullable=False)
    with op.batch_alter_table("sale_items") as batch_op:
        batch_op.alter_column(
            "totale_netto", existing_type=sa.Numeric(10, 2), nullable=False, server_default=None
        )
        batch_op.alter_column(
            "aliquota_iva_snapshot",
            existing_type=sa.Numeric(5, 2),
            nullable=False,
            server_default=None,
        )
        batch_op.alter_column(
            "totale_iva", existing_type=sa.Numeric(10, 2), nullable=False, server_default=None
        )


def downgrade():
    with op.batch_alter_table("sale_items") as batch_op:
        batch_op.drop_column("totale_iva")
        batch_op.drop_column("aliquota_iva_snapshot")
        batch_op.drop_column("totale_netto")
    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_index("ix_products_vat_rate_id")
        batch_op.drop_constraint("fk_products_vat_rate", type_="foreignkey")
        batch_op.drop_column("vat_rate_id")

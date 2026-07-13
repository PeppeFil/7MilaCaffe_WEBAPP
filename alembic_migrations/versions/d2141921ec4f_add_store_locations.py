"""add store locations

Revision ID: d2141921ec4f
Revises: e4b5c6d7f8a9
Create Date: 2026-07-13 22:35:33.684609

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd2141921ec4f'
down_revision = 'e4b5c6d7f8a9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "store_locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("codice", sa.String(length=40), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("indirizzo", sa.String(length=255), nullable=False),
        sa.Column("cap", sa.String(length=10), nullable=False),
        sa.Column("comune", sa.String(length=100), nullable=False),
        sa.Column("provincia", sa.String(length=10), nullable=False),
        sa.Column("ragione_sociale", sa.String(length=160), nullable=False),
        sa.Column("partita_iva", sa.String(length=20), nullable=False),
        sa.Column("attivo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("data_creazione", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("data_aggiornamento", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("codice"),
        sa.UniqueConstraint("partita_iva"),
    )
    op.create_index("ix_store_locations_codice", "store_locations", ["codice"], unique=True)
    op.create_index("ix_store_locations_attivo", "store_locations", ["attivo"])

    op.create_table(
        "store_inventory",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("punto_vendita_id", sa.Integer(), nullable=False),
        sa.Column("prodotto_id", sa.Integer(), nullable=False),
        sa.Column("quantita_disponibile", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quantita_minima_alert", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("data_creazione", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("data_aggiornamento", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["punto_vendita_id"], ["store_locations.id"]),
        sa.ForeignKeyConstraint(["prodotto_id"], ["products.id"]),
        sa.UniqueConstraint("punto_vendita_id", "prodotto_id", name="uq_store_inventory_store_product"),
    )
    op.create_index("ix_store_inventory_punto_vendita_id", "store_inventory", ["punto_vendita_id"])
    op.create_index("ix_store_inventory_prodotto_id", "store_inventory", ["prodotto_id"])
    op.create_index("ix_store_inventory_store_stock", "store_inventory", ["punto_vendita_id", "quantita_disponibile"])

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("punto_vendita_predefinito_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_users_default_store", "store_locations", ["punto_vendita_predefinito_id"], ["id"]
        )
        batch_op.create_index("ix_users_punto_vendita_predefinito_id", ["punto_vendita_predefinito_id"])
    with op.batch_alter_table("sales") as batch_op:
        batch_op.add_column(sa.Column("punto_vendita_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_sales_store", "store_locations", ["punto_vendita_id"], ["id"])
        batch_op.create_index("ix_sales_punto_vendita_id", ["punto_vendita_id"])
    with op.batch_alter_table("inventory_movements") as batch_op:
        batch_op.add_column(sa.Column("punto_vendita_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_inventory_movements_store", "store_locations", ["punto_vendita_id"], ["id"]
        )
        batch_op.create_index("ix_inventory_movements_punto_vendita_id", ["punto_vendita_id"])

    bind = op.get_bind()
    stores = sa.table(
        "store_locations",
        sa.column("codice", sa.String),
        sa.column("nome", sa.String),
        sa.column("indirizzo", sa.String),
        sa.column("cap", sa.String),
        sa.column("comune", sa.String),
        sa.column("provincia", sa.String),
        sa.column("ragione_sociale", sa.String),
        sa.column("partita_iva", sa.String),
        sa.column("attivo", sa.Boolean),
    )
    seed = [
        {
            "codice": "via-pepoli",
            "nome": "Via Conte Agostino Pepoli",
            "indirizzo": "Via Conte Agostino Pepoli 198",
            "cap": "91100",
            "comune": "Trapani",
            "provincia": "TP",
            "ragione_sociale": "7mila caffè di Fileti Rossella",
            "partita_iva": "02587220811",
            "attivo": True,
        },
        {
            "codice": "via-vespri",
            "nome": "Via Vespri",
            "indirizzo": "Via Vespri 235",
            "cap": "91019",
            "comune": "Valderice",
            "provincia": "TP",
            "ragione_sociale": "7mila caffè SRL",
            "partita_iva": "02719720811",
            "attivo": True,
        },
    ]
    for row in seed:
        exists = bind.execute(
            sa.text("select 1 from store_locations where codice = :codice"), {"codice": row["codice"]}
        ).first()
        if not exists:
            bind.execute(stores.insert().values(**row))

    pepoli_id = bind.execute(
        sa.text("select id from store_locations where codice = 'via-pepoli'")
    ).scalar_one()
    vespri_id = bind.execute(
        sa.text("select id from store_locations where codice = 'via-vespri'")
    ).scalar_one()
    bind.execute(
        sa.text("update users set punto_vendita_predefinito_id = :id where punto_vendita_predefinito_id is null"),
        {"id": pepoli_id},
    )
    bind.execute(
        sa.text("update users set punto_vendita_predefinito_id = :id where lower(username) = 'rossella'"),
        {"id": pepoli_id},
    )
    bind.execute(
        sa.text("update users set punto_vendita_predefinito_id = :id where lower(username) = 'annamaria'"),
        {"id": vespri_id},
    )
    bind.execute(sa.text("update sales set punto_vendita_id = :id where punto_vendita_id is null"), {"id": pepoli_id})
    bind.execute(
        sa.text("update inventory_movements set punto_vendita_id = :id where punto_vendita_id is null"),
        {"id": pepoli_id},
    )
    bind.execute(
        sa.text(
            "insert into store_inventory (punto_vendita_id, prodotto_id, quantita_disponibile, quantita_minima_alert) "
            "select :store_id, id, quantita_disponibile, quantita_minima_alert from products"
        ),
        {"store_id": pepoli_id},
    )


def downgrade():
    with op.batch_alter_table("inventory_movements") as batch_op:
        batch_op.drop_index("ix_inventory_movements_punto_vendita_id")
        batch_op.drop_constraint("fk_inventory_movements_store", type_="foreignkey")
        batch_op.drop_column("punto_vendita_id")
    with op.batch_alter_table("sales") as batch_op:
        batch_op.drop_index("ix_sales_punto_vendita_id")
        batch_op.drop_constraint("fk_sales_store", type_="foreignkey")
        batch_op.drop_column("punto_vendita_id")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_punto_vendita_predefinito_id")
        batch_op.drop_constraint("fk_users_default_store", type_="foreignkey")
        batch_op.drop_column("punto_vendita_predefinito_id")
    op.drop_index("ix_store_inventory_store_stock", table_name="store_inventory")
    op.drop_index("ix_store_inventory_prodotto_id", table_name="store_inventory")
    op.drop_index("ix_store_inventory_punto_vendita_id", table_name="store_inventory")
    op.drop_table("store_inventory")
    op.drop_index("ix_store_locations_attivo", table_name="store_locations")
    op.drop_index("ix_store_locations_codice", table_name="store_locations")
    op.drop_table("store_locations")

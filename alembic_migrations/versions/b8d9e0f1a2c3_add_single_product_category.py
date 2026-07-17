"""normalize the single product category

Revision ID: b8d9e0f1a2c3
Revises: a7c8d9e0f1b2
Create Date: 2026-07-17 18:30:00.000000

"""
from alembic import op


revision = "b8d9e0f1a2c3"
down_revision = "a7c8d9e0f1b2"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        UPDATE categories
        SET nome = 'Singole',
            descrizione = 'Unita singole ricavate dalle confezioni di capsule e cialde.'
        WHERE lower(nome) = 'singole'
        """
    )
    op.execute(
        """
        INSERT INTO categories (nome, descrizione, data_creazione, data_aggiornamento)
        SELECT
            'Singole',
            'Unita singole ricavate dalle confezioni di capsule e cialde.',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        WHERE NOT EXISTS (
            SELECT 1 FROM categories WHERE lower(nome) = 'singole'
        )
        """
    )


def downgrade():
    # Conserviamo la categoria se contiene gia prodotti o vendite collegate.
    op.execute(
        """
        DELETE FROM categories
        WHERE nome = 'Singole'
          AND NOT EXISTS (
              SELECT 1 FROM products WHERE products.categoria_id = categories.id
          )
        """
    )

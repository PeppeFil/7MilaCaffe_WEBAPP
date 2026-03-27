import pytest

from app.models import InventoryMovement, Product, Sale, User
from app.services.sale_service import annulla_vendita, crea_vendita


def test_sale_decrements_and_cancel_restores_stock(app):
    with app.app_context():
        operatore = User.query.filter_by(username="operatore").first()
        prodotto = Product.query.filter_by(sku_barcode="TEST-001").first()
        qty_start = prodotto.quantita_disponibile

        vendita = crea_vendita(
            operatore_id=operatore.id,
            items=[{"prodotto_id": prodotto.id, "quantita": 3}],
            sconto_tipo="nessuno",
            sconto_valore=0,
            metodo_pagamento="contanti",
            note_cliente="test",
        )

        prodotto_after_sale = Product.query.get(prodotto.id)
        assert prodotto_after_sale.quantita_disponibile == qty_start - 3
        assert Sale.query.get(vendita.id).stato == "completata"
        assert (
            InventoryMovement.query.filter_by(
                tipo_movimento="scarico_vendita",
                riferimento_entita=f"vendita:{vendita.id}",
            ).count()
            >= 1
        )

        annulla_vendita(vendita_id=vendita.id, operatore_id=operatore.id, motivo="test annullo")
        prodotto_after_cancel = Product.query.get(prodotto.id)
        assert prodotto_after_cancel.quantita_disponibile == qty_start
        assert Sale.query.get(vendita.id).stato == "annullata"
        assert (
            InventoryMovement.query.filter_by(
                tipo_movimento="ripristino_annullo_vendita",
                riferimento_entita=f"vendita:{vendita.id}",
            ).count()
            >= 1
        )


def test_sale_cannot_exceed_available_stock(app):
    with app.app_context():
        operatore = User.query.filter_by(username="operatore").first()
        prodotto = Product.query.filter_by(sku_barcode="TEST-001").first()
        with pytest.raises(ValueError):
            crea_vendita(
                operatore_id=operatore.id,
                items=[{"prodotto_id": prodotto.id, "quantita": prodotto.quantita_disponibile + 100}],
                sconto_tipo="nessuno",
                sconto_valore=0,
                metodo_pagamento="carta",
            )

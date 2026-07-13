import pytest

from app.extensions import db
from app.models import InventoryMovement, Product, Sale, StoreInventory, StoreLocation, User
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


def test_store_inventory_is_separate(app):
    with app.app_context():
        operatore = User.query.filter_by(username="operatore").first()
        prodotto = Product.query.filter_by(sku_barcode="TEST-001").first()
        pepoli = StoreLocation(
            codice="test-pepoli",
            nome="Pepoli",
            indirizzo="Via Pepoli 1",
            cap="91100",
            comune="Trapani",
            provincia="TP",
            ragione_sociale="Test Pepoli",
            partita_iva="00000000001",
        )
        vespri = StoreLocation(
            codice="test-vespri",
            nome="Vespri",
            indirizzo="Via Vespri 1",
            cap="91019",
            comune="Valderice",
            provincia="TP",
            ragione_sociale="Test Vespri",
            partita_iva="00000000002",
        )
        db.session.add_all([pepoli, vespri])
        db.session.flush()
        db.session.add_all([
            StoreInventory(punto_vendita_id=pepoli.id, prodotto_id=prodotto.id, quantita_disponibile=10),
            StoreInventory(punto_vendita_id=vespri.id, prodotto_id=prodotto.id, quantita_disponibile=4),
        ])
        db.session.commit()

        vendita = crea_vendita(
            operatore_id=operatore.id,
            punto_vendita_id=pepoli.id,
            items=[{"prodotto_id": prodotto.id, "quantita": 3}],
            sconto_tipo="nessuno",
            sconto_valore=0,
            metodo_pagamento="contanti",
        )

        assert vendita.punto_vendita_id == pepoli.id
        assert StoreInventory.query.filter_by(punto_vendita_id=pepoli.id, prodotto_id=prodotto.id).one().quantita_disponibile == 7
        assert StoreInventory.query.filter_by(punto_vendita_id=vespri.id, prodotto_id=prodotto.id).one().quantita_disponibile == 4

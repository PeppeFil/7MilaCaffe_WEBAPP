import pytest

from app.extensions import db
from app.models import Category, InventoryMovement, Product, Sale, StoreInventory, StoreLocation, User, VatRate
from app.services.sale_service import annulla_vendita, crea_vendita
from app.services.catalog_service import sync_varianti_singole
from app.services.inventory_service import crea_movimento_manuale


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


def test_single_sales_open_packages_only_when_needed(app):
    with app.app_context():
        operatore = User.query.filter_by(username="operatore").first()
        sorgente = Product.query.filter_by(sku_barcode="TEST-001").one()
        sync_varianti_singole()
        singola = Product.query.filter_by(sku_barcode="TEST-001-SINGOLA").one()

        prima = crea_vendita(
            operatore_id=operatore.id,
            items=[{"prodotto_id": singola.id, "quantita": 1}],
            sconto_tipo="nessuno",
            sconto_valore=0,
            metodo_pagamento="contanti",
        )
        assert sorgente.quantita_disponibile == 19
        assert singola.quantita_disponibile == 9
        assert InventoryMovement.query.filter_by(
            tipo_movimento="apertura_confezione",
            riferimento_entita=f"vendita:{prima.id}",
        ).one().quantita == -1
        assert InventoryMovement.query.filter_by(
            tipo_movimento="carico_da_confezione",
            riferimento_entita=f"vendita:{prima.id}",
        ).one().quantita == 10

        crea_vendita(
            operatore_id=operatore.id,
            items=[{"prodotto_id": singola.id, "quantita": 9}],
            sconto_tipo="nessuno",
            sconto_valore=0,
            metodo_pagamento="contanti",
        )
        assert sorgente.quantita_disponibile == 19
        assert singola.quantita_disponibile == 0

        terza = crea_vendita(
            operatore_id=operatore.id,
            items=[{"prodotto_id": singola.id, "quantita": 1}],
            sconto_tipo="nessuno",
            sconto_valore=0,
            metodo_pagamento="contanti",
        )
        assert sorgente.quantita_disponibile == 18
        assert singola.quantita_disponibile == 9

        annulla_vendita(terza.id, operatore.id)
        assert sorgente.quantita_disponibile == 18
        assert singola.quantita_disponibile == 10


def test_single_stock_cannot_be_manually_moved(app):
    with app.app_context():
        admin = User.query.filter_by(username="admin").one()
        sync_varianti_singole()
        singola = Product.query.filter_by(sku_barcode="TEST-001-SINGOLA").one()

        with pytest.raises(ValueError, match="gestita automaticamente"):
            crea_movimento_manuale(
                prodotto_id=singola.id,
                tipo_movimento="carico",
                quantita=10,
                operatore_id=admin.id,
            )


def test_single_package_opening_is_store_specific(app):
    with app.app_context():
        operatore = User.query.filter_by(username="operatore").one()
        sorgente = Product.query.filter_by(sku_barcode="TEST-001").one()
        pepoli = StoreLocation(
            codice="single-pepoli",
            nome="Pepoli singole",
            indirizzo="Via Pepoli 1",
            cap="91100",
            comune="Trapani",
            provincia="TP",
            ragione_sociale="Test Pepoli",
            partita_iva="00000000011",
        )
        vespri = StoreLocation(
            codice="single-vespri",
            nome="Vespri singole",
            indirizzo="Via Vespri 1",
            cap="91019",
            comune="Valderice",
            provincia="TP",
            ragione_sociale="Test Vespri",
            partita_iva="00000000012",
        )
        db.session.add_all([pepoli, vespri])
        db.session.flush()
        db.session.add_all(
            [
                StoreInventory(
                    punto_vendita_id=pepoli.id,
                    prodotto_id=sorgente.id,
                    quantita_disponibile=2,
                    quantita_minima_alert=0,
                ),
                StoreInventory(
                    punto_vendita_id=vespri.id,
                    prodotto_id=sorgente.id,
                    quantita_disponibile=3,
                    quantita_minima_alert=0,
                ),
            ]
        )
        db.session.commit()
        sync_varianti_singole()
        singola = Product.query.filter_by(sku_barcode="TEST-001-SINGOLA").one()

        crea_vendita(
            operatore_id=operatore.id,
            punto_vendita_id=pepoli.id,
            items=[{"prodotto_id": singola.id, "quantita": 4}],
            sconto_tipo="nessuno",
            sconto_valore=0,
            metodo_pagamento="contanti",
        )

        pepoli_pack = StoreInventory.query.filter_by(
            punto_vendita_id=pepoli.id, prodotto_id=sorgente.id
        ).one()
        pepoli_single = StoreInventory.query.filter_by(
            punto_vendita_id=pepoli.id, prodotto_id=singola.id
        ).one()
        vespri_pack = StoreInventory.query.filter_by(
            punto_vendita_id=vespri.id, prodotto_id=sorgente.id
        ).one()
        vespri_single = StoreInventory.query.filter_by(
            punto_vendita_id=vespri.id, prodotto_id=singola.id
        ).one()
        assert (pepoli_pack.quantita_disponibile, pepoli_single.quantita_disponibile) == (1, 6)
        assert (vespri_pack.quantita_disponibile, vespri_single.quantita_disponibile) == (3, 0)


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


def test_sale_calculates_vat_per_product_from_vat_included_prices(app):
    with app.app_context():
        operatore = User.query.filter_by(username="operatore").first()
        prodotto_22 = Product.query.filter_by(sku_barcode="TEST-001").first()
        prodotto_22.prezzo_vendita = 122
        iva_10 = VatRate(nome="IVA 10%", aliquota=10, attiva=True)
        categoria_solubili = Category(nome="Solubili")
        db.session.add_all([iva_10, categoria_solubili])
        db.session.flush()
        prodotto_10 = Product(
            nome="Solubile Test",
            categoria_id=categoria_solubili.id,
            marca_id=prodotto_22.marca_id,
            vat_rate_id=iva_10.id,
            prezzo_acquisto=50,
            prezzo_vendita=110,
            quantita_disponibile=5,
            quantita_minima_alert=1,
            sku_barcode="TEST-IVA-10",
            attivo=True,
        )
        db.session.add(prodotto_10)
        db.session.commit()

        vendita = crea_vendita(
            operatore_id=operatore.id,
            items=[
                {"prodotto_id": prodotto_22.id, "quantita": 1},
                {"prodotto_id": prodotto_10.id, "quantita": 1},
            ],
            sconto_tipo="nessuno",
            sconto_valore=0,
            metodo_pagamento="contanti",
        )

        assert vendita.totale_netto == 232
        assert vendita.totale_iva == 32
        assert vendita.vat_rate_id is None
        assert vendita.aliquota_iva_snapshot == 0
        righe = {r.prodotto_id: r for r in vendita.righe}
        assert righe[prodotto_22.id].aliquota_iva_snapshot == 22
        assert righe[prodotto_22.id].totale_iva == 22
        assert righe[prodotto_10.id].aliquota_iva_snapshot == 10
        assert righe[prodotto_10.id].totale_iva == 10

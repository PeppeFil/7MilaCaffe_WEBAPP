import json
from decimal import Decimal

import pytest

from app.extensions import db
from app.models import ActivityLog, InventoryMovement, Product, StoreInventory, StoreLocation, User
from app.services.promotion_service import BORBONE_55_SKU
from app.services.sale_service import annulla_vendita, crea_vendita
from tests.helpers import get_csrf_token, login


@pytest.fixture
def promo(app):
    with app.app_context():
        base = Product.query.filter_by(sku_barcode="TEST-001").one()
        base.sku_barcode = "8034028330636"
        for index, code in enumerate(["via-pepoli", "via-vespri"], 1):
            db.session.add(StoreLocation(
                codice=code, nome=code, indirizzo=f"Via Test {index}",
                cap="91100", comune="Trapani", provincia="TP",
                ragione_sociale=code, partita_iva=f"0000000000{index}",
            ))
        db.session.commit()
    result = app.test_cli_runner().invoke(args=["carica-promo-borbone-55"])
    assert result.exit_code == 0, result.output
    with app.app_context():
        product = Product.query.filter_by(sku_barcode=BORBONE_55_SKU).one()
        store = StoreLocation.query.filter_by(codice="via-pepoli").one()
        user = User.query.filter_by(username="operatore").one()
        user.punto_vendita_predefinito_id = store.id
        db.session.commit()
        return product.id, store.id, user.id


@pytest.mark.parametrize("quantity,total", [(1,11),(2,18),(3,29),(4,34),(5,45),(6,52),(7,63),(8,68)])
def test_promo_price_vat_margin_and_store_stock(app, promo, quantity, total):
    product_id, store_id, user_id = promo
    with app.app_context():
        sale = crea_vendita(
            operatore_id=user_id, punto_vendita_id=store_id,
            items=[{"prodotto_id":product_id,"quantita":quantity}],
            sconto_tipo="nessuno", sconto_valore=0, metodo_pagamento="contanti",
        )
        assert sale.totale_netto == total
        assert sale.totale_iva == (Decimal(total)*22/122).quantize(Decimal(".01"))
        assert sale.margine_stimato == Decimal(total)-Decimal("7.16")*quantity
        assert sale.righe[0].prezzo_unitario == 11
        assert sale.righe[0].subtotale == total
        assert StoreInventory.query.filter_by(punto_vendita_id=store_id,prodotto_id=product_id).one().quantita_disponibile == 400-quantity
        other = StoreLocation.query.filter_by(codice="via-vespri").one()
        assert StoreInventory.query.filter_by(punto_vendita_id=other.id,prodotto_id=product_id).one().quantita_disponibile == 140
        annulla_vendita(sale.id,user_id)
        assert StoreInventory.query.filter_by(punto_vendita_id=store_id,prodotto_id=product_id).one().quantita_disponibile == 400


def test_duplicate_cart_lines_use_combined_promo_and_manual_discount(app, promo):
    product_id, store_id, user_id = promo
    with app.app_context():
        base = Product.query.filter_by(sku_barcode="8034028330636").one()
        db.session.add(StoreInventory(punto_vendita_id=store_id,prodotto_id=base.id,quantita_disponibile=5))
        db.session.commit()
        sale = crea_vendita(
            operatore_id=user_id,punto_vendita_id=store_id,
            items=[{"prodotto_id":product_id,"quantita":2},{"prodotto_id":base.id,"quantita":1},{"prodotto_id":product_id,"quantita":2}],
            sconto_tipo="percentuale",sconto_valore=10,metodo_pagamento="carta",
        )
        assert len(sale.righe) == 2
        assert sale.totale_lordo == Decimal("34.40")
        assert sale.totale_netto == Decimal("30.96")
        assert sum(r.totale_netto for r in sale.righe) == sale.totale_netto
        assert sale.margine_stimato == Decimal("2.12")


def test_initial_stock_import_is_idempotent_after_sale(app, promo):
    product_id, store_id, user_id = promo
    with app.app_context():
        crea_vendita(operatore_id=user_id,punto_vendita_id=store_id,items=[{"prodotto_id":product_id,"quantita":2}],sconto_tipo="nessuno",sconto_valore=0,metodo_pagamento="contanti")
    result = app.test_cli_runner().invoke(args=["carica-promo-borbone-55"])
    assert result.exit_code == 0, result.output
    assert "gia caricata" in result.output
    with app.app_context():
        assert Product.query.filter_by(sku_barcode=BORBONE_55_SKU).count() == 1
        assert StoreInventory.query.filter_by(punto_vendita_id=store_id,prodotto_id=product_id).one().quantita_disponibile == 398
        assert ActivityLog.query.filter_by(azione="carico_promo_borbone_55").count() == 1
        assert InventoryMovement.query.filter_by(riferimento_entita="promo-borbone-55:2026-11-25").count() == 2


def test_checkout_recalculates_promo_and_receipt_shows_saving(app, client, promo):
    product_id, store_id, user_id = promo
    login(client,"operatore","operator123")
    products = client.get("/cassa/search?q=PROMO").get_json()
    assert len(products) == 1
    assert products[0]["promozione"]["prezzi"][0] == {"quantita":4,"totale":34}
    assert products[0]["quantita_disponibile"] == 400
    assert client.get(products[0]["immagine_url"]).status_code == 200
    response = client.post("/cassa/checkout", data={
        "csrf_token":get_csrf_token(client,"/cassa"),
        "cart_payload":json.dumps({"items":[{"prodotto_id":product_id,"quantita":4,"prezzo_unitario":0,"promozione":None}],"totale":0}),
    })
    assert response.status_code == 302
    with app.app_context():
        from app.models import Sale
        sale = Sale.query.filter_by(operatore_id=user_id).one()
        assert sale.totale_netto == 34
        sale_id = sale.id
    receipt = client.get(f"/cassa/ricevuta/{sale_id}")
    assert b"Promo automatica: -EUR 10.00" in receipt.data
    assert b"34.00" in receipt.data
    detail = client.get(f"/vendite/{sale_id}")
    assert b"Promo automatica: -EUR 10.00" in detail.data


def test_promo_rejects_overselling_without_partial_sale(app,promo):
    product_id,store_id,user_id=promo
    with app.app_context():
        from app.models import Sale
        with pytest.raises(ValueError,match="Stock insufficiente"):
            crea_vendita(operatore_id=user_id,punto_vendita_id=store_id,items=[{"prodotto_id":product_id,"quantita":401}],sconto_tipo="nessuno",sconto_valore=0,metodo_pagamento="contanti")
        assert Sale.query.count() == 0
        assert StoreInventory.query.filter_by(punto_vendita_id=store_id,prodotto_id=product_id).one().quantita_disponibile == 400

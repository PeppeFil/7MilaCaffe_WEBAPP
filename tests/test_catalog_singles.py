from decimal import Decimal

from app.extensions import db
from app.models import Brand, Category, Product
from app.services.catalog_service import _sku_singola, sync_varianti_singole


def test_sync_varianti_singole_calculates_unit_prices_and_is_idempotent(app):
    with app.app_context():
        sorgente = Product.query.filter_by(sku_barcode="TEST-001").one()
        sorgente.immagine_url = "/static/img/products/test.webp"
        db.session.commit()

        create, updated, skipped = sync_varianti_singole()

        assert (create, updated, skipped) == (1, 0, 0)
        singola = Product.query.filter_by(sku_barcode="TEST-001-SINGOLA").one()
        assert singola.nome == "Capsule Test - Singola"
        assert singola.categoria.nome == "Singole"
        assert singola.formato_confezione == "1 capsula"
        assert singola.prezzo_acquisto == Decimal("0.02")
        assert singola.prezzo_vendita == Decimal("0.04")
        assert singola.immagine_url == sorgente.immagine_url
        assert singola.quantita_disponibile == 0

        create, updated, skipped = sync_varianti_singole()

        assert (create, updated, skipped) == (0, 1, 0)
        assert Product.query.filter_by(sku_barcode="TEST-001-SINGOLA").count() == 1


def test_cash_order_prioritizes_borbone_then_lollo(app):
    from app.controllers.cash_register_controller import _ordinamento_prodotti_cassa

    with app.app_context():
        sorgente = Product.query.filter_by(sku_barcode="TEST-001").one()
        marche = [Brand(nome="Zeta"), Brand(nome="Lollo"), Brand(nome="Caffe Borbone")]
        db.session.add_all(marche)
        db.session.flush()
        for index, marca in enumerate(marche):
            db.session.add(
                Product(
                    nome=f"Prodotto {marca.nome}",
                    categoria_id=sorgente.categoria_id,
                    marca_id=marca.id,
                    vat_rate_id=sorgente.vat_rate_id,
                    prezzo_acquisto=1,
                    prezzo_vendita=2,
                    sku_barcode=f"ORDER-{index}",
                    attivo=True,
                )
            )
        db.session.commit()

        prodotti = (
            Product.query.join(Product.brand)
            .filter(Product.sku_barcode.like("ORDER-%"))
            .order_by(*_ordinamento_prodotti_cassa())
            .all()
        )

        assert [prodotto.brand.nome for prodotto in prodotti] == [
            "Caffe Borbone",
            "Lollo",
            "Zeta",
        ]


def test_single_sku_treats_text_none_as_missing(app):
    with app.app_context():
        prodotto = Product.query.filter_by(sku_barcode="TEST-001").one()
        prodotto.sku_barcode = "None"
        assert _sku_singola(prodotto) == f"SINGOLA-{prodotto.id}"

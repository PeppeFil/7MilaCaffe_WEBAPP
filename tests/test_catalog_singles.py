from decimal import Decimal

from app.extensions import db
from app.models import (
    Brand,
    Category,
    InventoryMovement,
    Product,
    StoreInventory,
    StoreLocation,
    VatRate,
)
from app.services.catalog_service import (
    CATALOGO_REALE,
    IMMAGINI_PRODOTTI,
    ULTIMO_IMPORT_BORBONE_SKU,
    _sku_singola,
    sync_catalogo_reale,
    sync_varianti_singole,
)
from app.cli import (
    FATTURE_BORBONE_SETTEMBRE_2026,
    GIACENZE_20_LUGLIO,
    ORDINI_BORBONE_LUGLIO_2026,
)
from app.services.store_service import quantita_fisica


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
        assert singola.confezione_origine_id == sorgente.id
        assert singola.unita_per_confezione == 10

        create, updated, skipped = sync_varianti_singole()

        assert (create, updated, skipped) == (0, 1, 0)
        assert Product.query.filter_by(sku_barcode="TEST-001-SINGOLA").count() == 1

        original_single_id = singola.id
        sorgente.sku_barcode = "TEST-RENAMED"
        db.session.commit()
        create, updated, skipped = sync_varianti_singole()
        assert (create, updated, skipped) == (0, 1, 0)
        renamed = Product.query.filter_by(sku_barcode="TEST-RENAMED-SINGOLA").one()
        assert renamed.id == original_single_id
        assert Product.query.filter_by(confezione_origine_id=sorgente.id).count() == 1


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


def test_borbone_invoices_use_only_base_discount_and_retail_units():
    catalogo = {row["barcode"]: row for row in CATALOGO_REALE}

    # 126,64 EUR è un collo da 48 confezioni da 10; costo unitario IVA 22%.
    assert catalogo["CFIBBLU48X10"]["formato"] == "10 capsule"
    assert catalogo["CFIBBLU48X10"]["costo"] == Decimal("3.057828")
    # 15,73 EUR è un collo da 6 confezioni solubili; IVA 10%.
    assert catalogo["AMGINSENG6X16"]["formato"] == "16 capsule"
    assert catalogo["AMGINSENG6X16"]["costo"] == Decimal("2.739642")

    nuovi_sku = {
        "REBDEK100N",
        "AMSDEK100NDONCARLO",
        "44BDEK150N",
        "DGBBLU90N",
        "GRBRED006REDVENDING",
        "44BORO150N",
        "BLTBDEK100N",
        "DGBDEK90N",
    }
    assert all(catalogo[sku]["quantita"] == 0 for sku in nuovi_sku)
    assert all(catalogo[sku]["aggiorna_costo_da_fattura"] for sku in nuovi_sku)
    assert all(row["category"] != "Capsule solubili" for row in CATALOGO_REALE)


def test_supplied_product_images_are_mapped_by_sku():
    expected_skus = {
        "44BDEK150N",
        "8029804009776",
        "AMGINSENG6X16",
        "AMNOCCIOLINO6X16",
        "AMTHELIMONE6X16",
        "BLTBBLU100N",
        "BLTBRED100N",
        "CFIBBLU48X10",
        "CFIBRED48X10",
        "DGBBLU90N",
        "DGBRED90N",
        "DGSUPERGIN4X16",
        "GRBBLU006SUPERVENDIN",
        "GRBRED006REDVENDING",
        "LVBORO100N",
        "LVBROSSA100N",
        "RESGINSEN6X10",
    }
    catalogo = {row["barcode"]: row for row in CATALOGO_REALE}

    for sku in expected_skus:
        expected_url = f"/static/img/products/{sku}.webp"
        assert IMMAGINI_PRODOTTI[sku] == expected_url
        assert catalogo[sku]["image"] == expected_url


def test_new_invoice_products_start_at_zero_without_inventory_movements(app):
    with app.app_context():
        db.session.add_all(
            [
                StoreLocation(
                    codice="via-pepoli",
                    nome="Pepoli",
                    indirizzo="Via Pepoli 198",
                    cap="91100",
                    comune="Trapani",
                    provincia="TP",
                    ragione_sociale="Pepoli",
                    partita_iva="00000000001",
                ),
                StoreLocation(
                    codice="via-vespri",
                    nome="Vespri",
                    indirizzo="Via Vespri 235",
                    cap="91019",
                    comune="Valderice",
                    provincia="TP",
                    ragione_sociale="Vespri",
                    partita_iva="00000000002",
                ),
            ]
        )
        db.session.add(VatRate(nome="IVA 10%", aliquota=10, attiva=True))
        db.session.commit()

        sync_catalogo_reale()
        sync_varianti_singole()

        for sku in (
            "44BDEK150N",
            "8029804009776",
            "BLTBBLU100N",
            "BLTBRED100N",
            "CFIBBLU48X10",
            "CFIBRED48X10",
            "DGBBLU90N",
            "DGBRED90N",
            "LVBORO100N",
            "LVBROSSA100N",
        ):
            confezione = Product.query.filter_by(sku_barcode=sku).one()
            singola = Product.query.filter_by(sku_barcode=f"{sku}-SINGOLA").one()
            assert singola.immagine_url == confezione.immagine_url

        assert Product.query.filter_by(
            sku_barcode="AMGINSENG6X16-SINGOLA"
        ).one_or_none() is None
        assert Product.query.filter_by(
            sku_barcode="GRBBLU006SUPERVENDIN-SINGOLA"
        ).one_or_none() is None

        prodotto = Product.query.filter_by(sku_barcode="REBDEK100N").one()
        assert prodotto.quantita_disponibile == 0
        assert prodotto.prezzo_acquisto == Decimal("17.697930")
        assert InventoryMovement.query.filter_by(prodotto_id=prodotto.id).count() == 0

        runner = app.test_cli_runner()
        result = runner.invoke(args=["imposta-giacenza-ultimo-import", "--quantita", "30"])
        assert result.exit_code == 0, result.output
        assert "38 rettifiche" in result.output
        assert StoreInventory.query.filter(
            StoreInventory.prodotto_id.in_(
                Product.query.with_entities(Product.id).filter(
                    Product.sku_barcode.in_(ULTIMO_IMPORT_BORBONE_SKU)
                )
            ),
            StoreInventory.quantita_disponibile == 30,
        ).count() == len(ULTIMO_IMPORT_BORBONE_SKU) * 2
        assert InventoryMovement.query.filter_by(prodotto_id=prodotto.id).count() == 2

        second_result = runner.invoke(
            args=["imposta-giacenza-ultimo-import", "--quantita", "30"]
        )
        assert second_result.exit_code == 0, second_result.output
        assert "0 rettifiche" in second_result.output
        assert InventoryMovement.query.filter_by(prodotto_id=prodotto.id).count() == 2

        reconciliation = runner.invoke(args=["riconcilia-giacenze-20-luglio"])
        assert reconciliation.exit_code == 0, reconciliation.output
        for store_code, targets in GIACENZE_20_LUGLIO.items():
            store = StoreLocation.query.filter_by(codice=store_code).one()
            for reference, target in targets.items():
                target_product = Product.query.filter_by(sku_barcode=reference).one()
                inventory = StoreInventory.query.filter_by(
                    punto_vendita_id=store.id,
                    prodotto_id=target_product.id,
                ).one()
                assert inventory.quantita_disponibile == target


def test_july_borbone_orders_load_sellable_units_once_per_store(app):
    with app.app_context():
        db.session.add_all(
            [
                StoreLocation(
                    codice="via-pepoli",
                    nome="Via Pepoli",
                    indirizzo="Via Pepoli 198",
                    cap="91100",
                    comune="Trapani",
                    provincia="TP",
                    ragione_sociale="Pepoli",
                    partita_iva="00000000001",
                ),
                StoreLocation(
                    codice="via-vespri",
                    nome="Via Vespri",
                    indirizzo="Via Vespri 235",
                    cap="91019",
                    comune="Valderice",
                    provincia="TP",
                    ragione_sociale="Vespri",
                    partita_iva="00000000002",
                ),
            ]
        )
        db.session.add(VatRate(nome="IVA 10%", aliquota=10, attiva=True))
        db.session.commit()
        sync_catalogo_reale()

        punti_vendita = {
            punto.codice: punto for punto in StoreLocation.query.all()
        }
        sku_richiesti = {
            sku_interno
            for ordine in ORDINI_BORBONE_LUGLIO_2026.values()
            for _, sku_interno, _, _ in ordine["righe"]
        }
        prodotti = {
            prodotto.sku_barcode: prodotto
            for prodotto in Product.query.filter(
                Product.sku_barcode.in_(sku_richiesti)
            ).all()
        }
        giacenze_iniziali = {
            (numero, sku): quantita_fisica(
                prodotti[sku], punti_vendita[ordine["punto_vendita"]].id
            )
            for numero, ordine in ORDINI_BORBONE_LUGLIO_2026.items()
            for _, sku, _, _ in ordine["righe"]
        }

        runner = app.test_cli_runner()
        result = runner.invoke(args=["carica-ordini-borbone-luglio-2026"])
        assert result.exit_code == 0, result.output
        assert "26 movimenti creati, 0 righe gia presenti" in result.output

        for numero, ordine in ORDINI_BORBONE_LUGLIO_2026.items():
            punto_vendita = punti_vendita[ordine["punto_vendita"]]
            for _, sku, colli, confezioni_per_collo in ordine["righe"]:
                assert quantita_fisica(prodotti[sku], punto_vendita.id) == (
                    giacenze_iniziali[(numero, sku)]
                    + colli * confezioni_per_collo
                )
            assert InventoryMovement.query.filter_by(
                tipo_movimento="carico",
                punto_vendita_id=punto_vendita.id,
                riferimento_entita=f"ordine-borbone:{numero}",
            ).count() == len(ordine["righe"])

        assert Product.query.filter_by(sku_barcode="DGBBLU4X16N").one().prezzo_acquisto == Decimal(
            "2.633828"
        )
        assert Product.query.filter_by(sku_barcode="DGNOCCIOLONE4X16").one().prezzo_acquisto == Decimal(
            "3.667950"
        )
        assert Product.query.filter_by(sku_barcode="8034028330636").one().prezzo_acquisto == Decimal(
            "15.067000"
        )

        second_result = runner.invoke(args=["carica-ordini-borbone-luglio-2026"])
        assert second_result.exit_code == 0, second_result.output
        assert "0 movimenti creati, 26 righe gia presenti" in second_result.output
        assert InventoryMovement.query.filter(
            InventoryMovement.riferimento_entita.in_(
                ["ordine-borbone:283447", "ordine-borbone:283449"]
            )
        ).count() == 26


def test_september_borbone_invoices_add_or_replace_stock_idempotently(app):
    with app.app_context():
        db.session.add_all(
            [
                StoreLocation(
                    codice="via-pepoli",
                    nome="Via Pepoli",
                    indirizzo="Via Pepoli 198",
                    cap="91100",
                    comune="Trapani",
                    provincia="TP",
                    ragione_sociale="Pepoli",
                    partita_iva="00000000001",
                ),
                StoreLocation(
                    codice="via-vespri",
                    nome="Via Vespri",
                    indirizzo="Via Vespri 235",
                    cap="91019",
                    comune="Valderice",
                    provincia="TP",
                    ragione_sociale="Vespri",
                    partita_iva="00000000002",
                ),
            ]
        )
        db.session.add(VatRate(nome="IVA 10%", aliquota=10, attiva=True))
        db.session.commit()
        sync_catalogo_reale()

        punti_vendita = {
            punto.codice: punto for punto in StoreLocation.query.all()
        }
        sku_richiesti = {
            sku_interno
            for fattura in FATTURE_BORBONE_SETTEMBRE_2026.values()
            for _, sku_interno, _, _ in fattura["righe"]
        }
        prodotti = {
            prodotto.sku_barcode: prodotto
            for prodotto in Product.query.filter(
                Product.sku_barcode.in_(sku_richiesti)
            ).all()
        }

        # Valderice: un valore provvisorio alto va sostituito, mentre 69 va
        # mantenuto e incrementato. A Trapani anche 99 deve essere sommato.
        casi_iniziali = (
            ("via-vespri", "8034028330780", 99),
            ("via-vespri", "8034028330827", 69),
            ("via-pepoli", "8034028336706", 99),
        )
        for codice_negozio, sku, quantita in casi_iniziali:
            punto_vendita = punti_vendita[codice_negozio]
            prodotto = prodotti[sku]
            giacenza = StoreInventory.query.filter_by(
                punto_vendita_id=punto_vendita.id,
                prodotto_id=prodotto.id,
            ).first()
            if not giacenza:
                giacenza = StoreInventory(
                    punto_vendita_id=punto_vendita.id,
                    prodotto_id=prodotto.id,
                    quantita_minima_alert=prodotto.quantita_minima_alert,
                )
                db.session.add(giacenza)
            giacenza.quantita_disponibile = quantita
        db.session.commit()

        giacenze_iniziali = {
            (numero, sku): quantita_fisica(
                prodotti[sku], punti_vendita[fattura["punto_vendita"]].id
            )
            for numero, fattura in FATTURE_BORBONE_SETTEMBRE_2026.items()
            for _, sku, _, _ in fattura["righe"]
        }

        runner = app.test_cli_runner()
        preview = runner.invoke(
            args=["carica-fatture-borbone-settembre-2026", "--dry-run"]
        )
        assert preview.exit_code == 0, preview.output
        assert "database non e stato modificato" in preview.output
        assert InventoryMovement.query.filter(
            InventoryMovement.riferimento_entita.like("fattura-borbone:%")
        ).count() == 0

        result = runner.invoke(args=["carica-fatture-borbone-settembre-2026"])
        assert result.exit_code == 0, result.output
        assert "38 movimenti creati (1 rettifiche)" in result.output

        for numero, fattura in FATTURE_BORBONE_SETTEMBRE_2026.items():
            punto_vendita = punti_vendita[fattura["punto_vendita"]]
            soglia = fattura["sostituisci_se_almeno"]
            for _, sku, colli, confezioni_per_collo in fattura["righe"]:
                quantita_fattura = colli * confezioni_per_collo
                quantita_iniziale = giacenze_iniziali[(numero, sku)]
                quantita_attesa = (
                    quantita_fattura
                    if soglia is not None and quantita_iniziale >= soglia
                    else quantita_iniziale + quantita_fattura
                )
                assert quantita_fisica(
                    prodotti[sku], punto_vendita.id
                ) == quantita_attesa

        assert Product.query.filter_by(
            sku_barcode="THELIMON4X16DOLCEGUS"
        ).one().prezzo_acquisto == Decimal("3.667950")
        assert Product.query.filter_by(
            sku_barcode="DGCAMOMILLA4X16"
        ).one().prezzo_acquisto == Decimal("3.667950")

        second_result = runner.invoke(
            args=["carica-fatture-borbone-settembre-2026"]
        )
        assert second_result.exit_code == 0, second_result.output
        assert "0 movimenti creati (0 rettifiche), 38 righe gia presenti" in second_result.output
        assert InventoryMovement.query.filter(
            InventoryMovement.riferimento_entita.in_(
                [
                    "fattura-borbone:1000022858",
                    "fattura-borbone:1000022859",
                ]
            )
        ).count() == 38

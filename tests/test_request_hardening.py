from sqlalchemy import event

from app.extensions import db
from app.models import (
    Brand,
    Category,
    Customer,
    Product,
    Sale,
    SaleItem,
    StoreInventory,
    StoreLocation,
    User,
)
from app.services.catalog_service import sync_varianti_singole
from tests.helpers import get_csrf_token, login


def test_cash_search_rejects_invalid_category(client):
    login(client, "operatore", "operator123")

    response = client.get("/cassa/search?categoria_id=abc")

    assert response.status_code == 400
    assert response.get_json()["error"] == "Categoria non valida."


def test_checkout_handles_invalid_json_payload(client):
    login(client, "operatore", "operator123")

    response = client.post(
        "/cassa/checkout",
        data={
            "csrf_token": get_csrf_token(client, "/cassa"),
            "cart_payload": "{not-json}",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Payload checkout non valido." in response.data


def test_sales_list_handles_invalid_date_filters(client):
    login(client, "admin", "admin123")

    response = client.get("/vendite?data_da=not-a-date", follow_redirects=True)

    assert response.status_code == 200
    assert b"Data iniziale non valida." in response.data


def test_analysis_handles_invalid_period_dates(client):
    login(client, "admin", "admin123")

    response = client.get(
        "/analisi?periodo=custom&data_inizio=2026-02-30&data_fine=2026-03-05",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Intervallo date non valido." in response.data


def test_analysis_page_renders_with_postgres_safe_aggregations(client):
    login(client, "admin", "admin123")

    response = client.get("/analisi?periodo=ultimi_7")

    assert response.status_code == 200
    assert b"Analisi Vendite" in response.data


def test_analysis_page_renders_when_a_store_filter_is_active(app, client):
    store = StoreLocation(
        codice="analysis-store",
        nome="Sede Analisi",
        indirizzo="Via Analisi 1",
        cap="91100",
        comune="Trapani",
        provincia="TP",
        ragione_sociale="Sede Analisi SRL",
        partita_iva="00000000009",
    )
    db.session.add(store)
    db.session.flush()
    admin = User.query.filter_by(username="admin").first()
    admin.punto_vendita_predefinito_id = store.id
    db.session.commit()

    login(client, "admin", "admin123")
    response = client.get("/analisi?periodo=ultimi_7")

    assert response.status_code == 200
    assert b"Analisi Vendite" in response.data


def test_global_store_selector_switches_the_viewed_location(app, client):
    first = StoreLocation(
        codice="selector-one",
        nome="Sede Uno",
        indirizzo="Via Uno 1",
        cap="91100",
        comune="Trapani",
        provincia="TP",
        ragione_sociale="Sede Uno SRL",
        partita_iva="00000000007",
    )
    second = StoreLocation(
        codice="selector-two",
        nome="Sede Due",
        indirizzo="Via Due 2",
        cap="91019",
        comune="Valderice",
        provincia="TP",
        ragione_sociale="Sede Due SRL",
        partita_iva="00000000008",
    )
    db.session.add_all([first, second])
    db.session.flush()
    operatore = User.query.filter_by(username="operatore").first()
    operatore.punto_vendita_predefinito_id = first.id
    db.session.commit()
    login(client, "operatore", "operator123")

    response = client.post(
        "/impostazioni/punto-vendita",
        data={
            "csrf_token": get_csrf_token(client, "/cassa"),
            "punto_vendita_id": second.id,
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Sede Due" in response.data


def test_cash_page_uses_simple_product_tiles(client):
    login(client, "operatore", "operator123")

    response = client.get("/cassa")

    assert response.status_code == 200
    assert b"Il carrello \xc3\xa8 vuoto." in response.data
    assert b'class="category-chip active"' in response.data
    assert b'id="categoriaFilter"' in response.data
    assert b'Cerca un prodotto o leggi il barcode' in response.data
    assert b"Completa vendita" in response.data
    assert b'id="customerCheckoutModal"' in response.data
    assert b'id="checkoutNewCustomerForm"' in response.data
    assert b'id="singleQuantityModal"' in response.data
    assert b"Vendita cialde e capsule singole" in response.data
    assert b"Cliente generico" in response.data
    assert b'id="vatRateId"' not in response.data


def test_cash_all_excludes_singles_but_singles_category_returns_them(app, client):
    with app.app_context():
        sync_varianti_singole()
        singola = Product.query.filter_by(sku_barcode="TEST-001-SINGOLA").one()
        singola.quantita_disponibile = 7
        categoria_singole = Category.query.filter_by(nome="Singole").one()
        singola_id = singola.id
        categoria_id = categoria_singole.id
        db.session.commit()

    login(client, "operatore", "operator123")

    tutti = client.get("/cassa/search").get_json()
    assert all(not prodotto["is_variante_singola"] for prodotto in tutti)
    assert singola_id not in {prodotto["id"] for prodotto in tutti}

    singole = client.get(f"/cassa/search?categoria_id={categoria_id}").get_json()
    assert {prodotto["id"] for prodotto in singole} == {singola_id}
    assert singole[0]["is_variante_singola"] is True


def test_cash_all_contains_only_coffee_packs_and_solubles_keep_their_category(app, client):
    with app.app_context():
        sorgente = Product.query.filter_by(sku_barcode="TEST-001").one()
        categoria_solubili = Category(nome="Solubili")
        db.session.add(categoria_solubili)
        db.session.flush()
        solubile = Product(
            nome="Ginseng Test",
            categoria_id=categoria_solubili.id,
            marca_id=sorgente.marca_id,
            vat_rate_id=sorgente.vat_rate_id,
            compatibilita_id=sorgente.compatibilita_id,
            prezzo_acquisto=1,
            prezzo_vendita=2,
            quantita_disponibile=10,
            sku_barcode="SOLUBILE-TEST",
            attivo=True,
        )
        db.session.add(solubile)
        db.session.commit()
        solubile_id = solubile.id
        categoria_id = categoria_solubili.id

    login(client, "operatore", "operator123")

    tutti = client.get("/cassa/search").get_json()
    assert solubile_id not in {prodotto["id"] for prodotto in tutti}

    solubili = client.get(f"/cassa/search?categoria_id={categoria_id}").get_json()
    assert {prodotto["id"] for prodotto in solubili} == {solubile_id}


def test_cash_all_orders_best_sellers_first_for_current_store(app, client):
    with app.app_context():
        sorgente = Product.query.filter_by(sku_barcode="TEST-001").one()
        marca = Brand.query.filter_by(nome="Marca Test").one()
        piu_venduto = Product(
            nome="Capsule Piu Vendute",
            categoria_id=sorgente.categoria_id,
            marca_id=marca.id,
            vat_rate_id=sorgente.vat_rate_id,
            compatibilita_id=sorgente.compatibilita_id,
            prezzo_acquisto=1,
            prezzo_vendita=2,
            quantita_disponibile=30,
            sku_barcode="BEST-SELLER",
            attivo=True,
        )
        punto_vendita = StoreLocation(
            codice="best-seller-store",
            nome="Negozio Classifica",
            indirizzo="Via Test 1",
            cap="91100",
            comune="Trapani",
            provincia="TP",
            ragione_sociale="Negozio Classifica SRL",
            partita_iva="00000000006",
        )
        db.session.add_all([piu_venduto, punto_vendita])
        db.session.flush()
        operatore = User.query.filter_by(username="operatore").one()
        operatore.punto_vendita_predefinito_id = punto_vendita.id
        vendita = Sale(
            operatore_id=operatore.id,
            punto_vendita_id=punto_vendita.id,
            stato="completata",
        )
        db.session.add(vendita)
        db.session.flush()
        db.session.add(
            SaleItem(
                vendita_id=vendita.id,
                prodotto_id=piu_venduto.id,
                quantita=12,
                prezzo_unitario=2,
                subtotale=24,
            )
        )
        db.session.commit()
        prodotto_id = piu_venduto.id

    login(client, "operatore", "operator123")
    prodotti = client.get("/cassa/search").get_json()

    assert prodotti[0]["id"] == prodotto_id


def test_checkout_can_create_customer_without_leaving_cash_register(app, client):
    login(client, "operatore", "operator123")

    response = client.post(
        "/cassa/clienti",
        data={
            "csrf_token": get_csrf_token(client, "/cassa"),
            "nome": "Cliente",
            "cognome": "Cassa",
            "telefono": "3331234567",
            "attivo": "1",
        },
        headers={"Accept": "application/json"},
    )

    assert response.status_code == 201
    assert response.get_json()["display_name"] == "Cliente Cassa"
    with app.app_context():
        assert Customer.query.filter_by(nome="Cliente", cognome="Cassa").count() == 1


def test_cash_page_does_not_eager_load_unrelated_collections(app, client):
    store = StoreLocation(
        codice="test-store",
        nome="Negozio Test",
        indirizzo="Via Test 1",
        cap="91100",
        comune="Trapani",
        provincia="TP",
        ragione_sociale="Negozio Test SRL",
        partita_iva="00000000000",
        attivo=True,
    )
    db.session.add(store)
    db.session.flush()

    operatore = User.query.filter_by(username="operatore").first()
    operatore.punto_vendita_predefinito_id = store.id
    prodotto = Product.query.first()
    db.session.add(
        StoreInventory(
            punto_vendita_id=store.id,
            prodotto_id=prodotto.id,
            quantita_disponibile=20,
            quantita_minima_alert=5,
        )
    )
    db.session.commit()

    login(client, "operatore", "operator123")
    statements = []

    def count_statement(*_args):
        statements.append(1)

    event.listen(db.engine, "before_cursor_execute", count_statement)
    try:
        response = client.get("/cassa")
    finally:
        event.remove(db.engine, "before_cursor_execute", count_statement)

    assert response.status_code == 200
    assert len(statements) <= 8

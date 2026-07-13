from sqlalchemy import event

from app.extensions import db
from app.models import Product, StoreInventory, StoreLocation, User
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


def test_cash_page_uses_simple_product_tiles(client):
    login(client, "operatore", "operator123")

    response = client.get("/cassa")

    assert response.status_code == 200
    assert b"Il carrello \xc3\xa8 vuoto." in response.data
    assert b'class="category-chip active"' in response.data
    assert b'id="categoriaFilter"' in response.data
    assert b'Cerca un prodotto o leggi il barcode' in response.data
    assert b"Completa vendita" in response.data


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

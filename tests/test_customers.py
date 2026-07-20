from app.extensions import db
from app.models import Compatibility, Customer, Product, StoreInventory, StoreLocation, User
from app.services.sale_service import crea_vendita
from tests.helpers import get_csrf_token, login


def test_customer_crud_and_soft_delete(client):
    login(client, "operatore", "operator123")
    response = client.post(
        "/clienti/nuovo",
        data={
            "csrf_token": get_csrf_token(client, "/clienti/nuovo"),
            "nome": "Giulia",
            "cognome": "Rossi",
            "telefono": "3331234567",
            "codice_fiscale": "rssgli80a01h501x",
            "attivo": "1",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Giulia Rossi" in response.data

    cliente = Customer.query.filter_by(codice_fiscale="RSSGLI80A01H501X").one()
    response = client.post(
        f"/clienti/{cliente.id}/modifica",
        data={
            "csrf_token": get_csrf_token(client, f"/clienti/{cliente.id}/modifica"),
            "nome": "Giulia",
            "cognome": "Bianchi",
            "email": "GIULIA@example.it",
            "codice_fiscale": "RSSGLI80A01H501X",
            "attivo": "1",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    db.session.refresh(cliente)
    assert cliente.cognome == "Bianchi"
    assert cliente.email == "giulia@example.it"

    response = client.post(
        f"/clienti/{cliente.id}/elimina",
        data={"csrf_token": get_csrf_token(client, "/clienti")},
        follow_redirects=True,
    )
    assert response.status_code == 200
    db.session.refresh(cliente)
    assert cliente.attivo is False


def test_customer_search_uses_contact_and_fiscal_fields(client):
    db.session.add(Customer(nome="Cliente Ricerca", telefono="3205550101", attivo=True))
    db.session.commit()
    login(client, "operatore", "operator123")

    response = client.get("/clienti?q=3205550101")

    assert response.status_code == 200
    assert b"Cliente Ricerca" in response.data


def test_new_customer_forms_are_compact_and_show_compatibility_early(client):
    login(client, "operatore", "operator123")

    page_response = client.get("/clienti/nuovo")
    assert page_response.status_code == 200
    assert b'name="ragione_sociale"' not in page_response.data
    assert b'name="codice_fiscale"' not in page_response.data
    assert b'name="partita_iva"' not in page_response.data
    assert page_response.data.index(b'name="compatibilita_preferita_id"') < page_response.data.index(
        b'name="telefono"'
    )

    cash_response = client.get("/cassa")
    assert cash_response.status_code == 200
    assert b'id="cashCustomerCompany"' not in cash_response.data
    assert b'id="cashCustomerFiscalCode"' not in cash_response.data
    assert b'id="cashCustomerVat"' not in cash_response.data
    assert cash_response.data.index(b'id="cashCustomerCompatibility"') < cash_response.data.index(
        b'id="cashCustomerPhone"'
    )


def test_new_customer_uses_current_store_city_and_preferred_compatibility(client):
    store = StoreLocation(
        codice="customer-vespri",
        nome="Via Vespri",
        indirizzo="Via Vespri 235",
        cap="91019",
        comune="Valderice",
        provincia="TP",
        ragione_sociale="Test Vespri",
        partita_iva="10000000001",
    )
    db.session.add(store)
    db.session.commit()
    compatibility = Compatibility.query.filter_by(nome="Nespresso").one()
    login(client, "operatore", "operator123")
    with client.session_transaction() as session:
        session["punto_vendita_id"] = store.id

    response = client.post(
        "/clienti/nuovo",
        data={
            "csrf_token": get_csrf_token(client, "/clienti/nuovo"),
            "nome": "Cliente Valderice",
            "compatibilita_preferita_id": str(compatibility.id),
            "attivo": "1",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    customer = Customer.query.filter_by(nome="Cliente Valderice").one()
    assert customer.citta == "Valderice"
    assert customer.compatibilita_preferita_id == compatibility.id


def test_customer_history_contains_all_sales_products_and_stores(client):
    operatore = User.query.filter_by(username="operatore").one()
    product = Product.query.filter_by(sku_barcode="TEST-001").one()
    customer = Customer(nome="Cliente Storico", attivo=True)
    pepoli = StoreLocation(
        codice="history-pepoli",
        nome="Via Conte Agostino Pepoli",
        indirizzo="Via Pepoli 198",
        cap="91100",
        comune="Trapani",
        provincia="TP",
        ragione_sociale="Test Pepoli",
        partita_iva="10000000002",
    )
    vespri = StoreLocation(
        codice="history-vespri",
        nome="Via Vespri",
        indirizzo="Via Vespri 235",
        cap="91019",
        comune="Valderice",
        provincia="TP",
        ragione_sociale="Test Vespri",
        partita_iva="10000000003",
    )
    db.session.add_all([customer, pepoli, vespri])
    db.session.flush()
    db.session.add_all(
        [
            StoreInventory(
                punto_vendita_id=pepoli.id,
                prodotto_id=product.id,
                quantita_disponibile=10,
            ),
            StoreInventory(
                punto_vendita_id=vespri.id,
                prodotto_id=product.id,
                quantita_disponibile=10,
            ),
        ]
    )
    db.session.commit()
    first = crea_vendita(
        operatore_id=operatore.id,
        customer_id=customer.id,
        items=[{"prodotto_id": product.id, "quantita": 1}],
        sconto_tipo="nessuno",
        sconto_valore=0,
        metodo_pagamento="contanti",
        punto_vendita_id=pepoli.id,
    )
    second = crea_vendita(
        operatore_id=operatore.id,
        customer_id=customer.id,
        items=[{"prodotto_id": product.id, "quantita": 2}],
        sconto_tipo="nessuno",
        sconto_valore=0,
        metodo_pagamento="carta",
        punto_vendita_id=vespri.id,
    )
    login(client, "operatore", "operator123")

    response = client.get(f"/clienti/{customer.id}/storico")

    assert response.status_code == 200
    assert f"Vendita #{first.id}".encode() in response.data
    assert f"Vendita #{second.id}".encode() in response.data
    assert response.data.count(b"Capsule Test") == 2
    assert b"Via Conte Agostino Pepoli" in response.data
    assert b"Via Vespri" in response.data

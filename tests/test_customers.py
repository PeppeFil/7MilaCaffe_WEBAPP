from app.extensions import db
from app.models import Customer
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

from tests.helpers import get_csrf_token, login
from app.models import Product, User
from app.services.sale_service import crea_vendita


def test_login_success(client):
    response = login(client, "admin", "admin123")
    assert response.status_code == 200
    assert b"Cassa" in response.data


def test_login_username_is_case_insensitive(client):
    response = login(client, "AdMiN", "admin123")
    assert response.status_code == 200
    assert b"Cassa" in response.data


def test_operator_forbidden_on_admin_route(client):
    login(client, "operatore", "operator123")
    response = client.get("/prodotti/nuovo")
    assert response.status_code == 403


def test_login_ignores_external_next_redirect(client):
    response = login(
        client,
        "admin",
        "admin123",
        next_page="https://evil.example/collect",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/cassa")


def test_login_requires_csrf_token(client):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )

    assert response.status_code == 400


def test_analysis_page_loads(client):
    with client.application.app_context():
        prodotto = Product.query.filter_by(sku_barcode="TEST-001").first()
        operatore = User.query.filter_by(username="operatore").first()
        crea_vendita(
            operatore_id=operatore.id,
            items=[{"prodotto_id": prodotto.id, "quantita": 1}],
            sconto_tipo="nessuno",
            sconto_valore=0,
            metodo_pagamento="contanti",
        )
    login(client, "admin", "admin123")
    response = client.get("/analisi")
    assert response.status_code == 200
    assert b"Analisi Vendite" in response.data


def test_logout_requires_post(client):
    login(client, "admin", "admin123")

    get_response = client.get("/logout", follow_redirects=False)
    post_response = client.post(
        "/logout",
        data={"csrf_token": get_csrf_token(client, "/cassa")},
        follow_redirects=False,
    )

    assert get_response.status_code == 405
    assert post_response.status_code == 302
    assert post_response.headers["Location"].endswith("/login")

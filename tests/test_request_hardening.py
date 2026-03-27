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

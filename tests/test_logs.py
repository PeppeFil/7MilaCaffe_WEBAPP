from app.models import ActivityLog
from tests.helpers import login


def test_log_page_is_available_only_to_username_admin(client):
    login(client, "operatore", "operator123")
    assert client.get("/log").status_code == 403

    client.post("/logout", data={"csrf_token": _csrf(client)})
    login(client, "AdMiN", "admin123")
    response = client.get("/log")

    assert response.status_code == 200
    assert b"Registro delle attivit" in response.data


def test_login_is_written_to_activity_log(client):
    login(client, "admin", "admin123")

    with client.application.app_context():
        log = ActivityLog.query.filter_by(azione="accesso").one()
        assert log.utente.username == "admin"
        assert log.entita_tipo == "session"


def _csrf(client):
    client.get("/cassa")
    with client.session_transaction() as session:
        return session["_csrf_token"]

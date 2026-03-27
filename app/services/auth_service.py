from app.models import User


def autentica_utente(username: str, password: str) -> User | None:
    user = User.query.filter_by(username=username, attivo=True).first()
    if user and user.check_password(password):
        return user
    return None

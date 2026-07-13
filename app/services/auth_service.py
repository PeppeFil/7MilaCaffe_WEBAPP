from sqlalchemy import func

from app.models import User


def autentica_utente(username: str, password: str) -> User | None:
    user = (
        User.query.filter(
            func.lower(User.username) == username.lower(),
            User.attivo.is_(True),
        ).first()
    )
    if user and user.check_password(password):
        return user
    return None

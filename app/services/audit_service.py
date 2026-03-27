from app.extensions import db
from app.models import ActivityLog


def registra_attivita(
    utente_id: int,
    azione: str,
    entita_tipo: str,
    entita_id: str | None = None,
    dettagli: str | None = None,
    commit: bool = False,
) -> ActivityLog:
    log = ActivityLog(
        utente_id=utente_id,
        azione=azione,
        entita_tipo=entita_tipo,
        entita_id=entita_id,
        dettagli=dettagli,
    )
    db.session.add(log)
    if commit:
        db.session.commit()
    return log

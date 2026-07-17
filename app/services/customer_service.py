from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Customer
from app.services.audit_service import registra_attivita


def apply_customer_data(cliente: Customer, data) -> None:
    nome = (data.get("nome") or "").strip()
    ragione_sociale = (data.get("ragione_sociale") or "").strip()
    if not nome and not ragione_sociale:
        raise ValueError("Inserisci almeno il nome o la ragione sociale.")
    cliente.nome = nome or ragione_sociale
    cliente.cognome = (data.get("cognome") or "").strip() or None
    cliente.ragione_sociale = ragione_sociale or None
    cliente.email = (data.get("email") or "").strip().lower() or None
    cliente.telefono = (data.get("telefono") or "").strip() or None
    cliente.codice_fiscale = (
        (data.get("codice_fiscale") or "").strip().replace(" ", "").upper() or None
    )
    cliente.partita_iva = (
        (data.get("partita_iva") or "").strip().replace(" ", "").upper() or None
    )
    cliente.indirizzo = (data.get("indirizzo") or "").strip() or None
    cliente.note = (data.get("note") or "").strip() or None
    cliente.attivo = str(data.get("attivo", "1")) in {"1", "true", "True", "on"}


def create_customer(data, utente_id: int, commit: bool = True) -> Customer:
    cliente = Customer()
    apply_customer_data(cliente, data)
    db.session.add(cliente)
    db.session.flush()
    registra_attivita(
        utente_id=utente_id,
        azione="creazione_cliente",
        entita_tipo="customer",
        entita_id=str(cliente.id),
        dettagli=cliente.ragione_sociale or cliente.nome,
    )
    if commit:
        db.session.commit()
    return cliente


def customer_error(exc: Exception) -> str:
    if isinstance(exc, IntegrityError):
        return "Codice fiscale o Partita IVA già presenti per un altro cliente."
    return str(exc)

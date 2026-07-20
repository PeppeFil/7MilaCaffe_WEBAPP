from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Compatibility, Customer
from app.services.audit_service import registra_attivita


def apply_customer_data(
    cliente: Customer,
    data,
    citta_predefinita: str | None = None,
) -> None:
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
    citta_inviata = (data.get("citta") or "").strip()
    if citta_inviata:
        cliente.citta = citta_inviata
    elif cliente.id is None and citta_predefinita:
        cliente.citta = citta_predefinita.strip() or None

    compatibilita_id = (data.get("compatibilita_preferita_id") or "").strip()
    if compatibilita_id:
        try:
            compatibilita_id_int = int(compatibilita_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("Compatibilita preferita non valida.") from exc
        compatibilita = db.session.get(Compatibility, compatibilita_id_int)
        if not compatibilita:
            raise ValueError("Compatibilita preferita non disponibile.")
        cliente.compatibilita_preferita_id = compatibilita.id
    else:
        cliente.compatibilita_preferita_id = None
    cliente.note = (data.get("note") or "").strip() or None
    cliente.attivo = str(data.get("attivo", "1")) in {"1", "true", "True", "on"}


def create_customer(
    data,
    utente_id: int,
    commit: bool = True,
    citta_predefinita: str | None = None,
) -> Customer:
    cliente = Customer()
    apply_customer_data(cliente, data, citta_predefinita=citta_predefinita)
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

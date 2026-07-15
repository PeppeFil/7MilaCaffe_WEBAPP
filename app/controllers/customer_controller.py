from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Customer


customer_bp = Blueprint("customers", __name__)


@customer_bp.route("/clienti")
@login_required
def index():
    query = Customer.query
    search = (request.args.get("q") or "").strip()
    stato = (request.args.get("stato") or "attivi").strip()
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Customer.nome.ilike(like),
                Customer.cognome.ilike(like),
                Customer.ragione_sociale.ilike(like),
                Customer.email.ilike(like),
                Customer.telefono.ilike(like),
                Customer.codice_fiscale.ilike(like),
                Customer.partita_iva.ilike(like),
            )
        )
    if stato == "attivi":
        query = query.filter(Customer.attivo.is_(True))
    elif stato == "eliminati":
        query = query.filter(Customer.attivo.is_(False))
    clienti = query.order_by(Customer.ragione_sociale.asc(), Customer.nome.asc()).all()
    return render_template(
        "customers/list.html", clienti=clienti, search=search, stato=stato
    )


@customer_bp.route("/clienti/nuovo", methods=["GET", "POST"])
@login_required
def nuovo():
    if request.method == "POST":
        cliente = Customer()
        try:
            _apply_customer_data(cliente, request.form)
            db.session.add(cliente)
            db.session.commit()
            flash("Cliente creato correttamente.", "success")
            return redirect(url_for("customers.index"))
        except (IntegrityError, ValueError) as exc:
            db.session.rollback()
            flash(_customer_error(exc), "danger")
    return render_template("customers/form.html", cliente=None)


@customer_bp.route("/clienti/<int:customer_id>/modifica", methods=["GET", "POST"])
@login_required
def modifica(customer_id):
    cliente = Customer.query.get_or_404(customer_id)
    if request.method == "POST":
        try:
            _apply_customer_data(cliente, request.form)
            db.session.commit()
            flash("Cliente aggiornato.", "success")
            return redirect(url_for("customers.index", stato="tutti"))
        except (IntegrityError, ValueError) as exc:
            db.session.rollback()
            flash(_customer_error(exc), "danger")
    return render_template("customers/form.html", cliente=cliente)


@customer_bp.route("/clienti/<int:customer_id>/elimina", methods=["POST"])
@login_required
def elimina(customer_id):
    cliente = Customer.query.get_or_404(customer_id)
    cliente.attivo = False
    db.session.commit()
    flash("Cliente eliminato dall'elenco attivo. Le vendite storiche restano conservate.", "warning")
    return redirect(url_for("customers.index"))


@customer_bp.route("/clienti/<int:customer_id>/ripristina", methods=["POST"])
@login_required
def ripristina(customer_id):
    cliente = Customer.query.get_or_404(customer_id)
    cliente.attivo = True
    db.session.commit()
    flash("Cliente ripristinato.", "success")
    return redirect(url_for("customers.index", stato="tutti"))


def _apply_customer_data(cliente: Customer, data) -> None:
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
    cliente.attivo = data.get("attivo", "1") == "1"


def _customer_error(exc: Exception) -> str:
    if isinstance(exc, IntegrityError):
        return "Codice fiscale o Partita IVA già presenti per un altro cliente."
    return str(exc)

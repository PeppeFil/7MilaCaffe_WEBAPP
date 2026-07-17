from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Customer
from app.services.audit_service import registra_attivita
from app.services.customer_service import apply_customer_data, create_customer, customer_error


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
        try:
            create_customer(request.form, current_user.id)
            flash("Cliente creato correttamente.", "success")
            return redirect(url_for("customers.index"))
        except (IntegrityError, ValueError) as exc:
            db.session.rollback()
            flash(customer_error(exc), "danger")
    return render_template("customers/form.html", cliente=None)


@customer_bp.route("/clienti/<int:customer_id>/modifica", methods=["GET", "POST"])
@login_required
def modifica(customer_id):
    cliente = Customer.query.get_or_404(customer_id)
    if request.method == "POST":
        try:
            apply_customer_data(cliente, request.form)
            registra_attivita(
                utente_id=current_user.id,
                azione="modifica_cliente",
                entita_tipo="customer",
                entita_id=str(cliente.id),
                dettagli=cliente.ragione_sociale or cliente.nome,
            )
            db.session.commit()
            flash("Cliente aggiornato.", "success")
            return redirect(url_for("customers.index", stato="tutti"))
        except (IntegrityError, ValueError) as exc:
            db.session.rollback()
            flash(customer_error(exc), "danger")
    return render_template("customers/form.html", cliente=cliente)


@customer_bp.route("/clienti/<int:customer_id>/elimina", methods=["POST"])
@login_required
def elimina(customer_id):
    cliente = Customer.query.get_or_404(customer_id)
    cliente.attivo = False
    registra_attivita(
        utente_id=current_user.id,
        azione="disattiva_cliente",
        entita_tipo="customer",
        entita_id=str(cliente.id),
        dettagli=cliente.ragione_sociale or cliente.nome,
    )
    db.session.commit()
    flash("Cliente eliminato dall'elenco attivo. Le vendite storiche restano conservate.", "warning")
    return redirect(url_for("customers.index"))


@customer_bp.route("/clienti/<int:customer_id>/ripristina", methods=["POST"])
@login_required
def ripristina(customer_id):
    cliente = Customer.query.get_or_404(customer_id)
    cliente.attivo = True
    registra_attivita(
        utente_id=current_user.id,
        azione="ripristina_cliente",
        entita_tipo="customer",
        entita_id=str(cliente.id),
        dettagli=cliente.ragione_sociale or cliente.nome,
    )
    db.session.commit()
    flash("Cliente ripristinato.", "success")
    return redirect(url_for("customers.index", stato="tutti"))

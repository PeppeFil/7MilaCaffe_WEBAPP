from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import Compatibility, Customer, Sale, SaleItem
from app.services.audit_service import registra_attivita
from app.services.customer_service import apply_customer_data, create_customer, customer_error
from app.services.store_service import punto_vendita_corrente


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
    clienti = (
        query.options(selectinload(Customer.vendite))
        .order_by(Customer.ragione_sociale.asc(), Customer.nome.asc())
        .all()
    )
    return render_template(
        "customers/list.html", clienti=clienti, search=search, stato=stato
    )


@customer_bp.route("/clienti/nuovo", methods=["GET", "POST"])
@login_required
def nuovo():
    punto_vendita = punto_vendita_corrente()
    if request.method == "POST":
        try:
            create_customer(
                request.form,
                current_user.id,
                citta_predefinita=punto_vendita.comune if punto_vendita else None,
            )
            flash("Cliente creato correttamente.", "success")
            return redirect(url_for("customers.index"))
        except (IntegrityError, ValueError) as exc:
            db.session.rollback()
            flash(customer_error(exc), "danger")
    return render_template(
        "customers/form.html",
        cliente=None,
        compatibilita=Compatibility.query.order_by(Compatibility.nome.asc()).all(),
        citta_predefinita=punto_vendita.comune if punto_vendita else "",
    )


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
    return render_template(
        "customers/form.html",
        cliente=cliente,
        compatibilita=Compatibility.query.order_by(Compatibility.nome.asc()).all(),
        citta_predefinita=cliente.citta or "",
    )


@customer_bp.route("/clienti/<int:customer_id>/storico")
@login_required
def storico(customer_id):
    cliente = (
        Customer.query.options(
            selectinload(Customer.vendite).selectinload(Sale.righe).joinedload(SaleItem.prodotto)
        )
        .filter_by(id=customer_id)
        .first_or_404()
    )
    vendite = sorted(cliente.vendite, key=lambda vendita: vendita.data_ora, reverse=True)
    return render_template(
        "customers/_history.html",
        cliente=cliente,
        vendite=vendite,
    )


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

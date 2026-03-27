from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.extensions import db
from app.models import Brand, Compatibility, Customer, ShopPreference, VatRate
from app.models.constants import RUOLO_ADMIN
from app.utils.decorators import role_required
from app.utils.parsers import to_decimal


settings_bp = Blueprint("settings", __name__)

DEFAULT_PREFERENCES = {
    "shop_name": ("Nome negozio", "7MilaCaffe"),
    "shop_address": ("Indirizzo", ""),
    "shop_phone": ("Telefono", ""),
    "shop_email": ("Email", ""),
    "shop_vat_number": ("Partita IVA", ""),
}


@settings_bp.route("/impostazioni")
@login_required
def index():
    _ensure_default_preferences()
    preferenze = ShopPreference.query.order_by(ShopPreference.chiave.asc()).all()
    marche = Brand.query.order_by(Brand.nome.asc()).all()
    compatibilita = Compatibility.query.order_by(Compatibility.nome.asc()).all()
    aliquote_iva = VatRate.query.order_by(VatRate.aliquota.asc()).all()
    clienti = Customer.query.order_by(Customer.nome.asc(), Customer.cognome.asc()).all()
    return render_template(
        "settings/index.html",
        preferenze=preferenze,
        marche=marche,
        compatibilita=compatibilita,
        aliquote_iva=aliquote_iva,
        clienti=clienti,
    )


@settings_bp.route("/impostazioni/preferenze", methods=["POST"])
@role_required(RUOLO_ADMIN)
def salva_preferenze():
    _ensure_default_preferences()
    try:
        for key in DEFAULT_PREFERENCES:
            value = (request.form.get(key) or "").strip()
            pref = ShopPreference.query.filter_by(chiave=key).first()
            if pref:
                pref.valore = value
        db.session.commit()
        flash("Preferenze negozio aggiornate.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Errore salvataggio preferenze: {exc}", "danger")
    return redirect(url_for("settings.index"))


@settings_bp.route("/impostazioni/marche", methods=["POST"])
@role_required(RUOLO_ADMIN)
def crea_marca():
    nome = (request.form.get("nome") or "").strip()
    if not nome:
        flash("Nome marca obbligatorio.", "warning")
        return redirect(url_for("settings.index"))

    existing = Brand.query.filter(Brand.nome.ilike(nome)).first()
    if existing:
        flash("Marca gia presente.", "warning")
        return redirect(url_for("settings.index"))

    try:
        db.session.add(Brand(nome=nome, descrizione=(request.form.get("descrizione") or "").strip() or None))
        db.session.commit()
        flash("Marca creata.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Errore creazione marca: {exc}", "danger")
    return redirect(url_for("settings.index"))


@settings_bp.route("/impostazioni/compatibilita", methods=["POST"])
@role_required(RUOLO_ADMIN)
def crea_compatibilita():
    nome = (request.form.get("nome") or "").strip()
    if not nome:
        flash("Nome compatibilita obbligatorio.", "warning")
        return redirect(url_for("settings.index"))

    existing = Compatibility.query.filter(Compatibility.nome.ilike(nome)).first()
    if existing:
        flash("Compatibilita gia presente.", "warning")
        return redirect(url_for("settings.index"))

    try:
        db.session.add(
            Compatibility(nome=nome, descrizione=(request.form.get("descrizione") or "").strip() or None)
        )
        db.session.commit()
        flash("Compatibilita creata.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Errore creazione compatibilita: {exc}", "danger")
    return redirect(url_for("settings.index"))


@settings_bp.route("/impostazioni/iva", methods=["POST"])
@role_required(RUOLO_ADMIN)
def crea_aliquota_iva():
    nome = (request.form.get("nome") or "").strip()
    aliquota = to_decimal(request.form.get("aliquota"), Decimal("0.00"))
    if not nome:
        flash("Nome aliquota IVA obbligatorio.", "warning")
        return redirect(url_for("settings.index"))

    predefinita = request.form.get("predefinita") == "1"
    attiva = request.form.get("attiva") != "0"

    try:
        if predefinita:
            VatRate.query.update({"predefinita": False})

        db.session.add(
            VatRate(
                nome=nome,
                aliquota=aliquota,
                descrizione=(request.form.get("descrizione") or "").strip() or None,
                predefinita=predefinita,
                attiva=attiva,
            )
        )
        db.session.commit()
        flash("Aliquota IVA creata.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Errore creazione aliquota IVA: {exc}", "danger")
    return redirect(url_for("settings.index"))


@settings_bp.route("/impostazioni/clienti", methods=["POST"])
@role_required(RUOLO_ADMIN)
def crea_cliente():
    nome = (request.form.get("nome") or "").strip()
    if not nome:
        flash("Nome cliente obbligatorio.", "warning")
        return redirect(url_for("settings.index"))

    try:
        cliente = Customer(
            nome=nome,
            cognome=(request.form.get("cognome") or "").strip() or None,
            ragione_sociale=(request.form.get("ragione_sociale") or "").strip() or None,
            email=(request.form.get("email") or "").strip() or None,
            telefono=(request.form.get("telefono") or "").strip() or None,
            codice_fiscale=(request.form.get("codice_fiscale") or "").strip() or None,
            partita_iva=(request.form.get("partita_iva") or "").strip() or None,
            indirizzo=(request.form.get("indirizzo") or "").strip() or None,
            note=(request.form.get("note") or "").strip() or None,
            attivo=request.form.get("attivo", "1") == "1",
        )
        db.session.add(cliente)
        db.session.commit()
        flash("Cliente creato.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Errore creazione cliente: {exc}", "danger")
    return redirect(url_for("settings.index"))


@settings_bp.route("/impostazioni/clienti/<int:customer_id>/toggle", methods=["POST"])
@role_required(RUOLO_ADMIN)
def toggle_cliente(customer_id):
    cliente = Customer.query.get_or_404(customer_id)
    try:
        cliente.attivo = not cliente.attivo
        db.session.commit()
        flash("Stato cliente aggiornato.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Errore aggiornamento cliente: {exc}", "danger")
    return redirect(url_for("settings.index"))


def _ensure_default_preferences() -> None:
    for key, (label, default_value) in DEFAULT_PREFERENCES.items():
        pref = ShopPreference.query.filter_by(chiave=key).first()
        if pref:
            continue
        db.session.add(ShopPreference(chiave=key, valore=default_value, descrizione=label))
    db.session.commit()

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Sale
from app.models.constants import RUOLO_ADMIN
from app.services.sale_service import annulla_vendita, query_vendite
from app.services.store_service import punto_vendita_corrente
from app.utils.decorators import role_required


sales_bp = Blueprint("sales", __name__)


@sales_bp.route("/vendite")
@login_required
def index():
    filtri = request.args.to_dict()
    punto_vendita = punto_vendita_corrente()
    try:
        vendite = query_vendite(filtri, punto_vendita.id if punto_vendita else None).limit(300).all()
    except ValueError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("sales.index"))
    return render_template("sales/list.html", vendite=vendite, filtri=filtri)


@sales_bp.route("/vendite/<int:sale_id>")
@login_required
def detail(sale_id):
    punto_vendita = punto_vendita_corrente()
    query = Sale.query.filter_by(id=sale_id)
    if punto_vendita:
        query = query.filter_by(punto_vendita_id=punto_vendita.id)
    vendita = query.first_or_404()
    return render_template("sales/detail.html", vendita=vendita)


@sales_bp.route("/vendite/<int:sale_id>/annulla", methods=["POST"])
@role_required(RUOLO_ADMIN)
def annulla(sale_id):
    punto_vendita = punto_vendita_corrente()
    if punto_vendita and not Sale.query.filter_by(id=sale_id, punto_vendita_id=punto_vendita.id).first():
        flash("Vendita non disponibile per questo punto vendita.", "danger")
        return redirect(url_for("sales.index"))
    motivo = request.form.get("motivo", "Annullamento da pannello vendite")
    try:
        annulla_vendita(vendita_id=sale_id, operatore_id=current_user.id, motivo=motivo)
        flash("Vendita annullata e stock ripristinato.", "warning")
    except Exception as exc:
        db.session.rollback()
        flash(f"Impossibile annullare la vendita: {exc}", "danger")
    return redirect(url_for("sales.detail", sale_id=sale_id))

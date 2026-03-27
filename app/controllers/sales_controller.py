from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Sale
from app.models.constants import RUOLO_ADMIN
from app.services.sale_service import annulla_vendita, query_vendite
from app.utils.decorators import role_required


sales_bp = Blueprint("sales", __name__)


@sales_bp.route("/vendite")
@login_required
def index():
    filtri = request.args.to_dict()
    try:
        vendite = query_vendite(filtri).limit(300).all()
    except ValueError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("sales.index"))
    return render_template("sales/list.html", vendite=vendite, filtri=filtri)


@sales_bp.route("/vendite/<int:sale_id>")
@login_required
def detail(sale_id):
    vendita = Sale.query.get_or_404(sale_id)
    return render_template("sales/detail.html", vendita=vendita)


@sales_bp.route("/vendite/<int:sale_id>/annulla", methods=["POST"])
@role_required(RUOLO_ADMIN)
def annulla(sale_id):
    motivo = request.form.get("motivo", "Annullamento da pannello vendite")
    try:
        annulla_vendita(vendita_id=sale_id, operatore_id=current_user.id, motivo=motivo)
        flash("Vendita annullata e stock ripristinato.", "warning")
    except Exception as exc:
        db.session.rollback()
        flash(f"Impossibile annullare la vendita: {exc}", "danger")
    return redirect(url_for("sales.detail", sale_id=sale_id))

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Brand, Category, Compatibility, Product, Supplier
from app.models.constants import RUOLO_ADMIN
from app.services.audit_service import registra_attivita
from app.services.product_service import (
    aggiorna_prodotto,
    cerca_prodotti,
    crea_prodotto,
    duplica_prodotto,
    elimina_prodotto_logico,
    esporta_prodotti_csv,
    importa_prodotti_csv,
)
from app.utils.decorators import role_required


product_bp = Blueprint("products", __name__)


@product_bp.route("/prodotti")
@login_required
def index():
    filtri = request.args.to_dict()
    prodotti = cerca_prodotti(filtri).all()
    categorie = Category.query.order_by(Category.nome.asc()).all()
    marche = Brand.query.order_by(Brand.nome.asc()).all()
    compatibilita = Compatibility.query.order_by(Compatibility.nome.asc()).all()
    fornitori = Supplier.query.order_by(Supplier.nome.asc()).all()
    return render_template(
        "products/list.html",
        prodotti=prodotti,
        categorie=categorie,
        marche=marche,
        compatibilita=compatibilita,
        fornitori=fornitori,
        filtri=filtri,
    )


@product_bp.route("/prodotti/nuovo", methods=["GET", "POST"])
@role_required(RUOLO_ADMIN)
def nuovo():
    categorie = Category.query.order_by(Category.nome.asc()).all()
    marche = Brand.query.order_by(Brand.nome.asc()).all()
    compatibilita = Compatibility.query.order_by(Compatibility.nome.asc()).all()
    fornitori = Supplier.query.order_by(Supplier.nome.asc()).all()

    if request.method == "POST":
        try:
            prodotto = crea_prodotto(request.form)
            registra_attivita(
                utente_id=current_user.id,
                azione="creazione_prodotto",
                entita_tipo="product",
                entita_id=str(prodotto.id),
                dettagli=prodotto.nome,
                commit=True,
            )
            flash("Prodotto creato correttamente.", "success")
            return redirect(url_for("products.index"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Errore creazione prodotto: {exc}", "danger")

    return render_template(
        "products/form.html",
        categorie=categorie,
        marche=marche,
        compatibilita=compatibilita,
        fornitori=fornitori,
        prodotto=None,
    )


@product_bp.route("/prodotti/<int:product_id>/modifica", methods=["GET", "POST"])
@role_required(RUOLO_ADMIN)
def modifica(product_id):
    prodotto = Product.query.get_or_404(product_id)
    categorie = Category.query.order_by(Category.nome.asc()).all()
    marche = Brand.query.order_by(Brand.nome.asc()).all()
    compatibilita = Compatibility.query.order_by(Compatibility.nome.asc()).all()
    fornitori = Supplier.query.order_by(Supplier.nome.asc()).all()

    if request.method == "POST":
        try:
            aggiorna_prodotto(prodotto, request.form)
            registra_attivita(
                utente_id=current_user.id,
                azione="modifica_prodotto",
                entita_tipo="product",
                entita_id=str(prodotto.id),
                dettagli=prodotto.nome,
                commit=True,
            )
            flash("Prodotto aggiornato.", "success")
            return redirect(url_for("products.index"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Errore aggiornamento: {exc}", "danger")

    return render_template(
        "products/form.html",
        categorie=categorie,
        marche=marche,
        compatibilita=compatibilita,
        fornitori=fornitori,
        prodotto=prodotto,
    )


@product_bp.route("/prodotti/<int:product_id>/elimina", methods=["POST"])
@role_required(RUOLO_ADMIN)
def elimina(product_id):
    prodotto = Product.query.get_or_404(product_id)
    elimina_prodotto_logico(prodotto)
    registra_attivita(
        utente_id=current_user.id,
        azione="disattiva_prodotto",
        entita_tipo="product",
        entita_id=str(prodotto.id),
        dettagli=prodotto.nome,
        commit=True,
    )
    flash("Prodotto disattivato.", "warning")
    return redirect(url_for("products.index"))


@product_bp.route("/prodotti/<int:product_id>/duplica", methods=["POST"])
@role_required(RUOLO_ADMIN)
def duplica(product_id):
    prodotto = Product.query.get_or_404(product_id)
    clone = duplica_prodotto(prodotto)
    registra_attivita(
        utente_id=current_user.id,
        azione="duplica_prodotto",
        entita_tipo="product",
        entita_id=str(clone.id),
        dettagli=f"Duplicato da {prodotto.id}",
        commit=True,
    )
    flash("Prodotto duplicato.", "success")
    return redirect(url_for("products.modifica", product_id=clone.id))


@product_bp.route("/prodotti/export.csv")
@login_required
def export_csv():
    filtri = request.args.to_dict()
    csv_text = esporta_prodotti_csv(cerca_prodotti(filtri).all())
    return Response(
        csv_text,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=prodotti.csv"},
    )


@product_bp.route("/prodotti/import.csv", methods=["POST"])
@role_required(RUOLO_ADMIN)
def import_csv():
    file_storage = request.files.get("file_csv")
    if not file_storage:
        flash("File CSV mancante.", "warning")
        return redirect(url_for("products.index"))
    try:
        created, updated = importa_prodotti_csv(file_storage)
        registra_attivita(
            utente_id=current_user.id,
            azione="import_csv_prodotti",
            entita_tipo="product",
            dettagli=f"Creati: {created}, Aggiornati: {updated}",
            commit=True,
        )
        flash(f"Import completato. Creati: {created}, aggiornati: {updated}.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Errore import CSV: {exc}", "danger")
    return redirect(url_for("products.index"))

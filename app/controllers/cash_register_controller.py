import json

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.models import Brand, Category, Compatibility, Customer, Product, Sale, VatRate
from app.models.constants import METODI_PAGAMENTO
from app.services.sale_service import crea_vendita
from app.utils.parsers import to_int


cash_bp = Blueprint("cash", __name__)


def _serialize_product(product: Product) -> dict:
    return {
        "id": product.id,
        "nome": product.nome,
        "marca": product.brand.nome if product.brand else "",
        "formato_confezione": product.formato_confezione or "",
        "prezzo_vendita": float(product.prezzo_vendita),
        "quantita_disponibile": product.quantita_disponibile,
        "categoria": product.categoria.nome if product.categoria else "",
        "sku_barcode": product.sku_barcode or "",
        "immagine_url": product.immagine_url or "",
    }


@cash_bp.route("/cassa")
@login_required
def cassa():
    categorie = Category.query.order_by(Category.nome.asc()).all()
    prodotti_popolari = Product.query.filter_by(attivo=True).order_by(Product.nome.asc()).limit(25).all()
    clienti = Customer.query.filter_by(attivo=True).order_by(Customer.nome.asc(), Customer.cognome.asc()).all()
    aliquote_iva = VatRate.query.filter_by(attiva=True).order_by(VatRate.aliquota.asc()).all()
    return render_template(
        "cassa.html",
        categorie=categorie,
        prodotti=prodotti_popolari,
        prodotti_json=[_serialize_product(product) for product in prodotti_popolari],
        metodi_pagamento=METODI_PAGAMENTO,
        clienti=clienti,
        aliquote_iva=aliquote_iva,
    )


@cash_bp.route("/cassa/search")
@login_required
def search_products():
    q = (request.args.get("q") or "").strip()
    categoria_id = request.args.get("categoria_id")

    query = (
        Product.query.join(Product.brand)
        .outerjoin(Product.compatibility)
        .filter(Product.attivo.is_(True))
    )
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Product.nome.ilike(like),
                Brand.nome.ilike(like),
                Compatibility.nome.ilike(like),
                Product.sku_barcode.ilike(like),
            )
        )
    categoria_id_int = to_int(categoria_id, default=0)
    if categoria_id and not categoria_id_int:
        return jsonify({"error": "Categoria non valida."}), 400
    if categoria_id_int:
        query = query.filter(Product.categoria_id == categoria_id_int)

    products = query.order_by(Product.nome.asc()).limit(40).all()
    return jsonify([_serialize_product(product) for product in products])


@cash_bp.route("/cassa/checkout", methods=["POST"])
@login_required
def checkout():
    payload = request.form.get("cart_payload")
    if not payload and request.is_json:
        payload = json.dumps(request.get_json())
    if not payload:
        flash("Carrello non inviato.", "warning")
        return redirect(url_for("cash.cassa"))

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        flash("Payload checkout non valido.", "danger")
        return redirect(url_for("cash.cassa"))

    try:
        if not isinstance(data, dict):
            raise ValueError("Payload checkout non valido.")
        vendita = crea_vendita(
            operatore_id=current_user.id,
            items=data.get("items", []),
            sconto_tipo=data.get("sconto_tipo", "nessuno"),
            sconto_valore=data.get("sconto_valore", 0),
            metodo_pagamento=data.get("metodo_pagamento", "contanti"),
            note_cliente=data.get("note_cliente", ""),
            customer_id=data.get("customer_id"),
            vat_rate_id=data.get("vat_rate_id"),
        )
        flash(f"Vendita #{vendita.id} completata.", "success")
        return redirect(url_for("sales.detail", sale_id=vendita.id))
    except (TypeError, ValueError) as exc:
        flash(str(exc), "danger")
        return redirect(url_for("cash.cassa"))


@cash_bp.route("/cassa/ricevuta/<int:sale_id>")
@login_required
def ricevuta(sale_id):
    vendita = Sale.query.get_or_404(sale_id)
    return render_template("receipt.html", vendita=vendita)

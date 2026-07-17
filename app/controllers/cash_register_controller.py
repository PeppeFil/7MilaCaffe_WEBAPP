import json

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import case, func, or_

from app.models import Brand, Category, Compatibility, Customer, Product, Sale
from app.models.constants import METODI_PAGAMENTO
from app.services.sale_service import crea_vendita
from app.services.store_service import mappa_disponibilita_vendibile, punto_vendita_corrente
from app.utils.parsers import to_int


cash_bp = Blueprint("cash", __name__)


def _ordinamento_prodotti_cassa():
    """Borbone e Lollo in testa, poi le altre marche in ordine alfabetico."""
    priorita_marca = case(
        (func.lower(Brand.nome).like("%borbone%"), 0),
        (func.lower(Brand.nome).like("%lollo%"), 1),
        else_=2,
    )
    return priorita_marca, func.lower(Brand.nome), func.lower(Product.nome)


def _serialize_product(product: Product, quantita_disponibile: int | None = None) -> dict:
    return {
        "id": product.id,
        "nome": product.nome,
        "marca": product.brand.nome if product.brand else "",
        "formato_confezione": product.formato_confezione or "",
        "prezzo_vendita": float(product.prezzo_vendita),
        "quantita_disponibile": (
            product.quantita_disponibile if quantita_disponibile is None else quantita_disponibile
        ),
        "categoria": product.categoria.nome if product.categoria else "",
        "sku_barcode": product.sku_barcode or "",
        "immagine_url": product.immagine_url or "",
        "aliquota_iva": float(product.vat_rate.aliquota) if product.vat_rate else 0,
    }


@cash_bp.route("/cassa")
@login_required
def cassa():
    punto_vendita = punto_vendita_corrente()
    categorie = Category.query.order_by(Category.nome.asc()).all()
    prodotti_popolari = (
        Product.query.join(Product.brand)
        .filter(Product.attivo.is_(True))
        .order_by(*_ordinamento_prodotti_cassa())
        .limit(25)
        .all()
    )
    disponibilita = mappa_disponibilita_vendibile(
        punto_vendita.id if punto_vendita else None, prodotti_popolari
    )
    clienti = Customer.query.filter_by(attivo=True).order_by(Customer.nome.asc(), Customer.cognome.asc()).all()
    return render_template(
        "cassa.html",
        categorie=categorie,
        prodotti=prodotti_popolari,
        prodotti_json=[
            _serialize_product(
                product,
                disponibilita.get(product.id, 0),
            )
            for product in prodotti_popolari
        ],
        metodi_pagamento=METODI_PAGAMENTO,
        clienti=clienti,
    )


@cash_bp.route("/cassa/search")
@login_required
def search_products():
    punto_vendita = punto_vendita_corrente()
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

    products = query.order_by(*_ordinamento_prodotti_cassa()).limit(40).all()
    disponibilita = mappa_disponibilita_vendibile(
        punto_vendita.id if punto_vendita else None, products
    )
    return jsonify([
        _serialize_product(
            product,
            disponibilita.get(product.id, 0),
        )
        for product in products
    ])


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
            punto_vendita_id=(punto_vendita_corrente().id if punto_vendita_corrente() else None),
        )
        flash(f"Vendita #{vendita.id} completata.", "success")
        return redirect(url_for("sales.detail", sale_id=vendita.id))
    except (TypeError, ValueError) as exc:
        flash(str(exc), "danger")
        return redirect(url_for("cash.cassa"))


@cash_bp.route("/cassa/ricevuta/<int:sale_id>")
@login_required
def ricevuta(sale_id):
    punto_vendita = punto_vendita_corrente()
    query = Sale.query.filter_by(id=sale_id)
    if punto_vendita:
        query = query.filter_by(punto_vendita_id=punto_vendita.id)
    vendita = query.first_or_404()
    return render_template("receipt.html", vendita=vendita)

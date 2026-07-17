import json

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import case, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased

from app.extensions import db
from app.models import (
    Brand,
    Category,
    Compatibility,
    Customer,
    Product,
    Sale,
    SaleItem,
)
from app.models.constants import METODI_PAGAMENTO
from app.services.sale_service import crea_vendita
from app.services.customer_service import create_customer, customer_error
from app.services.store_service import mappa_disponibilita_vendibile, punto_vendita_corrente
from app.utils.parsers import to_int


cash_bp = Blueprint("cash", __name__)
CATEGORIE_CONFEZIONI_CAFFE = ("capsule", "cialde", "grani")


def _ordinamento_prodotti_cassa():
    """Borbone e Lollo in testa, poi le altre marche in ordine alfabetico."""
    priorita_marca = case(
        (func.lower(Brand.nome).like("%borbone%"), 0),
        (func.lower(Brand.nome).like("%lollo%"), 1),
        else_=2,
    )
    return priorita_marca, func.lower(Brand.nome), func.lower(Product.nome)


def _vendite_per_confezione(punto_vendita_id: int | None):
    """Aggrega le vendite completate sulla confezione, incluse le sue singole."""
    prodotto_venduto = aliased(Product)
    confezione_id = func.coalesce(
        prodotto_venduto.confezione_origine_id,
        SaleItem.prodotto_id,
    )
    query = (
        db.session.query(
            confezione_id.label("confezione_id"),
            func.sum(SaleItem.quantita).label("quantita_venduta"),
        )
        .select_from(SaleItem)
        .join(Sale, Sale.id == SaleItem.vendita_id)
        .join(prodotto_venduto, prodotto_venduto.id == SaleItem.prodotto_id)
        .filter(Sale.stato == "completata")
    )
    if punto_vendita_id:
        query = query.filter(Sale.punto_vendita_id == punto_vendita_id)
    return query.group_by(confezione_id).subquery()


def _query_tutti_caffe(punto_vendita_id: int | None):
    vendite = _vendite_per_confezione(punto_vendita_id)
    query = (
        Product.query.join(Product.brand)
        .join(Product.categoria)
        .outerjoin(Product.compatibility)
        .outerjoin(vendite, vendite.c.confezione_id == Product.id)
        .filter(
            Product.attivo.is_(True),
            Product.confezione_origine_id.is_(None),
            func.lower(Category.nome).in_(CATEGORIE_CONFEZIONI_CAFFE),
        )
    )
    ordinamento = (
        func.coalesce(vendite.c.quantita_venduta, 0).desc(),
        *_ordinamento_prodotti_cassa(),
    )
    return query, ordinamento


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
        "is_variante_singola": product.is_variante_singola,
    }


@cash_bp.route("/cassa")
@login_required
def cassa():
    punto_vendita = punto_vendita_corrente()
    punto_vendita_id = punto_vendita.id if punto_vendita else None
    categorie = (
        Category.query.join(Category.prodotti)
        .filter(Product.attivo.is_(True))
        .distinct()
        .order_by(Category.nome.asc())
        .all()
    )
    prodotti_query, ordinamento = _query_tutti_caffe(punto_vendita_id)
    prodotti_popolari = prodotti_query.order_by(*ordinamento).limit(100).all()
    disponibilita = mappa_disponibilita_vendibile(
        punto_vendita_id, prodotti_popolari
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
    punto_vendita_id = punto_vendita.id if punto_vendita else None
    q = (request.args.get("q") or "").strip()
    categoria_id = request.args.get("categoria_id")
    categoria_id_int = to_int(categoria_id, default=0)
    if categoria_id and not categoria_id_int:
        return jsonify({"error": "Categoria non valida."}), 400
    if categoria_id_int:
        query = (
            Product.query.join(Product.brand)
            .join(Product.categoria)
            .outerjoin(Product.compatibility)
            .filter(
                Product.attivo.is_(True),
                Product.categoria_id == categoria_id_int,
            )
        )
        ordinamento = _ordinamento_prodotti_cassa()
    else:
        query, ordinamento = _query_tutti_caffe(punto_vendita_id)

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

    products = query.order_by(*ordinamento).limit(100).all()
    disponibilita = mappa_disponibilita_vendibile(
        punto_vendita_id, products
    )
    return jsonify([
        _serialize_product(
            product,
            disponibilita.get(product.id, 0),
        )
        for product in products
    ])


@cash_bp.route("/cassa/clienti", methods=["POST"])
@login_required
def create_checkout_customer():
    try:
        cliente = create_customer(request.form, current_user.id)
        return jsonify(
            {
                "id": cliente.id,
                "display_name": cliente.display_name,
                "telefono": cliente.telefono or "",
                "email": cliente.email or "",
                "codice_fiscale": cliente.codice_fiscale or "",
                "partita_iva": cliente.partita_iva or "",
            }
        ), 201
    except (IntegrityError, ValueError) as exc:
        db.session.rollback()
        return jsonify({"error": customer_error(exc)}), 400


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

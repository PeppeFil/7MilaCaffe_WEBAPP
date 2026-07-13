from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Brand, Category, Compatibility, Product
from app.models.constants import RUOLO_ADMIN
from app.services.inventory_service import crea_movimento_manuale, query_movimenti
from app.services.store_service import mappa_giacenze, punto_vendita_corrente
from app.utils.decorators import role_required
from app.utils.parsers import to_decimal, to_int


inventory_bp = Blueprint("inventory", __name__)


@inventory_bp.route("/magazzino")
@login_required
def magazzino():
    punto_vendita = punto_vendita_corrente()
    filtri = request.args.to_dict()
    query = (
        Product.query.join(Product.brand)
        .outerjoin(Product.compatibility)
        .filter(Product.attivo.is_(True))
    )

    categoria_id = filtri.get("categoria_id")
    if categoria_id:
        query = query.filter(Product.categoria_id == to_int(categoria_id))

    marca_id = to_int(filtri.get("marca_id"), default=0)
    if marca_id:
        query = query.filter(Product.marca_id == marca_id)

    compatibilita_id = to_int(filtri.get("compatibilita_id"), default=0)
    if compatibilita_id:
        query = query.filter(Product.compatibilita_id == compatibilita_id)

    prodotti = query.order_by(Product.nome.asc()).all()
    _aggiungi_giacenze_correnti(prodotti, punto_vendita.id if punto_vendita else None)
    sotto_scorta = [
        p for p in prodotti if p.giacenza_corrente <= p.scorta_minima_corrente
    ]
    categorie = Category.query.order_by(Category.nome.asc()).all()
    marche = Brand.query.order_by(Brand.nome.asc()).all()
    compatibilita = Compatibility.query.order_by(Compatibility.nome.asc()).all()
    return render_template(
        "inventory/index.html",
        prodotti=prodotti,
        sotto_scorta=sotto_scorta,
        categorie=categorie,
        marche=marche,
        compatibilita=compatibilita,
        filtri=filtri,
    )


@inventory_bp.route("/movimenti", methods=["GET", "POST"])
@login_required
def movimenti():
    punto_vendita = punto_vendita_corrente()
    if request.method == "POST":
        if not current_user.has_role(RUOLO_ADMIN):
            flash("Solo Admin può registrare movimenti manuali.", "danger")
            return redirect(url_for("inventory.movimenti"))
        try:
            movimento = crea_movimento_manuale(
                prodotto_id=to_int(request.form.get("prodotto_id")),
                tipo_movimento=request.form.get("tipo_movimento"),
                quantita=to_int(request.form.get("quantita")),
                operatore_id=current_user.id,
                motivo=request.form.get("motivo") or "",
                costo_unitario=to_decimal(request.form.get("costo_unitario")),
                note=request.form.get("note") or "",
                punto_vendita_id=punto_vendita.id if punto_vendita else None,
            )
            flash(f"Movimento #{movimento.id} registrato.", "success")
            return redirect(url_for("inventory.movimenti"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Errore movimento: {exc}", "danger")

    filtri = request.args.to_dict()
    movimenti_data = query_movimenti(filtri, punto_vendita.id if punto_vendita else None).limit(200).all()
    prodotti = Product.query.filter_by(attivo=True).order_by(Product.nome.asc()).all()
    _aggiungi_giacenze_correnti(prodotti, punto_vendita.id if punto_vendita else None)
    categorie = Category.query.order_by(Category.nome.asc()).all()
    tipi_movimento = [
        "carico",
        "scarico_manuale",
        "rettifica",
        "reso",
        "omaggio",
        "danneggiato",
    ]
    return render_template(
        "movements/list.html",
        movimenti=movimenti_data,
        prodotti=prodotti,
        categorie=categorie,
        tipi_movimento=tipi_movimento,
        filtri=filtri,
    )


def _aggiungi_giacenze_correnti(prodotti, punto_vendita_id: int | None) -> None:
    giacenze = mappa_giacenze(punto_vendita_id, [p.id for p in prodotti]) if punto_vendita_id else {}
    for prodotto in prodotti:
        giacenza = giacenze.get(prodotto.id)
        prodotto.giacenza_corrente = giacenza.quantita_disponibile if giacenza else prodotto.quantita_disponibile
        prodotto.scorta_minima_corrente = (
            giacenza.quantita_minima_alert if giacenza else prodotto.quantita_minima_alert
        )
        if prodotto.giacenza_corrente <= 0:
            prodotto.stato_disponibilita_corrente = "esaurito"
        elif prodotto.giacenza_corrente <= prodotto.scorta_minima_corrente:
            prodotto.stato_disponibilita_corrente = "quasi esaurito"
        else:
            prodotto.stato_disponibilita_corrente = "disponibile"

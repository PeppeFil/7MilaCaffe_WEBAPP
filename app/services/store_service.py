from flask import g, session
from flask_login import current_user

from app.extensions import db
from app.models import Product, StoreInventory, StoreLocation


STORE_SESSION_KEY = "punto_vendita_id"


def punto_vendita_corrente() -> StoreLocation | None:
    if hasattr(g, "punto_vendita_corrente"):
        return g.punto_vendita_corrente

    store_id = session.get(STORE_SESSION_KEY)
    if store_id:
        punto_vendita = StoreLocation.query.filter_by(id=store_id, attivo=True).first()
        if punto_vendita:
            g.punto_vendita_corrente = punto_vendita
            return punto_vendita

    if not current_user.is_authenticated:
        g.punto_vendita_corrente = None
        return None

    punto_vendita = current_user.punto_vendita_predefinito
    if not punto_vendita or not punto_vendita.attivo:
        punto_vendita = StoreLocation.query.filter_by(attivo=True).order_by(StoreLocation.id.asc()).first()
    if punto_vendita:
        session[STORE_SESSION_KEY] = punto_vendita.id
    g.punto_vendita_corrente = punto_vendita
    return punto_vendita


def imposta_punto_vendita(store_id: int) -> StoreLocation:
    punto_vendita = StoreLocation.query.filter_by(id=store_id, attivo=True).first()
    if not punto_vendita:
        raise ValueError("Punto vendita non disponibile.")
    session[STORE_SESSION_KEY] = punto_vendita.id
    g.punto_vendita_corrente = punto_vendita
    return punto_vendita


def giacenza_prodotto(prodotto_id: int, punto_vendita_id: int) -> StoreInventory | None:
    return StoreInventory.query.filter_by(
        prodotto_id=prodotto_id, punto_vendita_id=punto_vendita_id
    ).first()


def quantita_fisica(prodotto: Product, punto_vendita_id: int | None) -> int:
    if punto_vendita_id is None:
        return prodotto.quantita_disponibile
    giacenza = giacenza_prodotto(prodotto.id, punto_vendita_id)
    return giacenza.quantita_disponibile if giacenza else 0


def quantita_disponibile(prodotto: Product, punto_vendita_id: int | None) -> int:
    """Quantita vendibile, includendo le confezioni apribili automaticamente."""
    fisica = quantita_fisica(prodotto, punto_vendita_id)
    if not prodotto.confezione_origine_id or not prodotto.unita_per_confezione:
        return fisica
    confezione = prodotto.confezione_origine or db.session.get(
        Product, prodotto.confezione_origine_id
    )
    if not confezione:
        return fisica
    return fisica + (
        quantita_fisica(confezione, punto_vendita_id) * prodotto.unita_per_confezione
    )


def giacenza_o_crea(prodotto: Product, punto_vendita_id: int) -> StoreInventory:
    giacenza = giacenza_prodotto(prodotto.id, punto_vendita_id)
    if giacenza:
        return giacenza
    giacenza = StoreInventory(
        prodotto_id=prodotto.id,
        punto_vendita_id=punto_vendita_id,
        quantita_disponibile=0,
        quantita_minima_alert=prodotto.quantita_minima_alert,
    )
    db.session.add(giacenza)
    db.session.flush()
    return giacenza


def mappa_giacenze(punto_vendita_id: int, prodotto_ids: list[int] | None = None) -> dict[int, StoreInventory]:
    query = StoreInventory.query.filter_by(punto_vendita_id=punto_vendita_id)
    if prodotto_ids:
        query = query.filter(StoreInventory.prodotto_id.in_(prodotto_ids))
    return {r.prodotto_id: r for r in query.all()}


def mappa_disponibilita_vendibile(
    punto_vendita_id: int | None, prodotti: list[Product]
) -> dict[int, int]:
    """Calcola in batch la disponibilita mostrata in cassa senza query N+1."""
    ids = {prodotto.id for prodotto in prodotti}
    ids.update(
        prodotto.confezione_origine_id
        for prodotto in prodotti
        if prodotto.confezione_origine_id
    )
    if punto_vendita_id is None:
        quantita = {
            prodotto.id: prodotto.quantita_disponibile
            for prodotto in Product.query.filter(Product.id.in_(ids)).all()
        }
    else:
        quantita = {
            prodotto_id: giacenza.quantita_disponibile
            for prodotto_id, giacenza in mappa_giacenze(
                punto_vendita_id, list(ids)
            ).items()
        }

    result = {}
    for prodotto in prodotti:
        disponibile = quantita.get(prodotto.id, 0)
        if prodotto.confezione_origine_id and prodotto.unita_per_confezione:
            disponibile += (
                quantita.get(prodotto.confezione_origine_id, 0)
                * prodotto.unita_per_confezione
            )
        result[prodotto.id] = disponibile
    return result

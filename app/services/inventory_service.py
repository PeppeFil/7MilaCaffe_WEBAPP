from datetime import datetime
from decimal import Decimal

from app.extensions import db
from app.models import InventoryMovement, Product
from app.services.audit_service import registra_attivita
from app.services.store_service import giacenza_o_crea, quantita_fisica
from app.utils.parsers import to_int
from app.utils.timezones import utc_now_naive


MOVEMENT_DIRECTIONS = {
    "carico": 1,
    "scarico_manuale": -1,
    "scarico_vendita": -1,
    "rettifica": 0,
    "reso": 1,
    "omaggio": -1,
    "danneggiato": -1,
    "ripristino_annullo_vendita": 1,
    "apertura_confezione": -1,
    "carico_da_confezione": 1,
}


def apri_confezioni_necessarie(
    prodotto: Product,
    quantita_richiesta: int,
    operatore_id: int,
    riferimento_entita: str,
    punto_vendita_id: int | None = None,
    data_ora: datetime | None = None,
) -> int:
    """Apre solo le confezioni indispensabili a coprire una vendita di singole."""
    if not prodotto.confezione_origine_id:
        return 0
    if not prodotto.unita_per_confezione or prodotto.unita_per_confezione <= 0:
        raise ValueError(f"Formato confezione non valido per {prodotto.nome}.")

    singole_disponibili = quantita_fisica(prodotto, punto_vendita_id)
    deficit = quantita_richiesta - singole_disponibili
    if deficit <= 0:
        return 0

    confezioni_da_aprire = (
        deficit + prodotto.unita_per_confezione - 1
    ) // prodotto.unita_per_confezione
    confezione = prodotto.confezione_origine or db.session.get(
        Product, prodotto.confezione_origine_id
    )
    if not confezione:
        raise ValueError(f"Confezione origine mancante per {prodotto.nome}.")
    confezioni_disponibili = quantita_fisica(confezione, punto_vendita_id)
    if confezioni_disponibili < confezioni_da_aprire:
        disponibilita_totale = singole_disponibili + (
            confezioni_disponibili * prodotto.unita_per_confezione
        )
        raise ValueError(
            f"Stock insufficiente per {prodotto.nome}. "
            f"Disponibile: {disponibilita_totale}"
        )

    motivo = (
        f"Apertura automatica di {confezioni_da_aprire} confezione/i "
        f"da {prodotto.unita_per_confezione} unita"
    )
    registra_movimento(
        prodotto=confezione,
        tipo_movimento="apertura_confezione",
        quantita=confezioni_da_aprire,
        operatore_id=operatore_id,
        motivo=motivo,
        riferimento_entita=riferimento_entita,
        data_ora=data_ora,
        punto_vendita_id=punto_vendita_id,
    )
    registra_movimento(
        prodotto=prodotto,
        tipo_movimento="carico_da_confezione",
        quantita=confezioni_da_aprire * prodotto.unita_per_confezione,
        operatore_id=operatore_id,
        motivo=motivo,
        riferimento_entita=riferimento_entita,
        data_ora=data_ora,
        punto_vendita_id=punto_vendita_id,
    )
    return confezioni_da_aprire


def registra_movimento(
    prodotto: Product,
    tipo_movimento: str,
    quantita: int,
    operatore_id: int,
    motivo: str = "",
    costo_unitario: Decimal | None = None,
    riferimento_entita: str | None = None,
    note: str | None = None,
    data_ora: datetime | None = None,
    punto_vendita_id: int | None = None,
    commit: bool = False,
) -> InventoryMovement:
    if tipo_movimento not in MOVEMENT_DIRECTIONS:
        raise ValueError("Tipo movimento non valido.")

    quantita_int = to_int(quantita)
    if tipo_movimento != "rettifica" and quantita_int <= 0:
        raise ValueError("La quantità deve essere positiva.")
    if tipo_movimento == "rettifica" and quantita_int == 0:
        raise ValueError("La rettifica deve avere quantità diversa da zero.")

    if tipo_movimento == "rettifica":
        delta = quantita_int
    else:
        delta = abs(quantita_int) * MOVEMENT_DIRECTIONS[tipo_movimento]

    giacenza = giacenza_o_crea(prodotto, punto_vendita_id) if punto_vendita_id else None
    quantita_corrente = giacenza.quantita_disponibile if giacenza else prodotto.quantita_disponibile
    nuova_giacenza = quantita_corrente + delta
    if nuova_giacenza < 0:
        raise ValueError(
            f"Stock insufficiente per {prodotto.nome}. Disponibile: {quantita_corrente}"
        )

    if giacenza:
        giacenza.quantita_disponibile = nuova_giacenza
    else:
        prodotto.quantita_disponibile = nuova_giacenza

    movimento = InventoryMovement(
        tipo_movimento=tipo_movimento,
        data_ora=data_ora or utc_now_naive(),
        prodotto_id=prodotto.id,
        quantita=delta,
        motivo=motivo or None,
        costo_unitario=costo_unitario or prodotto.prezzo_acquisto,
        operatore_id=operatore_id,
        punto_vendita_id=punto_vendita_id,
        riferimento_entita=riferimento_entita,
        note=note,
    )
    db.session.add(movimento)

    if commit:
        db.session.commit()

    return movimento


def crea_movimento_manuale(
    prodotto_id: int,
    tipo_movimento: str,
    quantita: int,
    operatore_id: int,
    motivo: str = "",
    costo_unitario: Decimal | None = None,
    note: str | None = None,
    punto_vendita_id: int | None = None,
) -> InventoryMovement:
    prodotto = Product.query.get_or_404(prodotto_id)
    if prodotto.is_variante_singola:
        raise ValueError(
            "La giacenza delle singole e gestita automaticamente aprendo le confezioni."
        )
    movimento = registra_movimento(
        prodotto=prodotto,
        tipo_movimento=tipo_movimento,
        quantita=quantita,
        operatore_id=operatore_id,
        motivo=motivo,
        costo_unitario=costo_unitario,
        note=note,
        punto_vendita_id=punto_vendita_id,
    )

    registra_attivita(
        utente_id=operatore_id,
        azione=f"movimento_{tipo_movimento}",
        entita_tipo="inventory_movement",
        entita_id=str(movimento.id),
        dettagli=f"Prodotto {prodotto.nome}, delta {movimento.quantita}",
    )
    db.session.commit()
    return movimento


def query_movimenti(filtri: dict, punto_vendita_id: int | None = None):
    query = InventoryMovement.query.join(Product).order_by(InventoryMovement.data_ora.desc())
    if punto_vendita_id:
        query = query.filter(InventoryMovement.punto_vendita_id == punto_vendita_id)

    tipo = (filtri.get("tipo") or "").strip()
    if tipo:
        query = query.filter(InventoryMovement.tipo_movimento == tipo)

    categoria_id = filtri.get("categoria_id")
    if categoria_id:
        query = query.filter(Product.categoria_id == to_int(categoria_id))

    prodotto_text = (filtri.get("prodotto") or "").strip()
    if prodotto_text:
        query = query.filter(Product.nome.ilike(f"%{prodotto_text}%"))

    return query

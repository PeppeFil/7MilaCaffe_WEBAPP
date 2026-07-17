from datetime import datetime, timedelta, timezone
from decimal import Decimal
from collections import defaultdict

from sqlalchemy.orm import joinedload, lazyload

from app.extensions import db
from app.models import Customer, Product, Sale, SaleItem, StoreInventory
from app.services.audit_service import registra_attivita
from app.services.inventory_service import apri_confezioni_necessarie, registra_movimento
from app.services.store_service import (
    giacenza_o_crea,
    quantita_disponibile,
    quantita_fisica,
)
from app.utils.parsers import to_decimal, to_int
from app.utils.timezones import utc_now_naive
from app.utils.timezones import ROME_TIMEZONE


MONEY = Decimal("0.01")


def _carica_e_blocca_prodotti(
    items: list[dict], punto_vendita_id: int | None
) -> list[tuple[Product, int]]:
    """Valida il carrello e blocca le righe stock in ordine deterministico."""
    righe_input: list[tuple[int, int]] = []
    richieste = defaultdict(int)
    for item in items:
        prodotto_id = to_int(item.get("prodotto_id"))
        quantita = to_int(item.get("quantita"))
        if not prodotto_id or quantita <= 0:
            raise ValueError("Quantità riga non valida.")
        righe_input.append((prodotto_id, quantita))
        richieste[prodotto_id] += quantita

    prodotti = (
        Product.query.filter(Product.id.in_(richieste), Product.attivo.is_(True))
        .order_by(Product.id.asc())
        .all()
    )
    product_map = {prodotto.id: prodotto for prodotto in prodotti}
    missing = set(richieste) - set(product_map)
    if missing:
        raise ValueError(f"Prodotto ID {min(missing)} non trovato o non attivo.")

    stock_ids = set(richieste)
    stock_ids.update(
        prodotto.confezione_origine_id
        for prodotto in prodotti
        if prodotto.confezione_origine_id
    )
    if punto_vendita_id is None:
        locked_products = (
            Product.query.options(lazyload("*"))
            .filter(Product.id.in_(stock_ids))
            .order_by(Product.id.asc())
            .populate_existing()
            .with_for_update()
            .all()
        )
        locked_map = {prodotto.id: prodotto for prodotto in locked_products}
        product_map.update(
            {product_id: locked_map[product_id] for product_id in richieste}
        )
    else:
        for product_id in sorted(stock_ids):
            prodotto = product_map.get(product_id) or db.session.get(Product, product_id)
            if prodotto:
                giacenza_o_crea(prodotto, punto_vendita_id)
        db.session.flush()
        (
            StoreInventory.query.options(lazyload("*"))
            .filter(
                StoreInventory.punto_vendita_id == punto_vendita_id,
                StoreInventory.prodotto_id.in_(stock_ids),
            )
            .order_by(StoreInventory.prodotto_id.asc())
            .populate_existing()
            .with_for_update()
            .all()
        )

    for product_id, quantita in richieste.items():
        prodotto = product_map[product_id]
        disponibile = quantita_disponibile(prodotto, punto_vendita_id)
        if disponibile < quantita:
            raise ValueError(
                f"Stock insufficiente per {prodotto.nome}. "
                f"Disponibile: {disponibile}"
            )

    # Un carrello può contenere sia una confezione sia le sue singole: validiamo
    # congiuntamente la risorsa fisica condivisa prima di creare la vendita.
    confezioni_richieste = defaultdict(int)
    for product_id, quantita in richieste.items():
        prodotto = product_map[product_id]
        if prodotto.confezione_origine_id:
            singole_fisiche = quantita_fisica(prodotto, punto_vendita_id)
            deficit = max(0, quantita - singole_fisiche)
            confezioni_richieste[prodotto.confezione_origine_id] += (
                deficit + prodotto.unita_per_confezione - 1
            ) // prodotto.unita_per_confezione
        else:
            confezioni_richieste[prodotto.id] += quantita

    for source_id, quantita in confezioni_richieste.items():
        source = product_map.get(source_id) or db.session.get(Product, source_id)
        disponibile = quantita_fisica(source, punto_vendita_id) if source else 0
        if disponibile < quantita:
            raise ValueError(
                f"Stock confezioni insufficiente per {source.nome if source else source_id}. "
                f"Disponibile: {disponibile}"
            )

    return [(product_map[product_id], qty) for product_id, qty in righe_input]


def crea_vendita(
    operatore_id: int,
    items: list[dict],
    sconto_tipo: str,
    sconto_valore,
    metodo_pagamento: str,
    note_cliente: str = "",
    customer_id=None,
    data_ora: datetime | None = None,
    punto_vendita_id: int | None = None,
    commit: bool = True,
) -> Sale:
    if not items:
        raise ValueError("Il carrello è vuoto.")

    righe_input = _carica_e_blocca_prodotti(items, punto_vendita_id)

    totale_lordo = Decimal("0.00")
    margine_totale = Decimal("0.00")
    righe_calcolate = []

    for prodotto, quantita in righe_input:
        if not prodotto.vat_rate or not prodotto.vat_rate.attiva:
            raise ValueError(f"Aliquota IVA mancante o non attiva per {prodotto.nome}.")

        prezzo_unitario = Decimal(str(prodotto.prezzo_vendita))
        costo_unitario = Decimal(str(prodotto.prezzo_acquisto))
        subtotale = (prezzo_unitario * quantita).quantize(MONEY)
        margine_riga = ((prezzo_unitario - costo_unitario) * quantita).quantize(MONEY)

        righe_calcolate.append(
            {
                "prodotto": prodotto,
                "quantita": quantita,
                "prezzo_unitario": prezzo_unitario,
                "costo_unitario": costo_unitario,
                "subtotale": subtotale,
                "margine_riga": margine_riga,
                "vat_rate_id": prodotto.vat_rate_id,
                "aliquota_iva": Decimal(str(prodotto.vat_rate.aliquota)),
            }
        )
        totale_lordo += subtotale
        margine_totale += margine_riga

    sconto_tipo = (sconto_tipo or "nessuno").strip().lower()
    sconto_valore_dec = to_decimal(sconto_valore, Decimal("0.00"))

    if sconto_tipo == "percentuale":
        sconto_importo = (totale_lordo * sconto_valore_dec) / Decimal("100")
    elif sconto_tipo == "fisso":
        sconto_importo = sconto_valore_dec
    else:
        sconto_tipo = "nessuno"
        sconto_importo = Decimal("0.00")

    if sconto_importo < 0:
        sconto_importo = Decimal("0.00")
    if sconto_importo > totale_lordo:
        sconto_importo = totale_lordo

    totale_lordo = totale_lordo.quantize(MONEY)
    sconto_importo = sconto_importo.quantize(MONEY)
    totale_netto = (totale_lordo - sconto_importo).quantize(MONEY)
    margine_totale = (margine_totale - sconto_importo).quantize(MONEY)

    customer_id_int = to_int(customer_id, default=0) or None
    if customer_id_int:
        customer = Customer.query.filter_by(id=customer_id_int, attivo=True).first()
        if not customer:
            raise ValueError("Cliente selezionato non valido.")

    # I prezzi di vendita sono IVA inclusa. Lo sconto viene ripartito sulle
    # righe e l'IVA viene scorporata con l'aliquota del singolo prodotto.
    residuo_netto = totale_netto
    totale_iva = Decimal("0.00")
    for index, riga in enumerate(righe_calcolate):
        if index == len(righe_calcolate) - 1:
            netto_riga = residuo_netto
        elif totale_lordo:
            netto_riga = (riga["subtotale"] * totale_netto / totale_lordo).quantize(MONEY)
            residuo_netto -= netto_riga
        else:
            netto_riga = Decimal("0.00")
        aliquota = riga["aliquota_iva"]
        iva_riga = (
            netto_riga * aliquota / (Decimal("100.00") + aliquota)
        ).quantize(MONEY)
        riga["totale_netto"] = netto_riga
        riga["totale_iva"] = iva_riga
        totale_iva += iva_riga

    aliquote = {riga["vat_rate_id"]: riga["aliquota_iva"] for riga in righe_calcolate}
    vat_rate_id_int = next(iter(aliquote)) if len(aliquote) == 1 else None
    aliquota_iva = next(iter(aliquote.values())) if len(aliquote) == 1 else Decimal("0.00")
    totale_iva = totale_iva.quantize(MONEY)

    vendita = Sale(
        data_ora=data_ora or utc_now_naive(),
        totale_lordo=totale_lordo,
        sconto_tipo=sconto_tipo,
        sconto_valore=sconto_valore_dec,
        totale_netto=totale_netto,
        metodo_pagamento=metodo_pagamento,
        note_cliente=(note_cliente or "").strip() or None,
        customer_id=customer_id_int,
        vat_rate_id=vat_rate_id_int,
        aliquota_iva_snapshot=aliquota_iva,
        totale_iva=totale_iva,
        operatore_id=operatore_id,
        punto_vendita_id=punto_vendita_id,
        stato="completata",
        margine_stimato=margine_totale,
    )
    db.session.add(vendita)
    db.session.flush()

    for r in righe_calcolate:
        item = SaleItem(
            vendita_id=vendita.id,
            prodotto_id=r["prodotto"].id,
            quantita=r["quantita"],
            prezzo_unitario=r["prezzo_unitario"],
            subtotale=r["subtotale"],
            totale_netto=r["totale_netto"],
            aliquota_iva_snapshot=r["aliquota_iva"],
            totale_iva=r["totale_iva"],
            costo_unitario_snapshot=r["costo_unitario"],
            margine_riga=r["margine_riga"],
        )
        db.session.add(item)

        apri_confezioni_necessarie(
            prodotto=r["prodotto"],
            quantita_richiesta=r["quantita"],
            operatore_id=operatore_id,
            riferimento_entita=f"vendita:{vendita.id}",
            data_ora=vendita.data_ora,
            punto_vendita_id=punto_vendita_id,
        )

        registra_movimento(
            prodotto=r["prodotto"],
            tipo_movimento="scarico_vendita",
            quantita=r["quantita"],
            operatore_id=operatore_id,
            motivo="Scarico automatico da vendita",
            riferimento_entita=f"vendita:{vendita.id}",
            data_ora=vendita.data_ora,
            punto_vendita_id=punto_vendita_id,
        )

    registra_attivita(
        utente_id=operatore_id,
        azione="creazione_vendita",
        entita_tipo="sale",
        entita_id=str(vendita.id),
        dettagli=f"Totale netto: {vendita.totale_netto}",
    )

    if commit:
        db.session.commit()
    return vendita


def annulla_vendita(
    vendita_id: int,
    operatore_id: int,
    motivo: str = "Annullamento manuale",
    data_ora: datetime | None = None,
    commit: bool = True,
) -> Sale:
    vendita = (
        Sale.query.options(joinedload(Sale.righe).joinedload(SaleItem.prodotto))
        .filter_by(id=vendita_id)
        .first_or_404()
    )
    if vendita.stato == "annullata":
        raise ValueError("La vendita risulta già annullata.")

    for riga in vendita.righe:
        registra_movimento(
            prodotto=riga.prodotto,
            tipo_movimento="ripristino_annullo_vendita",
            quantita=riga.quantita,
            operatore_id=operatore_id,
            motivo=motivo,
            riferimento_entita=f"vendita:{vendita.id}",
            data_ora=data_ora or utc_now_naive(),
            punto_vendita_id=vendita.punto_vendita_id,
        )

    vendita.stato = "annullata"

    registra_attivita(
        utente_id=operatore_id,
        azione="annullo_vendita",
        entita_tipo="sale",
        entita_id=str(vendita.id),
        dettagli=motivo,
    )

    if commit:
        db.session.commit()
    return vendita


def query_vendite(filtri: dict, punto_vendita_id: int | None = None):
    query = Sale.query.order_by(Sale.data_ora.desc())
    if punto_vendita_id:
        query = query.filter(Sale.punto_vendita_id == punto_vendita_id)

    stato = (filtri.get("stato") or "").strip()
    if stato:
        query = query.filter(Sale.stato == stato)

    data_da = (filtri.get("data_da") or "").strip()
    if data_da:
        try:
            local_start = datetime.fromisoformat(data_da).replace(tzinfo=ROME_TIMEZONE)
            query = query.filter(
                Sale.data_ora >= local_start.astimezone(timezone.utc).replace(tzinfo=None)
            )
        except ValueError as exc:
            raise ValueError("Data iniziale non valida.") from exc

    data_a = (filtri.get("data_a") or "").strip()
    if data_a:
        try:
            local_end = (
                datetime.fromisoformat(data_a).replace(tzinfo=ROME_TIMEZONE) + timedelta(days=1)
            )
            query = query.filter(
                Sale.data_ora < local_end.astimezone(timezone.utc).replace(tzinfo=None)
            )
        except ValueError as exc:
            raise ValueError("Data finale non valida.") from exc

    metodo = (filtri.get("metodo_pagamento") or "").strip()
    if metodo:
        query = query.filter(Sale.metodo_pagamento == metodo)

    return query

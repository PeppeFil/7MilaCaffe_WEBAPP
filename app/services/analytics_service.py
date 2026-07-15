from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func

from app.models import Category, Product, Sale, SaleItem, StoreInventory
from app.utils.timezones import rome_day_bounds_utc


def snapshot_dashboard(punto_vendita_id: int | None = None) -> dict:
    oggi, domani = rome_day_bounds_utc()

    vendite_oggi = Sale.query.filter(
        Sale.data_ora >= oggi,
        Sale.data_ora < domani,
        Sale.stato == "completata",
    )
    if punto_vendita_id:
        vendite_oggi = vendite_oggi.filter(Sale.punto_vendita_id == punto_vendita_id)

    incasso_oggi = vendite_oggi.with_entities(func.coalesce(func.sum(Sale.totale_netto), 0)).scalar()
    numero_vendite_oggi = vendite_oggi.count()

    pezzi_venduti_oggi = (
        SaleItem.query.join(Sale, SaleItem.vendita_id == Sale.id)
        .filter(Sale.data_ora >= oggi, Sale.data_ora < domani, Sale.stato == "completata")
        .with_entities(func.coalesce(func.sum(SaleItem.quantita), 0))
    )
    if punto_vendita_id:
        pezzi_venduti_oggi = pezzi_venduti_oggi.filter(Sale.punto_vendita_id == punto_vendita_id)
    pezzi_venduti_oggi = pezzi_venduti_oggi.scalar()

    if punto_vendita_id:
        sotto_scorta = (
            Product.query.join(StoreInventory, StoreInventory.prodotto_id == Product.id)
            .filter(
                Product.attivo.is_(True),
                StoreInventory.punto_vendita_id == punto_vendita_id,
                StoreInventory.quantita_disponibile <= StoreInventory.quantita_minima_alert,
            )
            .order_by(StoreInventory.quantita_disponibile.asc())
        )
    else:
        sotto_scorta = Product.query.filter(
            Product.attivo.is_(True),
            Product.quantita_disponibile <= Product.quantita_minima_alert,
        ).order_by(Product.quantita_disponibile.asc())

    prodotto_top_query = (
        Product.query.join(SaleItem, Product.id == SaleItem.prodotto_id)
        .join(Sale, Sale.id == SaleItem.vendita_id)
        .filter(Sale.data_ora >= oggi, Sale.data_ora < domani, Sale.stato == "completata")
        .with_entities(
            Product.nome,
            func.sum(SaleItem.quantita).label("pezzi"),
        )
        .group_by(Product.nome)
        .order_by(func.sum(SaleItem.quantita).desc())
    )
    if punto_vendita_id:
        prodotto_top_query = prodotto_top_query.filter(Sale.punto_vendita_id == punto_vendita_id)
    prodotto_top = prodotto_top_query.first()

    prodotti_sotto_scorta = sotto_scorta.all()
    if punto_vendita_id:
        giacenze_sotto_scorta = {
            r.prodotto_id: r
            for r in StoreInventory.query.filter(
                StoreInventory.punto_vendita_id == punto_vendita_id,
                StoreInventory.prodotto_id.in_([p.id for p in prodotti_sotto_scorta]),
            ).all()
        }
        for prodotto in prodotti_sotto_scorta:
            giacenza = giacenze_sotto_scorta.get(prodotto.id)
            prodotto.giacenza_corrente = giacenza.quantita_disponibile if giacenza else 0
            prodotto.scorta_minima_corrente = giacenza.quantita_minima_alert if giacenza else 0

    trend = _trend_ultimi_sette_giorni(punto_vendita_id)
    magazzino = _sintesi_magazzino(punto_vendita_id)

    return {
        "incasso_oggi": Decimal(str(incasso_oggi or 0)),
        "numero_vendite_oggi": numero_vendite_oggi,
        "pezzi_venduti_oggi": int(pezzi_venduti_oggi or 0),
        "sotto_scorta": prodotti_sotto_scorta,
        "prodotto_top_oggi": prodotto_top,
        "trend_7_giorni": trend,
        "magazzino": magazzino,
    }


def analisi_periodo(
    data_inizio: datetime, data_fine: datetime, punto_vendita_id: int | None = None
) -> dict:
    vendite_range = Sale.query.filter(
        Sale.data_ora >= data_inizio,
        Sale.data_ora < data_fine,
        Sale.stato == "completata",
    )
    if punto_vendita_id:
        vendite_range = vendite_range.filter(Sale.punto_vendita_id == punto_vendita_id)

    tot_fatturato = vendite_range.with_entities(func.coalesce(func.sum(Sale.totale_netto), 0)).scalar()
    tot_margine = vendite_range.with_entities(func.coalesce(func.sum(Sale.margine_stimato), 0)).scalar()
    media_scontrino = vendite_range.with_entities(func.coalesce(func.avg(Sale.totale_netto), 0)).scalar()
    count_vendite = vendite_range.count()

    righe_giornaliere = (
        vendite_range.with_entities(
            func.date(Sale.data_ora).label("giorno"),
            func.sum(Sale.totale_netto).label("totale"),
        )
        .group_by(func.date(Sale.data_ora))
        .order_by(func.date(Sale.data_ora))
        .all()
    )
    vendite_giornaliere, vendite_settimanali, vendite_mensili = _periodi_da_giorni(
        righe_giornaliere
    )

    fatturato_categoria_query = (
        Category.query.join(Product, Product.categoria_id == Category.id)
        .join(SaleItem, SaleItem.prodotto_id == Product.id)
        .join(Sale, Sale.id == SaleItem.vendita_id)
        .filter(Sale.data_ora >= data_inizio, Sale.data_ora < data_fine, Sale.stato == "completata")
        .with_entities(
            Category.nome,
            func.coalesce(func.sum(SaleItem.subtotale), 0).label("totale"),
        )
        .group_by(Category.nome)
        .order_by(func.sum(SaleItem.subtotale).desc())
    )
    if punto_vendita_id:
        fatturato_categoria_query = fatturato_categoria_query.filter(
            Sale.punto_vendita_id == punto_vendita_id
        )
    fatturato_categoria = [
        {"nome": r.nome, "totale": float(r.totale or 0)}
        for r in fatturato_categoria_query.all()
    ]

    top_prodotti_query = (
        Product.query.join(SaleItem, Product.id == SaleItem.prodotto_id)
        .join(Sale, Sale.id == SaleItem.vendita_id)
        .filter(Sale.data_ora >= data_inizio, Sale.data_ora < data_fine, Sale.stato == "completata")
        .with_entities(
            Product.nome,
            func.sum(SaleItem.quantita).label("pezzi"),
            func.sum(SaleItem.subtotale).label("valore"),
        )
        .group_by(Product.nome)
        .order_by(func.sum(SaleItem.quantita).desc())
    )
    if punto_vendita_id:
        top_prodotti_query = top_prodotti_query.filter(Sale.punto_vendita_id == punto_vendita_id)
    top_prodotti = top_prodotti_query.limit(10).all()

    vendite_prodotto_query = (
        SaleItem.query.join(Sale, Sale.id == SaleItem.vendita_id)
        .filter(
            Sale.data_ora >= data_inizio,
            Sale.data_ora < data_fine,
            Sale.stato == "completata",
        )
        .with_entities(
            SaleItem.prodotto_id.label("prodotto_id"),
            func.sum(SaleItem.quantita).label("pezzi"),
        )
        .group_by(SaleItem.prodotto_id)
    )
    if punto_vendita_id:
        vendite_prodotto_query = vendite_prodotto_query.filter(
            Sale.punto_vendita_id == punto_vendita_id
        )
    vendite_prodotto = vendite_prodotto_query.subquery()
    pezzi_venduti = func.coalesce(vendite_prodotto.c.pezzi, 0)
    low_prodotti = (
        Product.query.outerjoin(
            vendite_prodotto, vendite_prodotto.c.prodotto_id == Product.id
        )
        .filter(Product.attivo.is_(True))
        .with_entities(Product.nome, pezzi_venduti.label("pezzi"))
        .order_by(pezzi_venduti.asc(), Product.nome.asc())
        .limit(10)
        .all()
    )

    pagamenti = (
        vendite_range.with_entities(
            Sale.metodo_pagamento,
            func.count(Sale.id).label("numero"),
            func.sum(Sale.totale_netto).label("totale"),
        )
        .group_by(Sale.metodo_pagamento)
        .order_by(func.count(Sale.id).desc())
        .all()
    )

    return {
        "tot_fatturato": Decimal(str(tot_fatturato or 0)),
        "tot_margine": Decimal(str(tot_margine or 0)),
        "media_scontrino": Decimal(str(media_scontrino or 0)),
        "count_vendite": count_vendite,
        "vendite_giornaliere": vendite_giornaliere,
        "vendite_settimanali": vendite_settimanali,
        "vendite_mensili": vendite_mensili,
        "fatturato_categoria": fatturato_categoria,
        "top_prodotti": top_prodotti,
        "low_prodotti": low_prodotti,
        "metodi_pagamento": pagamenti,
    }


def _periodi_da_giorni(righe):
    """Crea le serie temporali in Python per restare compatibili con SQLite e Postgres."""
    giornaliero = []
    settimanale = defaultdict(Decimal)
    mensile = defaultdict(Decimal)

    for riga in righe:
        giorno = _to_date(riga.giorno)
        totale = Decimal(str(riga.totale or 0))
        giornaliero.append({"giorno": giorno.isoformat(), "totale": float(totale)})
        anno_iso, settimana_iso, _ = giorno.isocalendar()
        settimanale[f"{anno_iso}-W{settimana_iso:02d}"] += totale
        mensile[f"{giorno.year}-{giorno.month:02d}"] += totale

    return (
        giornaliero,
        [{"settimana": key, "totale": float(value)} for key, value in sorted(settimanale.items())],
        [{"mese": key, "totale": float(value)} for key, value in sorted(mensile.items())],
    )


def _to_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _trend_ultimi_sette_giorni(punto_vendita_id: int | None = None):
    oggi, domani = rome_day_bounds_utc()
    inizio = oggi - timedelta(days=6)

    risultati_query = (
        Sale.query.filter(Sale.data_ora >= inizio, Sale.data_ora < oggi + timedelta(days=1), Sale.stato == "completata")
        .with_entities(func.date(Sale.data_ora), func.coalesce(func.sum(Sale.totale_netto), 0))
        .group_by(func.date(Sale.data_ora))
    )
    if punto_vendita_id:
        risultati_query = risultati_query.filter(Sale.punto_vendita_id == punto_vendita_id)
    risultati = risultati_query.all()
    by_date = {str(item[0]): float(item[1]) for item in risultati}

    trend = []
    for i in range(7):
        day = inizio + timedelta(days=i)
        key = day.date().isoformat()
        trend.append({"giorno": key, "totale": by_date.get(key, 0.0)})
    return trend


def _sintesi_magazzino(punto_vendita_id: int | None = None):
    if punto_vendita_id:
        valori = (
            Product.query.join(StoreInventory, StoreInventory.prodotto_id == Product.id)
            .filter(Product.attivo.is_(True), StoreInventory.punto_vendita_id == punto_vendita_id)
            .with_entities(
                func.count(Product.id),
                func.coalesce(func.sum(StoreInventory.quantita_disponibile), 0),
                func.coalesce(func.sum(StoreInventory.quantita_disponibile * Product.prezzo_acquisto), 0),
                func.coalesce(func.sum(StoreInventory.quantita_disponibile * Product.prezzo_vendita), 0),
            )
            .first()
        )
    else:
        valori = Product.query.filter(Product.attivo.is_(True)).with_entities(
        func.count(Product.id),
        func.coalesce(func.sum(Product.quantita_disponibile), 0),
        func.coalesce(func.sum(Product.quantita_disponibile * Product.prezzo_acquisto), 0),
        func.coalesce(func.sum(Product.quantita_disponibile * Product.prezzo_vendita), 0),
        ).first()

    return {
        "numero_prodotti": int(valori[0] or 0),
        "pezzi_totali": int(valori[1] or 0),
        "valore_costo": Decimal(str(valori[2] or 0)),
        "valore_vendita": Decimal(str(valori[3] or 0)),
    }

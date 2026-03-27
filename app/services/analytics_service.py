from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import case, func

from app.models import Category, Product, Sale, SaleItem


def snapshot_dashboard() -> dict:
    oggi = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    domani = oggi + timedelta(days=1)

    vendite_oggi = Sale.query.filter(
        Sale.data_ora >= oggi,
        Sale.data_ora < domani,
        Sale.stato == "completata",
    )

    incasso_oggi = vendite_oggi.with_entities(func.coalesce(func.sum(Sale.totale_netto), 0)).scalar()
    numero_vendite_oggi = vendite_oggi.count()

    pezzi_venduti_oggi = (
        SaleItem.query.join(Sale, SaleItem.vendita_id == Sale.id)
        .filter(Sale.data_ora >= oggi, Sale.data_ora < domani, Sale.stato == "completata")
        .with_entities(func.coalesce(func.sum(SaleItem.quantita), 0))
        .scalar()
    )

    sotto_scorta = Product.query.filter(
        Product.attivo.is_(True),
        Product.quantita_disponibile <= Product.quantita_minima_alert,
    ).order_by(Product.quantita_disponibile.asc())

    prodotto_top = (
        Product.query.join(SaleItem, Product.id == SaleItem.prodotto_id)
        .join(Sale, Sale.id == SaleItem.vendita_id)
        .filter(Sale.data_ora >= oggi, Sale.data_ora < domani, Sale.stato == "completata")
        .with_entities(
            Product.nome,
            func.sum(SaleItem.quantita).label("pezzi"),
        )
        .group_by(Product.nome)
        .order_by(func.sum(SaleItem.quantita).desc())
        .first()
    )

    trend = _trend_ultimi_sette_giorni()
    magazzino = _sintesi_magazzino()

    return {
        "incasso_oggi": Decimal(str(incasso_oggi or 0)),
        "numero_vendite_oggi": numero_vendite_oggi,
        "pezzi_venduti_oggi": int(pezzi_venduti_oggi or 0),
        "sotto_scorta": sotto_scorta.all(),
        "prodotto_top_oggi": prodotto_top,
        "trend_7_giorni": trend,
        "magazzino": magazzino,
    }


def analisi_periodo(data_inizio: datetime, data_fine: datetime) -> dict:
    vendite_range = Sale.query.filter(
        Sale.data_ora >= data_inizio,
        Sale.data_ora < data_fine,
        Sale.stato == "completata",
    )

    tot_fatturato = vendite_range.with_entities(func.coalesce(func.sum(Sale.totale_netto), 0)).scalar()
    tot_margine = vendite_range.with_entities(func.coalesce(func.sum(Sale.margine_stimato), 0)).scalar()
    media_scontrino = vendite_range.with_entities(func.coalesce(func.avg(Sale.totale_netto), 0)).scalar()
    count_vendite = vendite_range.count()

    vendite_giornaliere = (
        vendite_range.with_entities(
            func.date(Sale.data_ora).label("giorno"),
            func.sum(Sale.totale_netto).label("totale"),
        )
        .group_by(func.date(Sale.data_ora))
        .order_by(func.date(Sale.data_ora))
        .all()
    )

    vendite_settimanali = (
        vendite_range.with_entities(
            func.strftime("%Y-W%W", Sale.data_ora).label("settimana"),
            func.sum(Sale.totale_netto).label("totale"),
        )
        .group_by(func.strftime("%Y-W%W", Sale.data_ora))
        .order_by(func.strftime("%Y-W%W", Sale.data_ora))
        .all()
    )

    vendite_mensili = (
        vendite_range.with_entities(
            func.strftime("%Y-%m", Sale.data_ora).label("mese"),
            func.sum(Sale.totale_netto).label("totale"),
        )
        .group_by(func.strftime("%Y-%m", Sale.data_ora))
        .order_by(func.strftime("%Y-%m", Sale.data_ora))
        .all()
    )

    fatturato_categoria = (
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
        .all()
    )

    top_prodotti = (
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
        .limit(10)
        .all()
    )

    low_prodotti = (
        Product.query.outerjoin(SaleItem, Product.id == SaleItem.prodotto_id)
        .outerjoin(
            Sale,
            (Sale.id == SaleItem.vendita_id)
            & (Sale.data_ora >= data_inizio)
            & (Sale.data_ora < data_fine)
            & (Sale.stato == "completata"),
        )
        .with_entities(
            Product.nome,
            func.coalesce(func.sum(case((Sale.id.isnot(None), SaleItem.quantita), else_=0)), 0).label(
                "pezzi"
            ),
        )
        .group_by(Product.nome)
        .order_by("pezzi")
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


def _trend_ultimi_sette_giorni():
    oggi = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    inizio = oggi - timedelta(days=6)

    risultati = (
        Sale.query.filter(Sale.data_ora >= inizio, Sale.data_ora < oggi + timedelta(days=1), Sale.stato == "completata")
        .with_entities(func.date(Sale.data_ora), func.coalesce(func.sum(Sale.totale_netto), 0))
        .group_by(func.date(Sale.data_ora))
        .all()
    )
    by_date = {str(item[0]): float(item[1]) for item in risultati}

    trend = []
    for i in range(7):
        day = inizio + timedelta(days=i)
        key = day.date().isoformat()
        trend.append({"giorno": key, "totale": by_date.get(key, 0.0)})
    return trend


def _sintesi_magazzino():
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

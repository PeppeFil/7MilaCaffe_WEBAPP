from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import Customer, Product, Sale, SaleItem, VatRate
from app.services.audit_service import registra_attivita
from app.services.inventory_service import registra_movimento
from app.utils.parsers import to_decimal, to_int


def crea_vendita(
    operatore_id: int,
    items: list[dict],
    sconto_tipo: str,
    sconto_valore,
    metodo_pagamento: str,
    note_cliente: str = "",
    customer_id=None,
    vat_rate_id=None,
    data_ora: datetime | None = None,
    commit: bool = True,
) -> Sale:
    if not items:
        raise ValueError("Il carrello è vuoto.")

    totale_lordo = Decimal("0.00")
    margine_totale = Decimal("0.00")
    righe_calcolate = []

    for item in items:
        prodotto_id = to_int(item.get("prodotto_id"))
        quantita = to_int(item.get("quantita"))
        if quantita <= 0:
            raise ValueError("Quantità riga non valida.")

        prodotto = Product.query.filter_by(id=prodotto_id, attivo=True).first()
        if not prodotto:
            raise ValueError(f"Prodotto ID {prodotto_id} non trovato o non attivo.")
        if prodotto.quantita_disponibile < quantita:
            raise ValueError(
                f"Stock insufficiente per {prodotto.nome}. "
                f"Disponibile: {prodotto.quantita_disponibile}"
            )

        prezzo_unitario = Decimal(str(prodotto.prezzo_vendita))
        costo_unitario = Decimal(str(prodotto.prezzo_acquisto))
        subtotale = prezzo_unitario * quantita
        margine_riga = (prezzo_unitario - costo_unitario) * quantita

        righe_calcolate.append(
            {
                "prodotto": prodotto,
                "quantita": quantita,
                "prezzo_unitario": prezzo_unitario,
                "costo_unitario": costo_unitario,
                "subtotale": subtotale,
                "margine_riga": margine_riga,
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

    totale_netto = totale_lordo - sconto_importo
    margine_totale = margine_totale - sconto_importo

    customer_id_int = to_int(customer_id, default=0) or None
    if customer_id_int:
        customer = Customer.query.filter_by(id=customer_id_int, attivo=True).first()
        if not customer:
            raise ValueError("Cliente selezionato non valido.")

    vat_rate_id_int = to_int(vat_rate_id, default=0) or None
    aliquota_iva = Decimal("0.00")
    if vat_rate_id_int:
        vat_rate = VatRate.query.filter_by(id=vat_rate_id_int, attiva=True).first()
        if not vat_rate:
            raise ValueError("Aliquota IVA selezionata non valida.")
        aliquota_iva = Decimal(str(vat_rate.aliquota))

    totale_iva = (totale_netto * aliquota_iva) / Decimal("100")

    vendita = Sale(
        data_ora=data_ora or datetime.utcnow(),
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
            costo_unitario_snapshot=r["costo_unitario"],
            margine_riga=r["margine_riga"],
        )
        db.session.add(item)

        registra_movimento(
            prodotto=r["prodotto"],
            tipo_movimento="scarico_vendita",
            quantita=r["quantita"],
            operatore_id=operatore_id,
            motivo="Scarico automatico da vendita",
            riferimento_entita=f"vendita:{vendita.id}",
            data_ora=vendita.data_ora,
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
            data_ora=data_ora or datetime.utcnow(),
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


def query_vendite(filtri: dict):
    query = Sale.query.order_by(Sale.data_ora.desc())

    stato = (filtri.get("stato") or "").strip()
    if stato:
        query = query.filter(Sale.stato == stato)

    data_da = (filtri.get("data_da") or "").strip()
    if data_da:
        try:
            query = query.filter(Sale.data_ora >= datetime.fromisoformat(data_da))
        except ValueError as exc:
            raise ValueError("Data iniziale non valida.") from exc

    data_a = (filtri.get("data_a") or "").strip()
    if data_a:
        try:
            query = query.filter(Sale.data_ora <= datetime.fromisoformat(data_a))
        except ValueError as exc:
            raise ValueError("Data finale non valida.") from exc

    metodo = (filtri.get("metodo_pagamento") or "").strip()
    if metodo:
        query = query.filter(Sale.metodo_pagamento == metodo)

    return query

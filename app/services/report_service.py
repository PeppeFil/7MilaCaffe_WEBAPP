import csv
import io
from datetime import datetime, timedelta

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import func

from app.models import InventoryMovement, Product, Sale, SaleItem, StoreInventory
from app.utils.timezones import rome_day_bounds_utc, utc_to_rome


def csv_vendite_giornaliere(punto_vendita_id: int | None = None) -> str:
    riferimento, fine = rome_day_bounds_utc()

    query = (
        Sale.query.filter(Sale.data_ora >= riferimento, Sale.data_ora < fine)
        .order_by(Sale.data_ora.asc())
    )
    if punto_vendita_id:
        query = query.filter(Sale.punto_vendita_id == punto_vendita_id)
    vendite = query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id_vendita", "data_ora", "totale_lordo", "sconto", "totale_netto", "metodo", "stato"])
    for v in vendite:
        writer.writerow(
            [v.id, v.data_ora.isoformat(), v.totale_lordo, v.sconto_valore, v.totale_netto, v.metodo_pagamento, v.stato]
        )
    return output.getvalue()


def csv_magazzino_attuale(punto_vendita_id: int | None = None) -> str:
    query = Product.query
    if punto_vendita_id:
        query = query.join(StoreInventory, StoreInventory.prodotto_id == Product.id).filter(
            StoreInventory.punto_vendita_id == punto_vendita_id
        )
    prodotti = query.order_by(Product.nome.asc()).all()
    giacenze = {
        row.prodotto_id: row
        for row in StoreInventory.query.filter_by(punto_vendita_id=punto_vendita_id).all()
    } if punto_vendita_id else {}
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "nome", "categoria", "marca", "giacenza", "scorta_minima", "stato"])
    for p in prodotti:
        writer.writerow(
            [
                p.id,
                p.nome,
                p.categoria.nome if p.categoria else "",
                p.brand.nome if p.brand else "",
                giacenze[p.id].quantita_disponibile if p.id in giacenze else p.quantita_disponibile,
                giacenze[p.id].quantita_minima_alert if p.id in giacenze else p.quantita_minima_alert,
                p.stato_disponibilita,
            ]
        )
    return output.getvalue()


def csv_movimenti_magazzino(punto_vendita_id: int | None = None) -> str:
    query = InventoryMovement.query.order_by(InventoryMovement.data_ora.desc())
    if punto_vendita_id:
        query = query.filter(InventoryMovement.punto_vendita_id == punto_vendita_id)
    movimenti = query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "data_ora",
            "tipo_movimento",
            "prodotto",
            "quantita",
            "motivo",
            "riferimento_entita",
            "operatore_id",
        ]
    )
    for m in movimenti:
        writer.writerow(
            [
                m.id,
                m.data_ora.isoformat(),
                m.tipo_movimento,
                m.prodotto.nome if m.prodotto else "",
                m.quantita,
                m.motivo or "",
                m.riferimento_entita or "",
                m.operatore_id,
            ]
        )
    return output.getvalue()


def csv_sotto_scorta(punto_vendita_id: int | None = None) -> str:
    query = Product.query.filter(
        Product.attivo.is_(True),
        Product.quantita_disponibile <= Product.quantita_minima_alert,
    )
    if punto_vendita_id:
        query = (
            Product.query.join(StoreInventory, StoreInventory.prodotto_id == Product.id)
            .filter(
                Product.attivo.is_(True),
                StoreInventory.punto_vendita_id == punto_vendita_id,
                StoreInventory.quantita_disponibile <= StoreInventory.quantita_minima_alert,
            )
        )
    prodotti = query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "nome", "giacenza", "scorta_minima", "categoria", "marca"])
    for p in prodotti:
        writer.writerow(
            [
                p.id,
                p.nome,
                p.quantita_disponibile,
                p.quantita_minima_alert,
                p.categoria.nome if p.categoria else "",
                p.brand.nome if p.brand else "",
            ]
        )
    return output.getvalue()


def csv_prodotti_piu_venduti(punto_vendita_id: int | None = None) -> str:
    query = (
        Product.query.join(SaleItem, Product.id == SaleItem.prodotto_id)
        .join(Sale, Sale.id == SaleItem.vendita_id)
        .filter(Sale.stato == "completata")
        .with_entities(
            Product.nome,
            func.sum(SaleItem.quantita).label("pezzi"),
            func.sum(SaleItem.subtotale).label("valore"),
        )
        .group_by(Product.nome)
        .order_by(func.sum(SaleItem.quantita).desc())
    )
    if punto_vendita_id:
        query = query.filter(Sale.punto_vendita_id == punto_vendita_id)
    records = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["prodotto", "pezzi_venduti", "valore_venduto"])
    for r in records:
        writer.writerow([r.nome, r.pezzi, r.valore])
    return output.getvalue()


def pdf_vendite_giornaliere(data: datetime | None = None, punto_vendita_id: int | None = None) -> bytes:
    riferimento, fine = rome_day_bounds_utc(data)
    query = Sale.query.filter(Sale.data_ora >= riferimento, Sale.data_ora < fine)
    if punto_vendita_id:
        query = query.filter(Sale.punto_vendita_id == punto_vendita_id)
    vendite = query.all()

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 40
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, f"Report vendite giornaliere - {utc_to_rome(riferimento).date().isoformat()}")
    y -= 30

    pdf.setFont("Helvetica", 10)
    totale = 0
    for v in vendite:
        totale += float(v.totale_netto)
        line = (
            f"Vendita #{v.id} | {utc_to_rome(v.data_ora).strftime('%H:%M')} | "
            f"Totale: {v.totale_netto} | Pagamento: {v.metodo_pagamento} | Stato: {v.stato}"
        )
        pdf.drawString(40, y, line[:120])
        y -= 16
        if y < 80:
            pdf.showPage()
            y = height - 50
            pdf.setFont("Helvetica", 10)

    y -= 10
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, y, f"Totale giornata: {totale:.2f} EUR")

    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()

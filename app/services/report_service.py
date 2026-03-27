import csv
import io
from datetime import datetime, timedelta

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import func

from app.models import InventoryMovement, Product, Sale, SaleItem


def csv_vendite_giornaliere(data: datetime | None = None) -> str:
    riferimento = (data or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    fine = riferimento + timedelta(days=1)

    vendite = (
        Sale.query.filter(Sale.data_ora >= riferimento, Sale.data_ora < fine)
        .order_by(Sale.data_ora.asc())
        .all()
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id_vendita", "data_ora", "totale_lordo", "sconto", "totale_netto", "metodo", "stato"])
    for v in vendite:
        writer.writerow(
            [v.id, v.data_ora.isoformat(), v.totale_lordo, v.sconto_valore, v.totale_netto, v.metodo_pagamento, v.stato]
        )
    return output.getvalue()


def csv_magazzino_attuale() -> str:
    prodotti = Product.query.order_by(Product.nome.asc()).all()
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
                p.quantita_disponibile,
                p.quantita_minima_alert,
                p.stato_disponibilita,
            ]
        )
    return output.getvalue()


def csv_movimenti_magazzino() -> str:
    movimenti = InventoryMovement.query.order_by(InventoryMovement.data_ora.desc()).all()
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


def csv_sotto_scorta() -> str:
    prodotti = Product.query.filter(
        Product.attivo.is_(True),
        Product.quantita_disponibile <= Product.quantita_minima_alert,
    ).all()
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


def csv_prodotti_piu_venduti() -> str:
    records = (
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
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["prodotto", "pezzi_venduti", "valore_venduto"])
    for r in records:
        writer.writerow([r.nome, r.pezzi, r.valore])
    return output.getvalue()


def pdf_vendite_giornaliere(data: datetime | None = None) -> bytes:
    riferimento = (data or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    fine = riferimento + timedelta(days=1)
    vendite = Sale.query.filter(Sale.data_ora >= riferimento, Sale.data_ora < fine).all()

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 40
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, f"Report vendite giornaliere - {riferimento.date().isoformat()}")
    y -= 30

    pdf.setFont("Helvetica", 10)
    totale = 0
    for v in vendite:
        totale += float(v.totale_netto)
        line = (
            f"Vendita #{v.id} | {v.data_ora.strftime('%H:%M')} | "
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

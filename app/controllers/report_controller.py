from datetime import datetime

from flask import Blueprint, Response, render_template
from flask_login import login_required

from app.services.report_service import (
    csv_magazzino_attuale,
    csv_movimenti_magazzino,
    csv_prodotti_piu_venduti,
    csv_sotto_scorta,
    csv_vendite_giornaliere,
    pdf_vendite_giornaliere,
)
from app.services.store_service import punto_vendita_corrente


report_bp = Blueprint("report", __name__)


@report_bp.route("/report")
@login_required
def index():
    return render_template("report/index.html")


@report_bp.route("/report/export/<string:nome_report>.csv")
@login_required
def export_csv(nome_report):
    exporters = {
        "vendite_giornaliere": (csv_vendite_giornaliere, "report_vendite_giornaliere.csv"),
        "magazzino_attuale": (csv_magazzino_attuale, "report_magazzino.csv"),
        "movimenti_magazzino": (csv_movimenti_magazzino, "report_movimenti.csv"),
        "sotto_scorta": (csv_sotto_scorta, "report_sotto_scorta.csv"),
        "prodotti_piu_venduti": (csv_prodotti_piu_venduti, "report_top_prodotti.csv"),
    }
    if nome_report not in exporters:
        return Response("Report non trovato.", status=404)

    csv_func, filename = exporters[nome_report]
    punto_vendita = punto_vendita_corrente()
    csv_text = csv_func(punto_vendita.id if punto_vendita else None)
    return Response(
        csv_text,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@report_bp.route("/report/export/vendite_giornaliere.pdf")
@login_required
def export_pdf():
    punto_vendita = punto_vendita_corrente()
    pdf_data = pdf_vendite_giornaliere(datetime.now(), punto_vendita.id if punto_vendita else None)
    return Response(
        pdf_data,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=report_vendite_giornaliere.pdf"},
    )

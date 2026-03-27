from datetime import timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.services.analytics_service import analisi_periodo
from app.utils.parsers import parse_period_filter


analysis_bp = Blueprint("analysis", __name__)


@analysis_bp.route("/analisi")
@login_required
def index():
    periodo = request.args.get("periodo", "ultimi_7")
    data_inizio_raw = request.args.get("data_inizio")
    data_fine_raw = request.args.get("data_fine")

    try:
        data_inizio, data_fine = parse_period_filter(periodo, data_inizio_raw, data_fine_raw)
    except ValueError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("analysis.index", periodo="ultimi_7"))

    data = analisi_periodo(data_inizio, data_fine)

    return render_template(
        "analysis/index.html",
        periodo=periodo,
        data_inizio=data_inizio.date().isoformat(),
        data_fine=(data_fine - timedelta(days=1)).date().isoformat(),
        data=data,
    )

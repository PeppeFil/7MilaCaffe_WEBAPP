from flask import Blueprint, render_template
from flask_login import login_required

from app.services.analytics_service import snapshot_dashboard
from app.services.store_service import punto_vendita_corrente


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def index():
    punto_vendita = punto_vendita_corrente()
    stats = snapshot_dashboard(punto_vendita.id if punto_vendita else None)
    return render_template("dashboard.html", stats=stats)

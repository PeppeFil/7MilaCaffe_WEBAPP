from flask import Blueprint, render_template
from flask_login import login_required

from app.services.analytics_service import snapshot_dashboard


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def index():
    stats = snapshot_dashboard()
    return render_template("dashboard.html", stats=stats)

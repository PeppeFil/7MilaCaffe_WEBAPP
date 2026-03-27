from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.services.auth_service import autentica_utente
from app.utils.security import is_safe_redirect_target


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        utente = autentica_utente(username, password)
        if utente:
            login_user(utente)
            flash("Accesso effettuato con successo.", "success")
            next_page = request.args.get("next")
            if not is_safe_redirect_target(next_page, request.host_url):
                next_page = None
            return redirect(next_page or url_for("dashboard.index"))

        flash("Credenziali non valide.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Sessione terminata.", "info")
    return redirect(url_for("auth.login"))

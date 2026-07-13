import os

from flask import Flask, abort, redirect, request, url_for
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix

from config import config_by_name

from .extensions import db, login_manager, migrate
from .utils.security import get_csrf_token, request_csrf_token, validate_csrf_token


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    cfg_name = config_name or os.getenv("FLASK_CONFIG", "development")
    app.config.from_object(config_by_name.get(cfg_name, config_by_name["development"]))

    if cfg_name == "production":
        if app.config["SECRET_KEY"] == "dev-secret-change-me":
            raise RuntimeError("SECRET_KEY deve essere impostata in produzione.")
        if not app.config["SQLALCHEMY_DATABASE_URI"]:
            raise RuntimeError("DATABASE_URL deve essere impostata in produzione.")
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    _init_extensions(app)
    _register_commands(app)
    _register_blueprints(app)
    _register_routes(app)

    return app


def _init_extensions(app: Flask) -> None:
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db, directory="alembic_migrations")

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"
    login_manager.login_message = "Effettua il login per accedere."

    from .models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))

    @app.before_request
    def protect_from_csrf():
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            if not validate_csrf_token(request_csrf_token(request)):
                abort(400, description="CSRF token non valido.")

    @app.context_processor
    def inject_security_helpers():
        from .services.store_service import punto_vendita_corrente
        from .utils.timezones import utc_to_rome

        return {
            "csrf_token": get_csrf_token,
            "punto_vendita_corrente": punto_vendita_corrente() if current_user.is_authenticated else None,
            "data_roma": utc_to_rome,
        }

    @app.template_filter("roma_datetime")
    def roma_datetime(value, fmt="%d/%m/%Y %H:%M"):
        from .utils.timezones import utc_to_rome

        local_value = utc_to_rome(value)
        return local_value.strftime(fmt) if local_value else "-"


def _register_commands(app: Flask) -> None:
    from .cli import register_commands

    register_commands(app)


def _register_blueprints(app: Flask) -> None:
    from .controllers.analysis_controller import analysis_bp
    from .controllers.auth_controller import auth_bp
    from .controllers.cash_register_controller import cash_bp
    from .controllers.dashboard_controller import dashboard_bp
    from .controllers.inventory_controller import inventory_bp
    from .controllers.product_controller import product_bp
    from .controllers.report_controller import report_bp
    from .controllers.sales_controller import sales_bp
    from .controllers.settings_controller import settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(cash_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(settings_bp)


def _register_routes(app: Flask) -> None:
    @app.route("/")
    def home():
        return redirect(url_for("cash.cassa"))

    @app.get("/healthz")
    def healthcheck():
        return {"status": "ok"}, 200

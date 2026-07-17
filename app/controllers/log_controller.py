from datetime import datetime, time, timedelta, timezone

from flask import Blueprint, render_template, request
from sqlalchemy import func, or_

from app.models import ActivityLog, User
from app.utils.decorators import username_required
from app.utils.parsers import to_int
from app.utils.timezones import ROME_TIMEZONE, utc_now_naive


log_bp = Blueprint("logs", __name__)

ACTION_LABELS = {
    "accesso": "Accesso",
    "uscita": "Uscita",
    "creazione_vendita": "Vendita completata",
    "annullo_vendita": "Vendita annullata",
    "creazione_prodotto": "Prodotto creato",
    "modifica_prodotto": "Prodotto modificato",
    "disattiva_prodotto": "Prodotto disattivato",
    "duplica_prodotto": "Prodotto duplicato",
    "creazione_cliente": "Cliente creato",
    "modifica_cliente": "Cliente modificato",
    "disattiva_cliente": "Cliente disattivato",
    "ripristina_cliente": "Cliente ripristinato",
    "movimento_carico": "Carico magazzino",
    "movimento_scarico_manuale": "Scarico magazzino",
    "movimento_rettifica": "Rettifica magazzino",
    "movimento_reso": "Reso magazzino",
    "movimento_omaggio": "Omaggio",
    "movimento_danneggiato": "Prodotto danneggiato",
}


@log_bp.route("/log")
@username_required("admin")
def index():
    query = ActivityLog.query.join(ActivityLog.utente)
    search = (request.args.get("q") or "").strip()
    azione = (request.args.get("azione") or "").strip()
    utente_id = to_int(request.args.get("utente_id"), default=0)
    data_da = _parse_local_date(request.args.get("data_da"), end_of_day=False)
    data_a = _parse_local_date(request.args.get("data_a"), end_of_day=True)

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                ActivityLog.azione.ilike(like),
                ActivityLog.entita_tipo.ilike(like),
                ActivityLog.entita_id.ilike(like),
                ActivityLog.dettagli.ilike(like),
                User.username.ilike(like),
            )
        )
    if azione:
        query = query.filter(ActivityLog.azione == azione)
    if utente_id:
        query = query.filter(ActivityLog.utente_id == utente_id)
    if data_da:
        query = query.filter(ActivityLog.data_ora >= data_da)
    if data_a:
        query = query.filter(ActivityLog.data_ora <= data_a)

    page = max(1, to_int(request.args.get("page"), default=1))
    per_page = min(100, max(10, to_int(request.args.get("per_page"), default=25)))
    pagination = query.order_by(ActivityLog.data_ora.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )

    today_start = datetime.combine(
        datetime.now(ROME_TIMEZONE).date(), time.min, tzinfo=ROME_TIMEZONE
    ).astimezone(timezone.utc).replace(tzinfo=None)
    total_logs = ActivityLog.query.count()
    today_logs = ActivityLog.query.filter(ActivityLog.data_ora >= today_start).count()
    active_users = (
        ActivityLog.query.filter(ActivityLog.data_ora >= utc_now_naive() - timedelta(days=30))
        .with_entities(func.count(func.distinct(ActivityLog.utente_id)))
        .scalar()
        or 0
    )
    action_types = ActivityLog.query.with_entities(func.count(func.distinct(ActivityLog.azione))).scalar() or 0

    azioni = [row[0] for row in ActivityLog.query.with_entities(ActivityLog.azione).distinct().order_by(ActivityLog.azione)]
    utenti = User.query.order_by(User.username.asc()).all()
    return render_template(
        "logs/index.html",
        logs=pagination.items,
        pagination=pagination,
        total_logs=total_logs,
        today_logs=today_logs,
        active_users=active_users,
        action_types=action_types,
        azioni=azioni,
        utenti=utenti,
        action_labels=ACTION_LABELS,
        filters=request.args,
        per_page=per_page,
    )


def _parse_local_date(raw_value: str | None, end_of_day: bool) -> datetime | None:
    if not raw_value:
        return None
    try:
        value = datetime.strptime(raw_value, "%Y-%m-%d").date()
    except ValueError:
        return None
    local_time = time.max if end_of_day else time.min
    return datetime.combine(value, local_time, tzinfo=ROME_TIMEZONE).astimezone(timezone.utc).replace(
        tzinfo=None
    )

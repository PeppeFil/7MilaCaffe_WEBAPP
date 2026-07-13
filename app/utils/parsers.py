from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation


def to_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def to_decimal(value, default: Decimal = Decimal("0.00")) -> Decimal:
    try:
        if value is None or value == "":
            return default
        return Decimal(str(value))
    except (TypeError, InvalidOperation):
        return default


def parse_period_filter(period: str, start_date: str | None, end_date: str | None):
    now = rome_now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == "oggi":
        return _rome_to_utc(today), _rome_to_utc(today + timedelta(days=1))
    if period == "ieri":
        return _rome_to_utc(today - timedelta(days=1)), _rome_to_utc(today)
    if period == "ultimi_7":
        return _rome_to_utc(today - timedelta(days=6)), _rome_to_utc(today + timedelta(days=1))
    if period == "ultimi_30":
        return _rome_to_utc(today - timedelta(days=29)), _rome_to_utc(today + timedelta(days=1))
    if period == "mese_corrente":
        month_start = today.replace(day=1)
        return _rome_to_utc(month_start), _rome_to_utc(today + timedelta(days=1))

    if start_date and end_date:
        try:
            custom_start = datetime.fromisoformat(start_date).replace(
                hour=0, minute=0, second=0, microsecond=0, tzinfo=ROME_TIMEZONE
            )
            custom_end = datetime.fromisoformat(end_date).replace(
                hour=0, minute=0, second=0, microsecond=0, tzinfo=ROME_TIMEZONE
            ) + timedelta(days=1)
        except ValueError as exc:
            raise ValueError("Intervallo date non valido.") from exc

        if custom_end <= custom_start:
            raise ValueError("L'intervallo date deve avere una fine successiva all'inizio.")
        return _rome_to_utc(custom_start), _rome_to_utc(custom_end)

    return _rome_to_utc(today - timedelta(days=6)), _rome_to_utc(today + timedelta(days=1))


def _rome_to_utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(tzinfo=None)
from app.utils.timezones import ROME_TIMEZONE, rome_now

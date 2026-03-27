from datetime import datetime, timedelta
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
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == "oggi":
        return today, today + timedelta(days=1)
    if period == "ieri":
        return today - timedelta(days=1), today
    if period == "ultimi_7":
        return today - timedelta(days=6), today + timedelta(days=1)
    if period == "ultimi_30":
        return today - timedelta(days=29), today + timedelta(days=1)
    if period == "mese_corrente":
        month_start = today.replace(day=1)
        return month_start, today + timedelta(days=1)

    if start_date and end_date:
        try:
            custom_start = datetime.fromisoformat(start_date).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            custom_end = datetime.fromisoformat(end_date).replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + timedelta(days=1)
        except ValueError as exc:
            raise ValueError("Intervallo date non valido.") from exc

        if custom_end <= custom_start:
            raise ValueError("L'intervallo date deve avere una fine successiva all'inizio.")
        return custom_start, custom_end

    return today - timedelta(days=6), today + timedelta(days=1)

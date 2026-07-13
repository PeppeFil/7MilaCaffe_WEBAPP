from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


ROME_TIMEZONE = ZoneInfo("Europe/Rome")


def utc_now_naive() -> datetime:
    """Timestamp UTC senza timezone, coerente con le colonne esistenti."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def rome_now() -> datetime:
    return datetime.now(ROME_TIMEZONE)


def utc_to_rome(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc).astimezone(ROME_TIMEZONE)


def rome_midnight_to_utc_naive(value: datetime) -> datetime:
    local_midnight = value.astimezone(ROME_TIMEZONE).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return local_midnight.astimezone(timezone.utc).replace(tzinfo=None)


def rome_day_bounds_utc(value: datetime | None = None) -> tuple[datetime, datetime]:
    local_start = (value or rome_now()).astimezone(ROME_TIMEZONE).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    local_end = local_start + timedelta(days=1)
    return (
        local_start.astimezone(timezone.utc).replace(tzinfo=None),
        local_end.astimezone(timezone.utc).replace(tzinfo=None),
    )

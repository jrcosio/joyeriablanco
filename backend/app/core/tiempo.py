"""Hora actual con zona (UTC). La presentación en hora peninsular se hace en los bordes."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def ahora() -> datetime:
    return datetime.now(UTC)


def hoy() -> date:
    """Fecha de hoy en hora de España peninsular: fechas de expedición y cambio de año (002)."""
    return ahora().astimezone(ZoneInfo(get_settings().zona_horaria)).date()

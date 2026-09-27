"""Hora actual con zona (UTC). La presentación en hora peninsular se hace en los bordes."""

from datetime import UTC, datetime


def ahora() -> datetime:
    return datetime.now(UTC)

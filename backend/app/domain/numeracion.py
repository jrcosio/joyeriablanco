"""Numeración de facturas: `FAC-AAAA-NNNN` y `REC-AAAA-NNNN` (constitución 2.2.0, R-7).

`AAAA` es el año natural de la fecha de expedición y `NNNN` un correlativo de al menos cuatro
cifras que crece sin truncar a partir de 10.000 (FR-006, FR-009). La asignación concurrente está
en `repositories/contadores.py`.
"""

import re
from datetime import date
from typing import Final

from app.domain.tipos import Serie

_FORMATO: Final = re.compile(r"(FAC|REC)-([0-9]{4})-([0-9]{4,})")
# F-3 §3.1.3.1: «solo puede contener caracteres ASCII del 32 a 126 (…), no permitiéndose (…)
# " (ASCII 34) ' (ASCII 39) < (ASCII 60) > (ASCII 62) = (ASCII 61)». F-1: alfanumérico (60).
_PROHIBIDOS: Final = frozenset("\"'<>=")
LONGITUD_MAXIMA: Final = 60


def format_num_serie(serie: Serie, anio: int, numero: int) -> str:
    if numero <= 0:
        msg = "El número de factura debe ser mayor que cero"
        raise ValueError(msg)
    return f"{serie.value}-{anio:04d}-{numero:04d}"


def year_of(fecha_expedicion: date) -> int:
    return fecha_expedicion.year


def parse_num_serie(num_serie: str) -> tuple[Serie, int, int]:
    coincidencia = _FORMATO.fullmatch(num_serie)
    if coincidencia is None:
        msg = f"Número de factura con formato no válido: {num_serie!r}"
        raise ValueError(msg)
    serie, anio, numero = coincidencia.groups()
    return Serie(serie), int(anio), int(numero)


def validate_num_serie(num_serie: str) -> str | None:
    """Motivo de rechazo según F-3 y F-1, o `None` si es válido."""
    if len(num_serie) > LONGITUD_MAXIMA:
        return f"El número no puede superar {LONGITUD_MAXIMA} caracteres."
    if any(not 32 <= ord(c) <= 126 or c in _PROHIBIDOS for c in num_serie):
        return "El número contiene caracteres no permitidos."
    return None

"""Código postal español → provincia (FR-028).

Orden de 23/01/1984 (BOE-A-1984-3487), art. 2: «los dos primeros identifican la provincia según
el código geográfico nacional»; Orden de 27/09/1995 (BOE-A-1995-21835): Ceuta 51 y Melilla 52.
La equivalencia con los códigos INE (01–52) es una interpretación documentada (research R-20.3).
"""

import re
from typing import Final

_FORMATO: Final = re.compile(r"[0-9]{5}")
PRIMERA_PROVINCIA: Final = 1
ULTIMA_PROVINCIA: Final = 52


def provincia_from_codigo_postal(codigo_postal: str) -> str:
    """Devuelve el código INE de la provincia o lanza `ValueError` con el motivo."""
    if not _FORMATO.fullmatch(codigo_postal):
        msg = "El código postal debe tener 5 dígitos."
        raise ValueError(msg)
    provincia = codigo_postal[:2]
    if not PRIMERA_PROVINCIA <= int(provincia) <= ULTIMA_PROVINCIA:
        msg = "El código postal no corresponde a ninguna provincia."
        raise ValueError(msg)
    return provincia

"""Contacto: reglas de teléfono, correo y web, y el pie de factura (001 FR-055; 003 FR-024).

La regla del teléfono es la de los clientes de 001 (FR-055) y la comparten los clientes y la
configuración de facturación. El contacto y el pie de la joyería no son datos fiscales: se imprimen
en las facturas con los valores vigentes (003, FR-025, research R-9).
"""

import re
from typing import Final

from email_validator import EmailNotValidError, validate_email

_TELEFONO: Final = re.compile(r"[0-9 +()\-]+")
MIN_DIGITOS_TELEFONO: Final = 6
# Un dominio con al menos un punto, con `http(s)://` opcional y una ruta opcional.
_WEB: Final = re.compile(
    r"(https?://)?[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+(?:/\S*)?",
    re.IGNORECASE,
)


def validate_telefono(telefono: str) -> str | None:
    """Motivo por el que el teléfono no es válido, o `None`."""
    if not _TELEFONO.fullmatch(telefono):
        return "Teléfono no válido: solo dígitos, espacios, +, paréntesis y guiones."
    if sum(c.isdigit() for c in telefono) < MIN_DIGITOS_TELEFONO:
        return "Debe tener al menos 6 dígitos."
    return None


def validate_correo(correo: str) -> str | None:
    try:
        validate_email(correo, check_deliverability=False)
    except EmailNotValidError:
        return "Correo electrónico no válido."
    return None


def validate_web(web: str) -> str | None:
    if not _WEB.fullmatch(web):
        return "Escribe un dominio (joyeriablanco.es) o una dirección que empiece por https://."
    return None


def normalize_pie(texto: str) -> str | None:
    """Saltos de línea `\\n` y sin espacios ni líneas vacías en los extremos; vacío es «sin pie»."""
    normalizado = texto.replace("\r\n", "\n").replace("\r", "\n").strip()
    return normalizado or None

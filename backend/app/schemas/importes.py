"""Importes y cantidades en la API: SIEMPRE texto decimal, nunca número JSON (research R-10).

Constitución II: `float` está prohibido «en cualquier punto de la cadena, incluida la
serialización JSON». La entrada solo admite cadenas (un número JSON ya habría pasado por un
`float` al decodificarse) y la salida serializa `Decimal` como cadena con dos decimales.
"""

import re
from collections.abc import Callable
from decimal import Decimal
from typing import Annotated, Final

from pydantic import BeforeValidator, PlainSerializer, WithJsonSchema

PATRON_IMPORTE: Final = r"^[0-9]{1,10}(\.[0-9]{1,2})?$"
PATRON_CANTIDAD: Final = r"^[0-9]{1,5}(\.[0-9]{1,2})?$"
PATRON_TIPO_IVA: Final = r"^[0-9]{1,2}(\.[0-9]{1,2})?$"
PATRON_IMPORTE_SALIDA: Final = r"^-?[0-9]{1,10}\.[0-9]{2}$"
_CENTIMO: Final = Decimal("0.01")


def _texto_decimal(patron: str, *, positivo: bool = False) -> Callable[[object], Decimal]:
    compilado = re.compile(patron)

    def validar(valor: object) -> Decimal:
        if isinstance(valor, Decimal):  # uso interno (servicios y tests), nunca desde JSON
            texto = format(valor, "f")
        elif isinstance(valor, str):
            texto = valor
        else:
            msg = 'Debe enviarse como texto decimal con punto, por ejemplo "12.50".'
            raise ValueError(msg)
        if not compilado.fullmatch(texto):
            msg = "Formato no válido: número con punto decimal y como mucho dos decimales."
            raise ValueError(msg)
        numero = Decimal(texto)
        if positivo and numero <= 0:
            msg = "Debe ser mayor que cero."
            raise ValueError(msg)
        return numero

    return validar


def _dos_decimales(valor: Decimal) -> str:
    return format(valor.quantize(_CENTIMO), "f")


Importe = Annotated[
    Decimal,
    BeforeValidator(_texto_decimal(PATRON_IMPORTE)),
    WithJsonSchema({"type": "string", "pattern": PATRON_IMPORTE, "examples": ["1200.00"]}),
]
Cantidad = Annotated[
    Decimal,
    BeforeValidator(_texto_decimal(PATRON_CANTIDAD, positivo=True)),
    WithJsonSchema({"type": "string", "pattern": PATRON_CANTIDAD, "examples": ["2", "1.50"]}),
]
TipoIvaEntrada = Annotated[
    Decimal,
    BeforeValidator(_texto_decimal(PATRON_TIPO_IVA)),
    WithJsonSchema({"type": "string", "pattern": PATRON_TIPO_IVA, "examples": ["21.00"]}),
]
ImporteSalida = Annotated[
    Decimal,
    PlainSerializer(_dos_decimales, return_type=str),
    WithJsonSchema({"type": "string", "pattern": PATRON_IMPORTE_SALIDA, "examples": ["1290.00"]}),
]
TipoIvaSalida = Annotated[
    Decimal,
    PlainSerializer(_dos_decimales, return_type=str),
    WithJsonSchema({"type": "string", "pattern": PATRON_TIPO_IVA, "examples": ["21.00"]}),
]
CantidadSalida = Annotated[
    Decimal,
    PlainSerializer(_dos_decimales, return_type=str),
    WithJsonSchema({"type": "string", "examples": ["2.00"]}),
]

"""QR tributario de la factura (003, FR-014 a FR-016; research R-1 y R-2).

Fuente única (constitución IV): F-12, AEAT, «Detalle de las especificaciones técnicas del código
QR de la factura y de la URL del servicio de cotejo o remisión de información por parte del
receptor de la factura», v0.5.0 (10/12/2025), SHA-256
f86b3c260d8a4963dbc18c5007732b53199156c5d1db63242e68db71501b49eb; y F-10, Orden HAC/1177/2024,
arts. 20 y 21.

- §5: cuatro direcciones base según la modalidad (facturas verificables o no) y el entorno.
- §6: solo cuatro parámetros, en este orden: `nif` (9), `numserie` (hasta 60, ASCII 32-126),
  `fecha` (DD-MM-AAAA) e `importe` (punto decimal, hasta 12 cifras enteras y 2 decimales).
- §4: «URL encoding» en UTF-8.
- §7: `idioma` y `formato` son del servicio de cotejo; `formato` nunca va en el QR.
- F-10, art. 21.1: ISO/IEC 18004 (2015 según F-12 §2) con nivel M de corrección de errores.
"""

import re
from decimal import Decimal
from typing import Final
from urllib.parse import quote, urlencode

import segno

from app.domain.huella import format_amount
from app.domain.tipos import EntornoAeat, Modalidad

BASES: Final[dict[tuple[Modalidad, EntornoAeat], str]] = {
    (Modalidad.VERIFACTU, EntornoAeat.PRUEBAS): "https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR",
    (Modalidad.NO_VERIFACTU, EntornoAeat.PRUEBAS): (
        "https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQRNoVerifactu"
    ),
    (Modalidad.VERIFACTU, EntornoAeat.PRODUCCION): (
        "https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR"
    ),
    (Modalidad.NO_VERIFACTU, EntornoAeat.PRODUCCION): (
        "https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQRNoVerifactu"
    ),
}

# Frase de F-6, art. 6.5.b y F-10, art. 20.1.b. Solo en VERI*FACTU; se usa la larga
# (Clarifications de la spec, FR-015).
FRASE_VERIFACTU: Final = "Factura verificable en la sede electrónica de la AEAT"

_ASCII_IMPRIMIBLE: Final = re.compile(r"[\x20-\x7e]+")
_FECHA: Final = re.compile(r"\d{2}-\d{2}-\d{4}")
LONGITUD_NIF: Final = 9
MAX_NUMSERIE: Final = 60
MAX_CIFRAS_ENTERAS: Final = 12


def _exigir_ascii(nombre: str, valor: str) -> None:
    if not _ASCII_IMPRIMIBLE.fullmatch(valor):
        msg = f"El parámetro {nombre} solo admite caracteres ASCII de 32 a 126 (F-12 §4)"
        raise ValueError(msg)


def build_cotejo_url(
    modalidad: Modalidad,
    entorno: EntornoAeat,
    *,
    nif: str,
    num_serie: str,
    fecha_expedicion: str,
    importe_total: Decimal,
) -> str:
    """Dirección del QR con los valores del registro de alta (R-1).

    Un valor fuera de formato es un fallo interno (`ValueError`): los datos del registro ya se
    validaron al emitir.
    """
    _exigir_ascii("nif", nif)
    _exigir_ascii("numserie", num_serie)
    if len(nif) != LONGITUD_NIF:
        msg = f"El NIF del QR tiene {LONGITUD_NIF} caracteres (F-12 §6)"
        raise ValueError(msg)
    if len(num_serie) > MAX_NUMSERIE:
        msg = f"El número de serie del QR tiene como máximo {MAX_NUMSERIE} caracteres (F-12 §6)"
        raise ValueError(msg)
    if not _FECHA.fullmatch(fecha_expedicion):
        msg = "La fecha del QR va en formato DD-MM-AAAA (F-12 §6)"
        raise ValueError(msg)
    importe = format_amount(importe_total)
    if len(importe.lstrip("-").split(".")[0]) > MAX_CIFRAS_ENTERAS:
        msg = f"El importe del QR tiene como máximo {MAX_CIFRAS_ENTERAS} cifras enteras (F-12 §6)"
        raise ValueError(msg)
    parametros = (
        ("nif", nif),
        ("numserie", num_serie),
        ("fecha", fecha_expedicion),
        ("importe", importe),
    )
    return f"{BASES[(modalidad, entorno)]}?{urlencode(parametros, quote_via=quote)}"


def qr_simbolo(url: str) -> segno.QRCode:
    """Símbolo QR de modelo 2 con nivel M fijo: sin `boost_error`, que subiría a Q o H."""
    return segno.make(url, error="m", micro=False, boost_error=False)


def qr_svg(url: str, *, color: str) -> str:
    """SVG vectorial en línea, sin tamaño fijo (lo pone el CSS) y sin margen propio (R-2)."""
    svg: str = qr_simbolo(url).svg_inline(
        dark=color, light=None, border=0, omitsize=True, svgclass="qr-svg", lineclass=None
    )
    return svg

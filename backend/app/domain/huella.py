"""Huella SHA-256 de los registros de facturación (research R-2).

Fuente única (constitución IV): F-2, AEAT, «Detalle de las especificaciones técnicas para
generación de la huella o hash de los registros de facturación», v0.1.2 (27/08/2024).
- Algoritmo SHA-256 (`TipoHuella` 01, lista L12), entrada en UTF-8 y salida hexadecimal en
  mayúsculas de 64 caracteres (pp. 4, 7 y 9).
- Cadena `nombre=valor&nombre=valor…` en el orden de p. 5, sin `&` final, con los espacios
  extremos de cada valor recortados, y `nombre=` para un campo vacío (pp. 6–7).
- Los importes siempre con dos decimales y punto: representación canónica elegida en R-2 para que
  la huella sea reproducible («123.10», nunca «123.1»).
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Final
from zoneinfo import ZoneInfo

ZONA_REGISTRO: Final = ZoneInfo("Europe/Madrid")
_CENTIMO: Final = Decimal("0.01")


def format_amount(valor: Decimal) -> str:
    if valor != valor.quantize(_CENTIMO):
        msg = f"El importe {valor} debe tener como mucho dos decimales"
        raise ValueError(msg)
    return format(valor.quantize(_CENTIMO), "f")


def format_date(fecha: date) -> str:
    """Formato `dd-mm-yyyy` de F-1."""
    return fecha.strftime("%d-%m-%Y")


def format_timestamp(momento: datetime) -> str:
    """`YYYY-MM-DDThh:mm:ssTZD` (ISO 8601) en hora de Madrid con su desfase (F-1, fila 56)."""
    return momento.astimezone(ZONA_REGISTRO).isoformat(timespec="seconds")


def _cadena(pares: tuple[tuple[str, str], ...]) -> str:
    return "&".join(f"{nombre}={valor.strip()}" for nombre, valor in pares)


@dataclass(frozen=True, slots=True)
class CamposHuellaAlta:
    """Campos del alta en el orden de F-2, p. 5, ya formateados como en el registro."""

    id_emisor: str
    num_serie: str
    fecha_expedicion: str
    tipo_factura: str
    cuota_total: str
    importe_total: str
    huella_anterior: str
    fecha_hora_huso_gen: str

    def cadena(self) -> str:
        return _cadena(
            (
                ("IDEmisorFactura", self.id_emisor),
                ("NumSerieFactura", self.num_serie),
                ("FechaExpedicionFactura", self.fecha_expedicion),
                ("TipoFactura", self.tipo_factura),
                ("CuotaTotal", self.cuota_total),
                ("ImporteTotal", self.importe_total),
                ("Huella", self.huella_anterior),
                ("FechaHoraHusoGenRegistro", self.fecha_hora_huso_gen),
            )
        )


@dataclass(frozen=True, slots=True)
class CamposHuellaAnulacion:
    """Campos de la anulación en el orden de F-2, p. 5."""

    id_emisor: str
    num_serie: str
    fecha_expedicion: str
    huella_anterior: str
    fecha_hora_huso_gen: str

    def cadena(self) -> str:
        return _cadena(
            (
                ("IDEmisorFacturaAnulada", self.id_emisor),
                ("NumSerieFacturaAnulada", self.num_serie),
                ("FechaExpedicionFacturaAnulada", self.fecha_expedicion),
                ("Huella", self.huella_anterior),
                ("FechaHoraHusoGenRegistro", self.fecha_hora_huso_gen),
            )
        )


def compute_huella(cadena: str) -> str:
    return sha256(cadena.encode("utf-8")).hexdigest().upper()

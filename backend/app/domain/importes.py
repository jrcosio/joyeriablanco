"""Importes, redondeo y tipos de IVA: la política ÚNICA del sistema (constitución II, FR-015).

Research R-10:
- `importe_linea = redondear(unidades × precio_unitario)`.
- `base_tipo = Σ importe_linea` de las líneas de ese tipo.
- `cuota_tipo = redondear(base_tipo × tipo / 100)`.
- `cuota_total = Σ cuota_tipo`; `importe_total = Σ (base_tipo + cuota_tipo)`.
- `redondear`: al céntimo, con el medio alejándose de cero (`ROUND_HALF_UP` de `decimal`).

Factura de oro de inversión (ajuste de cierre, R-21): las líneas van sin tipo (`tipo_iva=None`) y
su detalle, exento, lleva cuota 0. Solo se redondea el importe de cada línea, como siempre.

Queda dentro de las tolerancias de F-3 («Validaciones y errores VERI*FACTU» v1.2.2, §15.7 y
puntos 16–17): la cuota es exacta al céntimo y los totales son sumas exactas del desglose.

Todo es `Decimal`. Mezclar un `float` provoca `TypeError` en la propia aritmética de `decimal`.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

CENTIMO: Final = Decimal("0.01")
CIEN: Final = Decimal(100)

# Límites (research R-10). Los importes de F-1 son Decimal(12,2).
MAX_IMPORTE: Final = Decimal("9999999999.99")
MAX_UNIDADES: Final = Decimal("99999.99")
MAX_PRECIO: Final = Decimal("99999999.99")
MAX_LINEAS: Final = 100


class ImporteFueraDeRango(ValueError):
    """Algún total supera el máximo de `Decimal(12,2)` de F-1."""


def round_amount(valor: Decimal) -> Decimal:
    return valor.quantize(CENTIMO, rounding=ROUND_HALF_UP)


def line_amount(unidades: Decimal, precio_unitario: Decimal) -> Decimal:
    return round_amount(unidades * precio_unitario)


@dataclass(frozen=True, slots=True)
class LineaCalculo:
    unidades: Decimal
    precio_unitario: Decimal
    tipo_iva: Decimal | None  # None: exenta, sin tipo ni cuota (oro de inversión, R-21)


@dataclass(frozen=True, slots=True)
class DesgloseTipo:
    """Base y cuota agregadas de un tipo de IVA (la «cabecera por tipo» de la constitución II).

    `tipo_iva=None` es el detalle exento, con cuota 0 (R-21).
    """

    tipo_iva: Decimal | None
    base: Decimal
    cuota: Decimal


@dataclass(frozen=True, slots=True)
class Totales:
    desglose: tuple[DesgloseTipo, ...]
    base_total: Decimal
    cuota_total: Decimal
    importe_total: Decimal


def _tipo(tipo_iva: Decimal | None) -> Decimal | None:
    return None if tipo_iva is None else tipo_iva.quantize(CENTIMO)


def _cuota(base: Decimal, tipo: Decimal | None) -> Decimal:
    return Decimal("0.00") if tipo is None else round_amount(base * tipo / CIEN)


def _orden(tipo: Decimal | None) -> tuple[bool, Decimal]:
    """Los sujetos de menor a mayor tipo y, al final, el exento."""
    return (tipo is None, tipo or Decimal(0))


def compute_totals(
    lineas: Sequence[LineaCalculo], *, tipo_iva_por_defecto: Decimal | None
) -> Totales:
    """Desglose por tipo (ordenado de menor a mayor, el exento al final) y totales.

    Sin líneas (devolución total, research R-4) hay un único detalle a cero al tipo por defecto,
    o exento si es `None`: F-1 exige entre 1 y 12 detalles de desglose.
    """
    bases: dict[Decimal | None, Decimal] = {}
    for linea in lineas:
        tipo = _tipo(linea.tipo_iva)
        bases[tipo] = bases.get(tipo, Decimal("0.00")) + line_amount(
            linea.unidades, linea.precio_unitario
        )
    if not bases:
        bases[_tipo(tipo_iva_por_defecto)] = Decimal("0.00")

    desglose = tuple(
        DesgloseTipo(tipo_iva=tipo, base=round_amount(base), cuota=_cuota(base, tipo))
        for tipo, base in sorted(bases.items(), key=lambda par: _orden(par[0]))
    )
    base_total = sum((d.base for d in desglose), Decimal("0.00"))
    cuota_total = sum((d.cuota for d in desglose), Decimal("0.00"))
    totales = Totales(
        desglose=desglose,
        base_total=base_total,
        cuota_total=cuota_total,
        importe_total=base_total + cuota_total,
    )
    if max(abs(totales.importe_total), *(abs(d.base) for d in desglose)) > MAX_IMPORTE:
        msg = "El importe supera el máximo admitido (9.999.999.999,99 €)."
        raise ImporteFueraDeRango(msg)
    return totales


# ------------------------------------------------ tipos de IVA (F-3): lista informativa


@dataclass(frozen=True, slots=True)
class VentanaTipo:
    tipo: Decimal
    desde: date | None = None
    hasta: date | None = None

    def admite(self, fecha: date) -> bool:
        return (self.desde is None or fecha >= self.desde) and (
            self.hasta is None or fecha <= self.hasta
        )


# F-3 §15.1 (p. 10), con Impuesto 01 y CalificacionOperacion S1: «Solo se permiten
# TipoImpositivo = 0; 2; 4; 5; 7,5; 10 y 21». El 5 solo si «FechaOperacion (FechaExpedicionFactura
# … si no se informa FechaOperacion) ≥ 1 de julio de 2022 y ≤ 30 de septiembre de 2024»; el 2 y
# el 7,5 solo del 1 de octubre al 31 de diciembre de 2024.
# Desde el ajuste de cierre (research R-20) la lista es INFORMATIVA: Configuración admite
# cualquier tipo de 0 a 99,99 y pide confirmación si no está aquí para la fecha actual; al emitir
# ya no se revalida. Si la ley cambia, conviene actualizar la tabla para que el aviso no salte.
TIPOS_IVA_S1: Final = (
    VentanaTipo(Decimal(0)),
    VentanaTipo(Decimal(2), date(2024, 10, 1), date(2024, 12, 31)),
    VentanaTipo(Decimal(4)),
    VentanaTipo(Decimal(5), date(2022, 7, 1), date(2024, 9, 30)),
    VentanaTipo(Decimal("7.5"), date(2024, 10, 1), date(2024, 12, 31)),
    VentanaTipo(Decimal(10)),
    VentanaTipo(Decimal(21)),
)


def is_rate_allowed(tipo_iva: Decimal, fecha: date) -> bool:
    """`fecha` es la de la operación o, si no la hay, la de expedición (F-3 §15.1)."""
    return any(v.tipo == tipo_iva and v.admite(fecha) for v in TIPOS_IVA_S1)


def allowed_rates(fecha: date) -> tuple[Decimal, ...]:
    return tuple(v.tipo for v in TIPOS_IVA_S1 if v.admite(fecha))

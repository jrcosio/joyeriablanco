"""Reglas puras de los presupuestos (feature 005; FR-001, FR-009; research R-3).

Sin acceso a la BD ni a la hora del sistema: quien llama pasa la fecha de hoy, calculada en la zona
de la aplicación (`core/tiempo.hoy`). Así la caducidad no depende del huso del servidor de la BD.
"""

from datetime import date, timedelta
from typing import Final

from app.domain.tipos import EstadoPresupuesto

VALIDEZ_MINIMA: Final = 1
VALIDEZ_MAXIMA: Final = 365


def validez_por_defecto(fecha: date, dias: int) -> date:
    """«Válido hasta» propuesto: la fecha del presupuesto más la validez de Configuración."""
    if not VALIDEZ_MINIMA <= dias <= VALIDEZ_MAXIMA:
        msg = f"La validez debe estar entre {VALIDEZ_MINIMA} y {VALIDEZ_MAXIMA} días"
        raise ValueError(msg)
    return fecha + timedelta(days=dias)


def estado_visible(
    estado: EstadoPresupuesto | str, valido_hasta: date, hoy: date
) -> EstadoPresupuesto:
    """Estado que ve el usuario a partir del guardado (`estado_presupuesto()` en la BD).

    Un pendiente se muestra caducado desde el día siguiente a su validez. «En facturación»
    prevalece sobre la caducidad (FR-001), y los cierres son terminales.
    """
    guardado = EstadoPresupuesto(estado)
    if guardado is EstadoPresupuesto.PENDIENTE and valido_hasta < hoy:
        return EstadoPresupuesto.CADUCADO
    return guardado

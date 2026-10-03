"""Validez por defecto y estado visible de un presupuesto (005: FR-001, FR-009; research R-3)."""

from datetime import date

import pytest

from app.domain.presupuestos import estado_visible, validez_por_defecto
from app.domain.tipos import EstadoPresupuesto as E


@pytest.mark.parametrize(
    ("fecha", "dias", "esperada"),
    [
        (date(2026, 10, 2), 30, date(2026, 11, 1)),
        (date(2026, 1, 31), 1, date(2026, 2, 1)),  # cambio de mes
        (date(2026, 12, 15), 30, date(2027, 1, 14)),  # cambio de año
        (date(2028, 2, 28), 1, date(2028, 2, 29)),  # bisiesto
    ],
)
def test_validez_por_defecto(fecha: date, dias: int, esperada: date) -> None:
    assert validez_por_defecto(fecha, dias) == esperada


@pytest.mark.parametrize("dias", [0, -1, 366])
def test_validez_fuera_de_rango(dias: int) -> None:
    with pytest.raises(ValueError, match="entre 1 y 365"):
        validez_por_defecto(date(2026, 10, 2), dias)


HOY = date(2026, 10, 2)


def test_pendiente_con_la_validez_vencida_se_muestra_caducado() -> None:
    assert estado_visible(E.PENDIENTE, date(2026, 10, 1), HOY) is E.CADUCADO


def test_el_ultimo_dia_de_validez_sigue_pendiente() -> None:
    assert estado_visible(E.PENDIENTE, HOY, HOY) is E.PENDIENTE


def test_en_facturacion_prevalece_sobre_la_caducidad() -> None:
    assert estado_visible(E.EN_FACTURACION, date(2026, 9, 1), HOY) is E.EN_FACTURACION


@pytest.mark.parametrize("estado", [E.CONVERTIDO, E.SUSTITUIDO, E.ANULADO, E.BORRADOR])
def test_los_demas_estados_no_caducan(estado: E) -> None:
    assert estado_visible(estado, date(2026, 1, 1), HOY) is estado


def test_acepta_el_valor_textual_de_la_bd() -> None:
    assert estado_visible("pendiente", date(2026, 1, 1), HOY) is E.CADUCADO

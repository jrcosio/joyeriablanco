"""⚖️ Test obligatorio (constitución VII): cálculo de importes y redondeos.

Tabla de casos calculados a mano con la política única de research R-10 (FR-015, SC-003):
importe de línea redondeado al céntimo; base por tipo = suma de líneas; cuota por tipo sobre la
base, redondeada; medio céntimo alejándose de cero.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.importes import (
    MAX_IMPORTE,
    ImporteFueraDeRango,
    LineaCalculo,
    allowed_rates,
    compute_totals,
    is_rate_allowed,
    line_amount,
    round_amount,
)

D = Decimal
IVA_21 = D("21")


def _linea(unidades: str, precio: str, tipo: str | None = "21") -> LineaCalculo:
    return LineaCalculo(
        unidades=D(unidades),
        precio_unitario=D(precio),
        tipo_iva=None if tipo is None else D(tipo),
    )


# ------------------------------------------------------------------------------ redondeo


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("0.125", "0.13"),  # medio céntimo exacto: alejándose de cero (no al par, que daría 0.12)
        ("0.105", "0.11"),  # ídem (al par daría 0.10)
        ("0.115", "0.12"),
        ("0.124", "0.12"),
        ("-0.125", "-0.13"),  # simétrico para negativos
        ("1290", "1290.00"),
    ],
)
def test_redondeo_al_centimo_alejandose_de_cero(valor: str, esperado: str) -> None:
    resultado = round_amount(D(valor))

    assert resultado == D(esperado)
    assert resultado.as_tuple().exponent == -2


def test_importe_de_linea_con_medio_centimo() -> None:
    assert line_amount(D("0.5"), D("0.25")) == D("0.13")  # 0.125 → 0.13


def test_importe_de_linea_con_cantidades_decimales() -> None:
    assert line_amount(D("1.5"), D("33.33")) == D("50.00")  # 49.995 → 50.00
    assert line_amount(D("2.25"), D("10.10")) == D("22.73")  # 22.725 → 22.73


# ------------------------------------------------------------------------------- totales


def test_ejemplo_de_la_captura() -> None:
    totales = compute_totals(
        [_linea("1", "1200.00"), _linea("2", "45.00")], tipo_iva_por_defecto=IVA_21
    )

    assert totales.base_total == D("1290.00")
    assert totales.cuota_total == D("270.90")
    assert totales.importe_total == D("1560.90")
    assert [(d.tipo_iva, d.base, d.cuota) for d in totales.desglose] == [
        (D("21.00"), D("1290.00"), D("270.90"))
    ]


def test_cuota_con_medio_centimo_exacto() -> None:
    totales = compute_totals([_linea("1", "0.50")], tipo_iva_por_defecto=IVA_21)

    assert totales.cuota_total == D("0.11")  # 0.105 → 0.11
    assert totales.importe_total == D("0.61")


def test_la_base_es_la_suma_de_las_lineas_ya_redondeadas() -> None:
    # 3 × 0.125 = 0.375 por separado → 3 × 0.13 = 0.39 (redondear el total daría 0.38)
    lineas = [_linea("0.5", "0.25") for _ in range(3)]

    totales = compute_totals(lineas, tipo_iva_por_defecto=IVA_21)

    assert totales.base_total == D("0.39")
    assert sum((line_amount(x.unidades, x.precio_unitario) for x in lineas), D(0)) == D("0.39")


def test_la_cuota_se_calcula_sobre_la_base_y_no_linea_a_linea() -> None:
    # Tres líneas de 0.07 € al 21 %. Línea a línea: 0.0147 → 0.01 (× 3 = 0.03).
    # Sobre la base: 0.21 × 21 % = 0.0441 → 0.04, que es lo que dice la política de R-10.
    totales = compute_totals([_linea("1", "0.07") for _ in range(3)], tipo_iva_por_defecto=IVA_21)

    assert totales.base_total == D("0.21")
    assert totales.cuota_total == D("0.04")


def test_varios_tipos_se_desglosan_por_separado() -> None:
    totales = compute_totals(
        [_linea("1", "100.00", "21"), _linea("1", "100.00", "10"), _linea("2", "10.00", "21")],
        tipo_iva_por_defecto=IVA_21,
    )

    assert [(d.tipo_iva, d.base, d.cuota) for d in totales.desglose] == [
        (D("10.00"), D("100.00"), D("10.00")),
        (D("21.00"), D("120.00"), D("25.20")),
    ]
    assert totales.base_total == D("220.00")
    assert totales.cuota_total == D("35.20")
    assert totales.importe_total == D("255.20")


def test_devolucion_total_sin_lineas_da_un_desglose_a_cero() -> None:
    totales = compute_totals([], tipo_iva_por_defecto=IVA_21)

    assert [(d.tipo_iva, d.base, d.cuota) for d in totales.desglose] == [
        (D("21.00"), D("0.00"), D("0.00"))
    ]
    assert totales.importe_total == D("0.00")


def test_importe_maximo_admitido() -> None:
    # 99.999,99 × 99.999,99 no cabe; el máximo de Decimal(12,2) sí se alcanza sin superarlo.
    base_maxima = round_amount(MAX_IMPORTE / D("1.21"))
    totales = compute_totals([_linea("1", str(base_maxima))], tipo_iva_por_defecto=IVA_21)

    assert totales.importe_total <= MAX_IMPORTE


def test_superar_el_importe_maximo_se_rechaza() -> None:
    with pytest.raises(ImporteFueraDeRango):
        compute_totals([_linea("99999.99", "99999999.99")], tipo_iva_por_defecto=IVA_21)


def test_ningun_resultado_es_float() -> None:
    totales = compute_totals([_linea("1", "1.10")], tipo_iva_por_defecto=IVA_21)

    valores: list[Decimal | None] = [totales.base_total, totales.cuota_total, totales.importe_total]
    valores += [v for d in totales.desglose for v in (d.tipo_iva, d.base, d.cuota)]
    assert all(isinstance(v, Decimal) for v in valores)


def test_no_se_admiten_floats_de_entrada() -> None:
    with pytest.raises(TypeError):
        line_amount(1.1, D("1"))  # type: ignore[arg-type]


# ------------------------------------------------ factura de oro de inversión exenta (R-21)


def test_lingote_exento_sin_tipo_ni_cuota() -> None:
    # 1 × 7.450,00 sin IVA: la base es el total (FR-052, US2-10).
    totales = compute_totals([_linea("1", "7450.00", None)], tipo_iva_por_defecto=None)

    assert [(d.tipo_iva, d.base, d.cuota) for d in totales.desglose] == [
        (None, D("7450.00"), D("0.00"))
    ]
    assert totales.base_total == D("7450.00")
    assert totales.cuota_total == D("0.00")
    assert totales.importe_total == D("7450.00")


def test_exenta_redondea_solo_el_importe_de_cada_linea() -> None:
    # Misma política que las sujetas: medio céntimo de la línea alejándose de cero (0.125 → 0.13).
    totales = compute_totals(
        [_linea("0.5", "0.25", None), _linea("2", "1200.00", None)], tipo_iva_por_defecto=None
    )

    assert totales.base_total == D("2400.13")
    assert totales.cuota_total == D("0.00")
    assert totales.importe_total == D("2400.13")


def test_devolucion_total_exenta_da_un_detalle_exento_a_cero() -> None:
    totales = compute_totals([], tipo_iva_por_defecto=None)

    assert [(d.tipo_iva, d.base, d.cuota) for d in totales.desglose] == [
        (None, D("0.00"), D("0.00"))
    ]
    assert totales.importe_total == D("0.00")


def test_el_detalle_exento_va_despues_de_los_sujetos() -> None:
    # La factura nunca mezcla (FR-052), pero el dominio ordena igual si se le pide.
    totales = compute_totals(
        [_linea("1", "10.00", None), _linea("1", "100.00", "21")], tipo_iva_por_defecto=IVA_21
    )

    assert [(d.tipo_iva, d.cuota) for d in totales.desglose] == [
        (D("21.00"), D("21.00")),
        (None, D("0.00")),
    ]
    assert totales.importe_total == D("131.00")


# ---------------------------------------------- tipos de IVA (F-3): lista informativa (R-20)


@pytest.mark.parametrize("tipo", ["0", "4", "10", "21", "21.00"])
def test_tipos_admitidos_en_2026(tipo: str) -> None:
    assert is_rate_allowed(D(tipo), date(2026, 9, 29))


@pytest.mark.parametrize("tipo", ["5", "22", "2", "7.5", "16"])
def test_tipos_no_admitidos_en_2026(tipo: str) -> None:
    assert not is_rate_allowed(D(tipo), date(2026, 9, 29))


def test_ventanas_historicas_de_f3() -> None:
    assert is_rate_allowed(D("5"), date(2024, 8, 15))
    assert not is_rate_allowed(D("5"), date(2024, 10, 1))
    assert is_rate_allowed(D("7.5"), date(2024, 11, 15))
    assert is_rate_allowed(D("2"), date(2024, 12, 31))
    assert not is_rate_allowed(D("2"), date(2025, 1, 1))


def test_la_fecha_evaluada_es_la_de_la_operacion() -> None:
    # F-3 §15.1: «Si FechaOperacion (FechaExpedicionFactura … si no se informa FechaOperacion)».
    # Quien llama pasa la fecha de operación si existe; la función solo evalúa la fecha dada.
    operacion_2024 = date(2024, 11, 20)

    assert is_rate_allowed(D("7.5"), operacion_2024)


def test_lista_de_tipos_admitidos_hoy() -> None:
    assert allowed_rates(date(2026, 9, 29)) == (D("0"), D("4"), D("10"), D("21"))

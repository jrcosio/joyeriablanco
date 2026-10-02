"""Formato en español de los documentos impresos (003, FR-006, research R-6).

Las cadenas de euros, porcentajes, fechas e IBAN son las mismas que esperan los tests de la web
(`joyeriablanco_web/src/lib/dinero.test.ts`, `facturacion.test.ts` y `fechas.ts`). Las unidades
siguen FR-006: decimales solo si los tienen.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain.formato import (
    format_euros,
    format_fecha,
    format_fecha_hora,
    format_iban,
    format_identificacion,
    format_porcentaje,
    format_unidades,
    nombre_mes,
    nombre_pais,
)

NBSP = " "


@pytest.mark.parametrize(
    ("importe", "esperado"),
    [
        (Decimal("1560.90"), f"1.560,90{NBSP}€"),
        (Decimal("45"), f"45,00{NBSP}€"),
        (Decimal("0.00"), f"0,00{NBSP}€"),
        (Decimal("1234567.89"), f"1.234.567,89{NBSP}€"),
        (Decimal("0.05"), f"0,05{NBSP}€"),
        (Decimal("-12.30"), f"-12,30{NBSP}€"),
    ],
)
def test_euros(importe: Decimal, esperado: str) -> None:
    assert format_euros(importe) == esperado


def test_euros_rechaza_mas_de_dos_decimales_y_float() -> None:
    with pytest.raises(ValueError, match="dos decimales"):
        format_euros(Decimal("1.005"))
    with pytest.raises(TypeError):
        format_euros(1.5)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("unidades", "esperado"),
    [
        (Decimal("2"), "2"),
        (Decimal("2.00"), "2"),
        (Decimal("1.50"), "1,50"),
        (Decimal("0.25"), "0,25"),
        (Decimal("1200"), "1.200"),
        (Decimal("1200.5"), "1.200,50"),
    ],
)
def test_unidades(unidades: Decimal, esperado: str) -> None:
    assert format_unidades(unidades) == esperado


@pytest.mark.parametrize(
    ("tipo", "esperado"),
    [(Decimal("21.00"), "21 %"), (Decimal("10.5"), "10,5 %"), (Decimal("7.25"), "7,25 %")],
)
def test_porcentaje(tipo: Decimal, esperado: str) -> None:
    assert format_porcentaje(tipo) == esperado


def test_fechas() -> None:
    assert format_fecha(date(2026, 3, 5)) == "05/03/2026"
    # 2026-10-01 16:42 UTC son las 18:42 en Madrid (horario de verano)
    assert format_fecha_hora(datetime(2026, 10, 1, 16, 42, tzinfo=UTC)) == (
        "01/10/2026 a las 18:42"
    )


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("ES9121000418450200051332", "ES91 2100 0418 4502 0005 1332"),
        ("es91 2100 0418 4502 0005 1332", "ES91 2100 0418 4502 0005 1332"),
        ("GB82WEST12345698765432", "GB82 WEST 1234 5698 7654 32"),
    ],
)
def test_iban(entrada: str, esperado: str) -> None:
    assert format_iban(entrada) == esperado


def test_meses_y_paises_en_espanol() -> None:
    assert nombre_mes(3) == "marzo"
    assert nombre_mes(12) == "diciembre"
    assert nombre_pais("FR") == "Francia"
    assert nombre_pais("DE") == "Alemania"
    assert nombre_pais("ES") == "España"


@pytest.mark.parametrize(
    ("tipo", "pais", "numero", "esperado"),
    [
        ("NIF", "ES", "52364897H", "NIF 52364897H"),
        ("02", "FR", "FR12345678901", "NIF-IVA FR12345678901 (Francia)"),
        ("03", "FR", "X1234567", "Pasaporte X1234567 (Francia)"),
        ("03", "ES", "PAB123456", "Pasaporte PAB123456"),
        ("04", "DE", "T22000129", "Documento oficial de identificación T22000129 (Alemania)"),
        ("05", "PT", "CR-99", "Certificado de residencia CR-99 (Portugal)"),
        ("06", "MA", "Z-77", "Otro documento probatorio Z-77 (Marruecos)"),
    ],
)
def test_identificacion(tipo: str, pais: str, numero: str, esperado: str) -> None:
    assert format_identificacion(tipo, pais, numero) == esperado

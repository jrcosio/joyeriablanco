"""Numeración `FAC-AAAA-NNNN` y `REC-AAAA-NNNN` (FR-006, FR-009; constitución 2.2.0; R-7)."""

from datetime import date

import pytest

from app.domain.numeracion import (
    format_num_serie,
    parse_num_serie,
    validate_num_serie,
    year_of,
)
from app.domain.tipos import Serie


@pytest.mark.parametrize(
    ("serie", "anio", "numero", "esperado"),
    [
        (Serie.ORDINARIA, 2026, 1, "FAC-2026-0001"),
        (Serie.ORDINARIA, 2026, 143, "FAC-2026-0143"),
        (Serie.RECTIFICATIVA, 2026, 1, "REC-2026-0001"),
        (Serie.ORDINARIA, 2026, 10000, "FAC-2026-10000"),  # crece sin truncar
    ],
)
def test_formato(serie: Serie, anio: int, numero: int, esperado: str) -> None:
    assert format_num_serie(serie, anio, numero) == esperado


def test_numero_no_positivo() -> None:
    with pytest.raises(ValueError, match="mayor que cero"):
        format_num_serie(Serie.ORDINARIA, 2026, 0)


def test_el_anio_es_el_de_la_fecha_de_expedicion() -> None:
    assert year_of(date(2027, 1, 1)) == 2027
    assert year_of(date(2026, 12, 31)) == 2026


def test_parseo_inverso() -> None:
    assert parse_num_serie("REC-2026-0012") == (Serie.RECTIFICATIVA, 2026, 12)
    assert parse_num_serie("FAC-2026-10000") == (Serie.ORDINARIA, 2026, 10000)


@pytest.mark.parametrize("valor", ["FAC-26-0001", "XYZ-2026-0001", "FAC-2026-001", "fac-2026-0001"])
def test_parseo_rechaza_formatos_ajenos(valor: str) -> None:
    with pytest.raises(ValueError, match="formato no válido"):
        parse_num_serie(valor)


@pytest.mark.parametrize("valor", ["FAC-2026-0001", "12345678 / G33", "A" * 60])
def test_num_serie_admitido_por_f3(valor: str) -> None:
    assert validate_num_serie(valor) is None


@pytest.mark.parametrize("valor", ['FAC"1', "FAC'1", "FAC<1", "FAC>1", "FAC=1", "FACñ1", "A" * 61])
def test_num_serie_rechazado_por_f3(valor: str) -> None:
    # F-3 §3.1.3.1: ASCII 32–126 sin " ' < > =; F-1: alfanumérico (60).
    assert validate_num_serie(valor) is not None

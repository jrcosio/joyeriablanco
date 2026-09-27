"""Código postal → provincia (FR-028; F-7 y research R-20.3)."""

import pytest

from app.domain.codigos_postales import provincia_from_codigo_postal


@pytest.mark.parametrize(
    ("cp", "provincia"),
    [("29001", "29"), ("01001", "01"), ("08080", "08"), ("51001", "51"), ("52001", "52")],
)
def test_los_dos_primeros_digitos_identifican_la_provincia(cp: str, provincia: str) -> None:
    assert provincia_from_codigo_postal(cp) == provincia


@pytest.mark.parametrize("cp", ["00123", "53000", "99999"])
def test_prefijo_sin_provincia(cp: str) -> None:
    with pytest.raises(ValueError, match="no corresponde a ninguna provincia"):
        provincia_from_codigo_postal(cp)


@pytest.mark.parametrize("cp", ["2900", "290011", "29O01", "", "29 001"])
def test_formato_distinto_de_cinco_digitos(cp: str) -> None:
    with pytest.raises(ValueError, match="5 dígitos"):
        provincia_from_codigo_postal(cp)

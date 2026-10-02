"""Contacto y pie de factura de la joyería (003, FR-024; research R-9)."""

import pytest

from app.domain.contacto import normalize_pie, validate_correo, validate_telefono, validate_web


@pytest.mark.parametrize("telefono", ["+34 942 000 000", "(942) 21-34-56", "942213456", "600 000"])
def test_telefonos_validos(telefono: str) -> None:
    assert validate_telefono(telefono) is None


@pytest.mark.parametrize(
    ("telefono", "motivo"),
    [
        ("abc", "solo dígitos, espacios, +, paréntesis y guiones"),
        ("942.21.34", "solo dígitos, espacios, +, paréntesis y guiones"),
        ("+34 94", "al menos 6 dígitos"),
    ],
)
def test_telefonos_no_validos(telefono: str, motivo: str) -> None:
    error = validate_telefono(telefono)

    assert error is not None
    assert motivo in error


def test_correo() -> None:
    assert validate_correo("info@joyeriablanco.es") is None
    assert validate_correo("x@") is not None
    assert validate_correo("sin-arroba") is not None


@pytest.mark.parametrize(
    "web",
    [
        "joyeriablanco.es",
        "www.joyeriablanco.es",
        "https://www.joyeriablanco.es/",
        "http://joyeriablanco.es/tienda",
        "joyeria-blanco.com.es",
    ],
)
def test_webs_validas(web: str) -> None:
    assert validate_web(web) is None


@pytest.mark.parametrize(
    "web", ["ftp://joyeriablanco.es", "joyeria blanco", "localhost", "https://"]
)
def test_webs_no_validas(web: str) -> None:
    assert validate_web(web) is not None


def test_pie_normaliza_saltos_y_extremos() -> None:
    assert normalize_pie("  Línea 1\r\nLínea 2\rLínea 3\n\n") == "Línea 1\nLínea 2\nLínea 3"
    assert normalize_pie("   \n  ") is None

"""IBAN del emisor (research R-22): estructura de ISO 13616, 24 caracteres en ES y dígito de
control ISO 7064 MOD 97-10."""

import pytest

from app.domain.iban import normalize_iban, validate_iban


@pytest.mark.parametrize(
    "iban",
    [
        "ES9121000418450200051332",  # ejemplo de los datos demo
        "DE89370400440532013000",
    ],
)
def test_iban_valido(iban: str) -> None:
    assert validate_iban(iban) is None


def test_se_normaliza_quitando_espacios_y_en_mayusculas() -> None:
    assert normalize_iban(" es91 2100 0418 4502 0005 1332 ") == "ES9121000418450200051332"


@pytest.mark.parametrize(
    ("iban", "motivo"),
    [
        ("ES9121000418450200051333", "dígito de control"),  # último dígito cambiado
        ("ES9121000418450200051", "24 caracteres"),  # ES corto con estructura válida
        ("ES912100041845020005133", "24 caracteres"),  # 23
        ("ES91210004184502000513321", "24 caracteres"),  # 25
        ("ES91210004184502000513AB", "24 caracteres"),  # letras en la parte numérica de ES
        ("9121000418450200051332", "código del país"),  # sin país
        ("DE8937040044", "código del país"),  # menos de 15
        ("MT84MALT011000012345MTLCAST001SXYZW", "código del país"),  # 35: más de 34
        ("ES91-2100-0418-4502-0005-1332", "código del país"),  # caracteres no alfanuméricos
    ],
)
def test_iban_no_valido(iban: str, motivo: str) -> None:
    resultado = validate_iban(iban)

    assert resultado is not None
    assert motivo in resultado

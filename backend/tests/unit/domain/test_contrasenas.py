"""Política de contraseñas (FR-008) y contraseña temporal (FR-015)."""

import pytest

from app.domain.contrasenas import (
    LONGITUD_MAXIMA,
    LONGITUD_MINIMA,
    generate_temporary_password,
    validate_password,
)


def test_longitudes_limite() -> None:
    assert LONGITUD_MINIMA == 12
    assert LONGITUD_MAXIMA == 128
    assert validate_password("x7Qm-v9Lp#2a") == []  # 12 caracteres
    assert validate_password("x7Qm-v9Lp#2") != []  # 11 caracteres
    assert validate_password("Rubí" * 32) == []  # 128 caracteres
    assert validate_password("Rubí" * 32 + "!") != []  # 129 caracteres


@pytest.mark.parametrize(
    "comun", ["qwertyuiopasdfghjkl", "QWERTYUIOPASDFGHJKL", "JoyeriaBlanco123"]
)
def test_rechaza_contrasenas_comunes_sin_distinguir_mayusculas(comun: str) -> None:
    errores = validate_password(comun)

    assert any("común" in e for e in errores)


def test_rechaza_si_contiene_el_nombre_de_usuario_sin_distinguir_mayusculas() -> None:
    errores = validate_password("Mi-clave-ANA.GARCIA-2026", nombre_usuario="ana.garcia")

    assert any("nombre de usuario" in e for e in errores)


def test_no_exige_reglas_de_composicion() -> None:
    # Solo minúsculas y espacios: válida si es larga y no es común (NIST SP 800-63B).
    assert validate_password("una frase larga de joyero discreto") == []


def test_mensajes_en_espanol() -> None:
    (mensaje,) = validate_password("corta")

    assert mensaje == "Debe tener al menos 12 caracteres."


def test_contrasena_temporal_cumple_la_politica_y_es_distinta_cada_vez() -> None:
    temporales = {generate_temporary_password() for _ in range(50)}

    assert len(temporales) == 50
    for temporal in temporales:
        assert validate_password(temporal) == []
        assert len(temporal.replace("-", "")) == 16
        assert not set(temporal) & set("0O1lI")  # sin caracteres ambiguos

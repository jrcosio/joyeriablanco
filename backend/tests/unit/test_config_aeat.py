"""Entorno de la AEAT para la dirección de cotejo del QR (003, FR-017, research R-3)."""

import pytest
from pydantic import ValidationError

from app.core.config import Entorno, Settings
from app.domain.tipos import EntornoAeat


def _produccion(**extra: object) -> Settings:
    datos: dict[str, object] = {
        "entorno": Entorno.PRODUCCION,
        "sesion_cookie_segura": True,
        "origen_permitido": "https://gestion.example.com",
        "sif_productor_nombre": "Productora, S.L.",
        "sif_productor_nif": "12345678Z",
        **extra,
    }
    return Settings.model_validate(datos)


@pytest.mark.parametrize("entorno", [Entorno.DESARROLLO, Entorno.E2E, Entorno.TEST])
def test_fuera_de_produccion_sin_valor_apunta_a_pruebas(entorno: Entorno) -> None:
    ajustes = Settings(entorno=entorno)

    assert ajustes.aeat_entorno is None
    assert ajustes.entorno_aeat is EntornoAeat.PRUEBAS


def test_fuera_de_produccion_se_puede_fijar() -> None:
    ajustes = Settings(entorno=Entorno.DESARROLLO, aeat_entorno=EntornoAeat.PRODUCCION)

    assert ajustes.entorno_aeat is EntornoAeat.PRODUCCION


def test_en_produccion_sin_aeat_entorno_no_arranca() -> None:
    with pytest.raises(ValidationError, match="AEAT_ENTORNO"):
        _produccion()


@pytest.mark.parametrize("valor", ["pruebas", "produccion"])
def test_en_produccion_con_aeat_entorno_arranca(valor: str) -> None:
    ajustes = _produccion(aeat_entorno=valor)

    assert ajustes.entorno_aeat == EntornoAeat(valor)


def test_valor_desconocido_se_rechaza() -> None:
    with pytest.raises(ValidationError):
        Settings(entorno=Entorno.TEST, aeat_entorno="preproduccion")  # type: ignore[arg-type]

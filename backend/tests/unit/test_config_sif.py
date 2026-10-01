"""Bloque SistemaInformatico: en producción el productor es obligatorio (research R-5, T001)."""

import pytest
from pydantic import ValidationError

from app.core.config import Entorno, Settings


def _produccion(**productor: str) -> Settings:
    datos: dict[str, object] = {
        "entorno": Entorno.PRODUCCION,
        "sesion_cookie_segura": True,
        "origen_permitido": "https://gestion.example.com",
        **productor,
    }
    return Settings.model_validate(datos)


def test_fuera_de_produccion_valen_los_valores_ficticios() -> None:
    ajustes = Settings(entorno=Entorno.TEST)

    assert ajustes.sif_id_sistema == "JB"
    assert ajustes.sif_nombre_sistema == "Joyería Blanco Gestión"


def test_en_produccion_sin_productor_no_arranca() -> None:
    with pytest.raises(ValidationError, match="SIF_PRODUCTOR_NOMBRE"):
        _produccion()


def test_en_produccion_con_nif_no_valido_no_arranca() -> None:
    with pytest.raises(ValidationError, match="SIF_PRODUCTOR_NIF"):
        _produccion(sif_productor_nombre="Productora, S.L.", sif_productor_nif="12345678A")


def test_en_produccion_con_nif_ficticio_no_arranca() -> None:
    with pytest.raises(ValidationError, match="SIF_PRODUCTOR_NIF"):
        _produccion(sif_productor_nombre="Productora, S.L.")


def test_en_produccion_con_productor_valido_arranca() -> None:
    ajustes = _produccion(sif_productor_nombre="Productora, S.L.", sif_productor_nif="12345678Z")

    assert ajustes.sif_productor_nif == "12345678Z"


@pytest.mark.parametrize("codigo", ["jb", "Ñ1", "ABC", "J"])
def test_el_id_del_sistema_son_dos_mayusculas_o_digitos(codigo: str) -> None:
    with pytest.raises(ValidationError):
        Settings(entorno=Entorno.TEST, sif_id_sistema=codigo)

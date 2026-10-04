"""Bloque SistemaInformatico: en producción el productor es obligatorio (research R-5, T001)."""

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Entorno, Settings

# Obligatorios en producción desde 004 (research R-6 y R-13)
DECLARACION_Y_CERTIFICADO: dict[str, str] = {
    "sif_productor_direccion": "Calle Mayor 1, 28001 Madrid",
    "sif_declaracion_fecha": "2026-10-03",
    "sif_declaracion_lugar": "Madrid (España)",
    "certificado_ruta": "/run/secrets/certificado.p12",
    "certificado_contrasena": "secreta",
}


def _produccion(**productor: str) -> Settings:
    datos: dict[str, object] = {
        "entorno": Entorno.PRODUCCION,
        "sesion_cookie_segura": True,
        "origen_permitido": "https://gestion.example.com",
        "aeat_entorno": "pruebas",  # obligatorio en producción desde 003 (research R-3)
        **DECLARACION_Y_CERTIFICADO,
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


PRODUCTOR = {"sif_productor_nombre": "Productora, S.L.", "sif_productor_nif": "12345678Z"}


@pytest.mark.parametrize(
    ("campo", "variable"),
    [
        ("sif_productor_direccion", "SIF_PRODUCTOR_DIRECCION"),
        ("sif_declaracion_lugar", "SIF_DECLARACION_LUGAR"),
    ],
)
def test_en_produccion_la_declaracion_no_admite_valores_ficticios(
    campo: str, variable: str
) -> None:
    ficticio = str(Settings.model_fields[campo].default)

    with pytest.raises(ValidationError, match=variable):
        _produccion(**PRODUCTOR, **{campo: ficticio})


def test_en_produccion_sin_fecha_de_la_declaracion_no_arranca() -> None:
    datos = {**DECLARACION_Y_CERTIFICADO, **PRODUCTOR}
    del datos["sif_declaracion_fecha"]

    with pytest.raises(ValidationError, match="SIF_DECLARACION_FECHA"):
        Settings.model_validate(
            {
                "entorno": Entorno.PRODUCCION,
                "origen_permitido": "https://gestion.example.com",
                "aeat_entorno": "pruebas",
                **datos,
            }
        )


@pytest.mark.parametrize("falta", ["certificado_ruta", "certificado_contrasena"])
def test_en_produccion_sin_certificado_configurado_no_arranca(falta: str) -> None:
    # None explícito: los tests publican el certificado de la sesión en el entorno (conftest).
    datos: dict[str, str | None] = {**DECLARACION_Y_CERTIFICADO, **PRODUCTOR, falta: None}

    with pytest.raises(ValidationError, match="CERTIFICADO_RUTA y CERTIFICADO_CONTRASENA"):
        Settings.model_validate(
            {
                "entorno": Entorno.PRODUCCION,
                "origen_permitido": "https://gestion.example.com",
                "aeat_entorno": "pruebas",
                **datos,
            }
        )


def test_la_contrasena_del_certificado_no_se_muestra() -> None:
    ajustes = Settings(entorno=Entorno.TEST, certificado_contrasena=SecretStr("muy-secreta"))

    assert "muy-secreta" not in repr(ajustes)
    assert "muy-secreta" not in str(ajustes.model_dump())

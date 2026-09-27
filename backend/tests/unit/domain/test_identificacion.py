"""Identificación fiscal del cliente (FR-024 a FR-026; research R-20.1 y R-20.2)."""

import pytest

from app.domain.identificacion import (
    ClaseNif,
    allowed_identificacion_tipos,
    classify_nif,
    normalize_identificacion,
    validate_identificacion,
    validate_nif,
    validate_nif_iva,
)
from app.domain.tipos import TipoIdentificacion as T


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [("12.345.678-z", "12345678Z"), (" x 1234567 l ", "X1234567L"), ("b-1234/5678", "B12345678")],
)
def test_normaliza_mayusculas_sin_separadores(entrada: str, esperado: str) -> None:
    assert normalize_identificacion(entrada) == esperado


@pytest.mark.parametrize(
    ("nif", "clase"),
    [
        ("12345678Z", ClaseNif.DNI),
        ("X1234567L", ClaseNif.NIE),
        ("B12345678", ClaseNif.ENTIDAD),
        ("W1234567J", ClaseNif.ENTIDAD),
        ("K1234567L", ClaseNif.ESPECIAL),
        ("M12AB34CD", ClaseNif.ESPECIAL),
        ("I1234567A", None),  # letra de forma jurídica inexistente
        ("O1234567A", None),
        ("T1234567A", None),
        ("1234567Z", None),
    ],
)
def test_clasifica_el_nif_segun_su_composicion_oficial(nif: str, clase: ClaseNif | None) -> None:
    assert classify_nif(nif) == clase


@pytest.mark.parametrize("nif", ["12345678Z", "00000000T", "X1234567L", "Y1234567X", "Z1234567R"])
def test_dni_y_nie_con_letra_correcta(nif: str) -> None:
    assert validate_nif(nif) is None


@pytest.mark.parametrize("nif", ["12345678A", "00000000R", "X1234567A", "Y1234567L"])
def test_dni_y_nie_con_letra_incorrecta(nif: str) -> None:
    assert validate_nif(nif) == "La letra del NIF no es correcta."


@pytest.mark.parametrize("nif", ["B12345678", "A1234567J", "N1234567C", "K1234567L", "L1234567A"])
def test_entidades_y_klm_solo_se_valida_la_estructura(nif: str) -> None:
    # Su algoritmo de control no está publicado en fuente oficial (research R-20.2).
    assert validate_nif(nif) is None


@pytest.mark.parametrize("nif", ["I1234567A", "B1234567", "1234567Z", "ABCDEFGHI"])
def test_nif_con_estructura_invalida(nif: str) -> None:
    assert validate_nif(nif) == "Formato de NIF no válido."


@pytest.mark.parametrize(
    ("pais", "numero", "canonico"),
    [
        ("DE", "DE123456789", "DE123456789"),
        ("DE", "123456789", "DE123456789"),  # sin prefijo: se añade
        ("FR", "FR1A3456789012", None),  # 12 caracteres: demasiado largo
        ("FR", "FRAB345678901", "FRAB345678901"),  # 11 alfanuméricos
        ("FR", "AB345678901", "FRAB345678901"),
        ("GR", "EL123456789", "EL123456789"),  # Grecia usa el prefijo EL
        ("GR", "123456789", "EL123456789"),
        ("GB", "XI123456789", "XI123456789"),  # Irlanda del Norte
        ("RO", "RO1234", "RO1234"),
        ("RO", "RO01234", None),  # sin ceros a la izquierda
        ("CZ", "CZ12345678", "CZ12345678"),
        ("NL", "NL123456789B01", "NL123456789B01"),
        ("PT", "PT12345678", None),
        ("ES", "ESB12345678", None),  # España no figura en la tabla
        ("US", "123456789", None),
    ],
)
def test_nif_iva_segun_la_tabla_oficial(pais: str, numero: str, canonico: str | None) -> None:
    if canonico is None:
        with pytest.raises(ValueError, match="NIF-IVA"):
            validate_nif_iva(pais, numero)
    else:
        assert validate_nif_iva(pais, numero) == canonico


def test_tipos_admitidos_por_pais() -> None:
    assert allowed_identificacion_tipos("ES") == (T.NIF, T.PASAPORTE)
    assert allowed_identificacion_tipos("FR") == (
        T.NIF_IVA,
        T.PASAPORTE,
        T.DOCUMENTO_OFICIAL,
        T.CERTIFICADO_RESIDENCIA,
        T.OTRO_DOCUMENTO,
    )
    assert allowed_identificacion_tipos("US") == (
        T.PASAPORTE,
        T.DOCUMENTO_OFICIAL,
        T.CERTIFICADO_RESIDENCIA,
        T.OTRO_DOCUMENTO,
    )


def test_validacion_completa_devuelve_la_forma_canonica_y_los_errores_por_campo() -> None:
    assert validate_identificacion("es", T.NIF, "12.345.678-z") == ("12345678Z", [])
    assert validate_identificacion("US", T.PASAPORTE, "a b 123-456") == ("AB123456", [])

    _, errores = validate_identificacion("ES", T.NIF_IVA, "B12345678")
    assert [(e.campo, e.mensaje) for e in errores] == [
        ("identificacion_tipo", "Tipo de identificación no admitido para este país.")
    ]
    _, errores = validate_identificacion("ES", T.NIF, "12345678A")
    assert [e.campo for e in errores] == ["identificacion_numero"]
    _, errores = validate_identificacion("XX", T.PASAPORTE, "123")
    assert [e.campo for e in errores] == ["identificacion_pais"]
    _, errores = validate_identificacion("US", T.PASAPORTE, "A" * 21)
    assert errores[0].mensaje == "No puede superar 20 caracteres."

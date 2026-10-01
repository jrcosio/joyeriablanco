"""Importes y cantidades viajan como texto: nunca como número JSON (constitución II, R-10)."""

from decimal import Decimal

import pytest
from pydantic import BaseModel, ValidationError

from app.schemas.importes import Cantidad, Importe, ImporteSalida, TipoIvaEntrada, TipoIvaSalida


class _Entrada(BaseModel):
    importe: Importe
    cantidad: Cantidad


class _Salida(BaseModel):
    importe: ImporteSalida
    tipo: TipoIvaSalida


class _Tipo(BaseModel):
    tipo: TipoIvaEntrada


@pytest.mark.parametrize(
    ("texto", "valor"), [("45", "45"), ("1200.5", "1200.5"), ("1200.50", "1200.50"), ("0", "0")]
)
def test_importe_admite_texto_decimal_con_punto(texto: str, valor: str) -> None:
    modelo = _Entrada.model_validate_json(f'{{"importe": "{texto}", "cantidad": "1"}}')

    assert modelo.importe == Decimal(valor)
    assert isinstance(modelo.importe, Decimal)


@pytest.mark.parametrize("json_importe", ["45", "45.5", "0"])
def test_importe_rechaza_numeros_json(json_importe: str) -> None:
    with pytest.raises(ValidationError, match="texto"):
        _Entrada.model_validate_json(f'{{"importe": {json_importe}, "cantidad": "1"}}')


@pytest.mark.parametrize("texto", ["-1", "1.005", "1,50", "1.2.3", "", " 12", "12345678901"])
def test_importe_rechaza_formatos_no_validos(texto: str) -> None:
    with pytest.raises(ValidationError):
        _Entrada.model_validate_json(f'{{"importe": "{texto}", "cantidad": "1"}}')


@pytest.mark.parametrize("texto", ["0", "0.00", "-1", "100000", "1.234"])
def test_cantidad_mayor_que_cero_con_dos_decimales(texto: str) -> None:
    with pytest.raises(ValidationError):
        _Entrada.model_validate_json(f'{{"importe": "1", "cantidad": "{texto}"}}')


def test_cantidad_valida() -> None:
    modelo = _Entrada.model_validate_json('{"importe": "1", "cantidad": "1.50"}')

    assert modelo.cantidad == Decimal("1.50")


def test_la_salida_serializa_como_cadena_con_dos_decimales() -> None:
    salida = _Salida(importe=Decimal("1290"), tipo=Decimal("21"))

    assert salida.model_dump_json() == '{"importe":"1290.00","tipo":"21.00"}'


def test_tipo_de_iva_de_entrada() -> None:
    assert _Tipo.model_validate_json('{"tipo": "21"}').tipo == Decimal("21")
    with pytest.raises(ValidationError):
        _Tipo.model_validate_json('{"tipo": 21}')


def test_el_esquema_openapi_es_string_con_patron() -> None:
    esquema = _Entrada.model_json_schema()

    for campo in ("importe", "cantidad"):
        assert esquema["properties"][campo]["type"] == "string"
        assert "pattern" in esquema["properties"][campo]
    salida = _Salida.model_json_schema(mode="serialization")
    assert salida["properties"]["importe"]["type"] == "string"

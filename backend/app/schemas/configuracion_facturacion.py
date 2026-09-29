"""Esquemas de la configuración de facturación (contracts/openapi.yaml de 002; FR-001)."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.domain.tipos import Modalidad
from app.schemas.comunes import EntradaBase, SalidaBase
from app.schemas.importes import TipoIvaEntrada, TipoIvaSalida
from app.schemas.usuario import UsuarioReferencia

TextoOpcional = Annotated[str, StringConstraints(strip_whitespace=True)]


class DatosEmisorEntrada(EntradaBase):
    nombre: Annotated[TextoOpcional, Field(max_length=120)] | None = None
    nif: Annotated[TextoOpcional, Field(max_length=20)] | None = None
    direccion: Annotated[TextoOpcional, Field(max_length=200)] | None = None
    codigo_postal: Annotated[TextoOpcional, Field(max_length=10)] | None = None
    localidad: Annotated[TextoOpcional, Field(max_length=100)] | None = None


class ConfiguracionFacturacionEntrada(EntradaBase):
    version: Annotated[int, Field(ge=1)]
    iva_por_defecto: TipoIvaEntrada
    clave_regimen: Annotated[str, Field(pattern=r"^[0-9]{2}$")]
    modalidad: Modalidad | None
    emisor: DatosEmisorEntrada


class DatosEmisorSalida(SalidaBase):
    nombre: str | None
    nif: str | None
    direccion: str | None
    codigo_postal: str | None
    localidad: str | None
    provincia: str | None


class ConfiguracionFacturacionSalida(SalidaBase):
    version: int
    iva_por_defecto: TipoIvaSalida
    clave_regimen: str
    modalidad: Modalidad | None
    emisor: DatosEmisorSalida
    emision_posible: bool
    faltan: list[str]
    proximo_numero: str
    modalidad_bloqueada: bool
    tipos_iva_admitidos: list[TipoIvaSalida]
    actualizado_en: datetime
    actualizado_por: UsuarioReferencia | None


class AjusteContadorEntrada(EntradaBase):
    proximo_numero: Annotated[int, Field(ge=2)]
    motivo: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    simular: bool


class AjusteContadorSalida(SalidaBase):
    serie: Literal["FAC"]
    anio: int
    ultimo_usado: int
    proximo_numero: int
    numeros_sin_usar: int
    aplicado: bool


class ParametrosFacturacionSalida(SalidaBase):
    iva_por_defecto: TipoIvaSalida
    emision_posible: bool
    faltan: list[str]
    proximo_numero: str
    hoy: date
    fecha_minima: date | None

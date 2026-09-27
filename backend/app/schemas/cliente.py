"""Esquemas de clientes (contracts/openapi.yaml). Nunca se expone el modelo ORM."""

import uuid
from datetime import datetime
from typing import Annotated, Any

from email_validator import EmailNotValidError, validate_email
from pydantic import BeforeValidator, Field, field_validator

from app.domain.tipos import TipoCliente, TipoIdentificacion
from app.models.cliente import Cliente
from app.schemas.comunes import EntradaBase, SalidaBase
from app.schemas.usuario import UsuarioReferencia


def _vacio_a_nulo(valor: Any) -> Any:
    """Un campo opcional vacío o solo con espacios equivale a "sin dato" (FR-055)."""
    if isinstance(valor, str) and not valor.strip():
        return None
    return valor


Opcional = Annotated[str | None, BeforeValidator(_vacio_a_nulo)]
CODIGO_PAIS = r"^[A-Za-z]{2}$"


class ClienteEntrada(EntradaBase):
    tipo: TipoCliente
    nombre: str = Field(min_length=1, max_length=120)
    identificacion_pais: str = Field(default="ES", pattern=CODIGO_PAIS)
    identificacion_tipo: TipoIdentificacion
    identificacion_numero: str = Field(min_length=1, max_length=30)
    direccion: Opcional = Field(default=None, max_length=200)
    codigo_postal: Opcional = Field(default=None, max_length=10)
    localidad: Opcional = Field(default=None, max_length=100)
    provincia_codigo: Opcional = Field(default=None, pattern=r"^[0-9]{2}$")
    provincia_texto: Opcional = Field(default=None, max_length=100)
    pais_residencia: str = Field(default="ES", pattern=CODIGO_PAIS)
    telefono: Opcional = Field(default=None, max_length=30)
    correo: Opcional = Field(default=None, max_length=254)
    observaciones: Opcional = Field(default=None, max_length=2000)

    @field_validator("correo")
    @classmethod
    def _correo_valido(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        try:
            validate_email(valor.strip(), check_deliverability=False)
        except EmailNotValidError as exc:
            msg = "Correo electrónico no válido."
            raise ValueError(msg) from exc
        return valor.strip()


class ClienteEdicionEntrada(ClienteEntrada):
    version: int = Field(ge=1)


class ClienteResumenSalida(SalidaBase):
    id: uuid.UUID
    tipo: TipoCliente
    nombre: str
    identificacion_pais: str
    identificacion_tipo: TipoIdentificacion
    identificacion_numero: str
    localidad: str | None
    provincia_nombre: str | None
    telefono: str | None
    correo: str | None
    activo: bool

    @staticmethod
    def _provincia_nombre(cliente: Cliente) -> str | None:
        if cliente.provincia is not None:
            return cliente.provincia.nombre_visible
        return cliente.provincia_texto

    @classmethod
    def from_model(cls, cliente: Cliente) -> "ClienteResumenSalida":
        return cls(
            id=cliente.id,
            tipo=TipoCliente(cliente.tipo),
            nombre=cliente.nombre,
            identificacion_pais=cliente.identificacion_pais,
            identificacion_tipo=TipoIdentificacion(cliente.identificacion_tipo),
            identificacion_numero=cliente.identificacion_numero,
            localidad=cliente.localidad,
            provincia_nombre=cls._provincia_nombre(cliente),
            telefono=cliente.telefono,
            correo=cliente.correo,
            activo=cliente.activo,
        )


class ClienteSalida(ClienteResumenSalida):
    direccion: str | None
    codigo_postal: str | None
    provincia_codigo: str | None
    provincia_texto: str | None
    pais_residencia: str
    observaciones: str | None
    version: int
    creado_en: datetime
    creado_por: UsuarioReferencia
    actualizado_en: datetime
    actualizado_por: UsuarioReferencia

    @classmethod
    def from_model(cls, cliente: Cliente) -> "ClienteSalida":
        resumen = ClienteResumenSalida.from_model(cliente).model_dump()
        return cls(
            **resumen,
            direccion=cliente.direccion,
            codigo_postal=cliente.codigo_postal,
            provincia_codigo=cliente.provincia_codigo,
            provincia_texto=cliente.provincia_texto,
            pais_residencia=cliente.pais_residencia,
            observaciones=cliente.observaciones,
            version=cliente.version,
            creado_en=cliente.creado_en,
            creado_por=UsuarioReferencia(
                id=cliente.creado_por.id, nombre=cliente.creado_por.nombre
            ),
            actualizado_en=cliente.actualizado_en,
            actualizado_por=UsuarioReferencia(
                id=cliente.actualizado_por.id, nombre=cliente.actualizado_por.nombre
            ),
        )


class ClienteExistente(SalidaBase):
    id: uuid.UUID
    nombre: str
    activo: bool


class IndicadoresSalida(SalidaBase):
    activos: int
    nuevos_este_anio: int

"""Esquemas del sistema informático y de su declaración responsable (004, contrato)."""

from typing import Annotated, Literal

from pydantic import Field

from app.schemas.comunes import SalidaBase


class DeclaracionApartado(SalidaBase):
    letra: str
    texto: Annotated[str, Field(description="Texto descriptivo del art. 15.1 de la Orden")]
    valor: str


class Declaracion(SalidaBase):
    titulo: Literal["DECLARACIÓN RESPONSABLE DEL SISTEMA INFORMÁTICO DE FACTURACIÓN"]
    apartados: list[DeclaracionApartado]


class Productor(SalidaBase):
    nombre: str
    nif: str
    direccion: str


class SistemaSalida(SalidaBase):
    nombre: str
    id_sistema: str
    version: str
    numero_instalacion: str
    productor: Productor
    modalidad: Literal["no_verifactu"]
    declaracion: Declaracion

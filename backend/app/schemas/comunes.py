"""Esquemas comunes: problema RFC 9457 y paginación."""

from pydantic import BaseModel, ConfigDict


class EntradaBase(BaseModel):
    """Base de los esquemas de entrada: rechaza campos desconocidos."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class SalidaBase(BaseModel):
    """Base de los esquemas de salida (nunca se exponen modelos ORM directamente)."""

    model_config = ConfigDict(from_attributes=True)


class CampoErrorSalida(SalidaBase):
    campo: str
    mensaje: str


class Problema(SalidaBase):
    type: str
    title: str
    status: int
    detail: str | None = None
    errores: list[CampoErrorSalida] | None = None


class Pagina[T](SalidaBase):
    elementos: list[T]
    total: int
    pagina: int
    tamano: int

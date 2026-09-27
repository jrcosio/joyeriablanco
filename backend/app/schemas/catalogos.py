"""Esquemas de catálogos."""

from app.domain.tipos import TipoIdentificacion
from app.schemas.comunes import SalidaBase


class ProvinciaSalida(SalidaBase):
    codigo: str
    nombre: str
    nombre_visible: str


class TipoIdentificacionSalida(SalidaBase):
    codigo: TipoIdentificacion
    descripcion: str
    ambito: str


class CatalogosSalida(SalidaBase):
    provincias: list[ProvinciaSalida]
    paises: list[str]
    paises_nif_iva: list[str]
    tipos_identificacion: list[TipoIdentificacionSalida]

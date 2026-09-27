"""Catálogos de apoyo para formularios (contracts/openapi.yaml §/v1/catalogos)."""

from dataclasses import dataclass
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.identificacion import NIF_IVA_ESTRUCTURAS
from app.domain.paises import codigos_pais
from app.domain.tipos import TipoIdentificacion
from app.models.provincia import Provincia
from app.repositories import catalogos as repo


@dataclass(frozen=True, slots=True)
class TipoIdentificacionInfo:
    codigo: TipoIdentificacion
    descripcion: str
    ambito: str


# Descripciones de la lista L7 (DsRegistroVeriFactu.xlsx v1.0, spec F-2) y ámbito (R-20.1).
TIPOS_IDENTIFICACION: Final = (
    TipoIdentificacionInfo(
        TipoIdentificacion.NIF, "NIF (DNI, NIE o NIF de entidad)", "solo_espana"
    ),
    TipoIdentificacionInfo(TipoIdentificacion.NIF_IVA, "NIF-IVA", "paises_nif_iva"),
    TipoIdentificacionInfo(TipoIdentificacion.PASAPORTE, "Pasaporte", "cualquiera"),
    TipoIdentificacionInfo(
        TipoIdentificacion.DOCUMENTO_OFICIAL,
        "Documento oficial de identificación del país de residencia",
        "fuera_de_espana",
    ),
    TipoIdentificacionInfo(
        TipoIdentificacion.CERTIFICADO_RESIDENCIA, "Certificado de residencia", "fuera_de_espana"
    ),
    TipoIdentificacionInfo(
        TipoIdentificacion.OTRO_DOCUMENTO, "Otro documento probatorio", "fuera_de_espana"
    ),
)


@dataclass(frozen=True, slots=True)
class Catalogos:
    provincias: list[Provincia]
    paises: tuple[str, ...]
    paises_nif_iva: tuple[str, ...]
    tipos_identificacion: tuple[TipoIdentificacionInfo, ...]


async def get_catalogos(session: AsyncSession) -> Catalogos:
    return Catalogos(
        provincias=await repo.list_provincias(session),
        paises=codigos_pais(),
        paises_nif_iva=tuple(sorted(NIF_IVA_ESTRUCTURAS)),
        tipos_identificacion=TIPOS_IDENTIFICACION,
    )

"""Esquemas de borradores de factura (contracts/openapi.yaml de 002). Las entradas NUNCA llevan
totales: los previstos los calcula el servidor al guardar (constitución VI, research R-9)."""

import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import Field

from app.schemas.comunes import EntradaBase, SalidaBase
from app.schemas.factura import ClienteFacturaSalida, LineaEntrada, OroInversion, TotalesSalida
from app.schemas.importes import CantidadSalida, ImporteSalida, TipoIvaSalida
from app.schemas.usuario import UsuarioReferencia


class BorradorEntrada(EntradaBase):
    """Un borrador puede guardarse incompleto: sin cliente o sin líneas (FR-011)."""

    fecha_expedicion: date
    cliente_id: uuid.UUID | None = None
    lineas: Annotated[list[LineaEntrada], Field(max_length=100)]
    oro_inversion: OroInversion = False  # al crear, por defecto con IVA


class BorradorEdicionEntrada(BorradorEntrada):
    """Editar y emitir: la casilla es obligatoria, para que omitirla no convierta en sujeto un
    borrador exento (research R-21)."""

    version: Annotated[int, Field(ge=1)]
    oro_inversion: OroInversion


class LineaBorradorSalida(SalidaBase):
    orden: int
    unidades: CantidadSalida
    descripcion: str
    precio_unitario: ImporteSalida
    importe: ImporteSalida


class BorradorSalida(SalidaBase):
    id: uuid.UUID
    version: int
    fecha_expedicion: date
    cliente: ClienteFacturaSalida | None
    lineas: list[LineaBorradorSalida]
    oro_inversion: bool
    mencion_exencion: Annotated[
        str | None, Field(description="Mención de F-6, art. 6.1.j (FR-052)")
    ]
    totales_previstos: TotalesSalida
    tipo_iva_previsto: Annotated[
        TipoIvaSalida, Field(description="IVA vigente cuando se guardó (aviso de cambio de IVA)")
    ]
    creado_en: datetime
    creado_por: UsuarioReferencia
    actualizado_en: datetime
    actualizado_por: UsuarioReferencia

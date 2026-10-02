"""Esquemas de borradores de presupuesto (contracts/openapi.yaml de 005). Las entradas NUNCA
llevan totales: los previstos los calcula el servidor al guardar (constitución VI)."""

import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import Field

from app.schemas.borrador import LineaBorradorSalida
from app.schemas.comunes import EntradaBase, SalidaBase
from app.schemas.factura import ClienteFacturaSalida, LineaEntrada, OroInversion, TotalesSalida
from app.schemas.importes import TipoIvaSalida
from app.schemas.usuario import UsuarioReferencia


class BorradorPresupuestoEntrada(EntradaBase):
    """Un borrador puede guardarse incompleto: sin cliente o sin líneas (FR-012)."""

    fecha: date
    valido_hasta: date
    cliente_id: uuid.UUID | None = None
    lineas: Annotated[list[LineaEntrada], Field(max_length=100)]
    oro_inversion: OroInversion = False


class BorradorPresupuestoEdicionEntrada(BorradorPresupuestoEntrada):
    """Editar y emitir: la casilla es obligatoria, como en el borrador de factura (002, R-21)."""

    version: Annotated[int, Field(ge=1)]
    oro_inversion: OroInversion


class BorradorPresupuestoSalida(SalidaBase):
    id: uuid.UUID
    version: int
    fecha: date
    valido_hasta: date
    cliente: ClienteFacturaSalida | None
    lineas: list[LineaBorradorSalida]
    oro_inversion: bool
    mencion_exencion: str | None
    totales_previstos: TotalesSalida
    tipo_iva_previsto: TipoIvaSalida
    creado_en: datetime
    creado_por: UsuarioReferencia
    actualizado_en: datetime
    actualizado_por: UsuarioReferencia

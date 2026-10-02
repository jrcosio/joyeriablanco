"""Esquemas de presupuestos (contracts/openapi.yaml de 005). Las entradas NUNCA llevan totales.

Constitución VI: el servidor calcula líneas, desglose y totales; `extra="forbid"` rechaza con 422
cualquier campo de más (FR-007). Los importes son texto (schemas/importes.py).
"""

import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import Field

from app.domain.tipos import EstadoPresupuesto, TipoCierrePresupuesto
from app.schemas.comunes import EntradaBase, SalidaBase
from app.schemas.configuracion_facturacion import DatosEmisorSalida
from app.schemas.factura import (
    ClienteFacturaSalida,
    FacturaReferencia,
    LineaEntrada,
    LineaSalida,
    MotivoTexto,
    OroInversion,
    TotalesSalida,
)
from app.schemas.importes import ImporteSalida, TipoIvaSalida
from app.schemas.usuario import UsuarioReferencia


class PresupuestoEntrada(EntradaBase):
    fecha: date
    valido_hasta: date
    cliente_id: uuid.UUID
    lineas: Annotated[list[LineaEntrada], Field(min_length=1, max_length=100)]
    oro_inversion: OroInversion = False


class ModificacionPresupuestoEntrada(EntradaBase):
    motivo_texto: MotivoTexto
    fecha: date
    valido_hasta: date
    cliente_id: uuid.UUID
    lineas: Annotated[list[LineaEntrada], Field(min_length=1, max_length=100)]
    # Obligatoria: omitirla no puede convertir en sujeto un presupuesto exento.
    oro_inversion: OroInversion


class AnulacionPresupuestoEntrada(EntradaBase):
    motivo_texto: MotivoTexto


class PresupuestoReferencia(SalidaBase):
    id: uuid.UUID
    num_serie: str
    fecha: Annotated[
        date,
        Field(description="Fecha mínima de expedición del borrador de factura vinculado (FR-019)"),
    ]


class CierrePresupuestoSalida(SalidaBase):
    tipo: TipoCierrePresupuesto
    motivo_texto: str | None
    creado_en: datetime
    creado_por: UsuarioReferencia
    presupuesto_nuevo: PresupuestoReferencia | None
    factura: FacturaReferencia | None
    factura_vigente: FacturaReferencia | None


class BorradorReferencia(SalidaBase):
    id: uuid.UUID


class PresupuestoSalida(SalidaBase):
    id: uuid.UUID
    num_serie: str
    estado: EstadoPresupuesto
    fecha: date
    valido_hasta: date
    emisor: DatosEmisorSalida
    cliente: ClienteFacturaSalida
    lineas: list[LineaSalida]
    totales: TotalesSalida
    oro_inversion: bool
    mencion_exencion: str | None
    sustituye_a: PresupuestoReferencia | None
    vigente_actual: PresupuestoReferencia | None
    cierre: CierrePresupuestoSalida | None
    borrador_factura: BorradorReferencia | None
    emitido_en: datetime
    emitido_por: UsuarioReferencia


class PresupuestoResumenSalida(SalidaBase):
    """Fila del listado (FR-024): un borrador no tiene número y sus totales son los previstos."""

    tipo_documento: Literal["borrador", "presupuesto"]
    id: uuid.UUID
    num_serie: str | None
    fecha: date
    valido_hasta: date
    cliente_nombre: str | None
    identificacion: str | None
    base: ImporteSalida
    cuota: ImporteSalida
    total: ImporteSalida
    estado: EstadoPresupuesto
    oro_inversion: bool


class ParametrosPresupuestoSalida(SalidaBase):
    iva_por_defecto: TipoIvaSalida
    emision_posible: bool
    faltan: list[str]
    proximo_numero: str
    hoy: date
    fecha_minima: date
    validez_dias: Annotated[int, Field(ge=1, le=365)]
    mencion_exencion_oro_inversion: str

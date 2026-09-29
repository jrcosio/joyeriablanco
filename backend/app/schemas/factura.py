"""Esquemas de facturas (contracts/openapi.yaml de 002). Las entradas NUNCA llevan totales.

Constitución VI: el servidor calcula líneas, desglose y totales; `extra="forbid"` rechaza con 422
cualquier campo de más (FR-014). Los importes son texto (schemas/importes.py, R-10).
"""

import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.domain.tipos import (
    CausaRectificacion,
    EstadoFactura,
    MotivoModificacion,
    TipoCorreccion,
    TipoFactura,
)
from app.schemas.comunes import EntradaBase, SalidaBase
from app.schemas.configuracion_facturacion import DatosEmisorSalida
from app.schemas.importes import (
    Cantidad,
    CantidadSalida,
    Importe,
    ImporteSalida,
    TipoIvaSalida,
)
from app.schemas.usuario import UsuarioReferencia

Descripcion = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
MotivoTexto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class LineaEntrada(EntradaBase):
    unidades: Cantidad
    descripcion: Descripcion
    precio_unitario: Importe


class FacturaEntrada(EntradaBase):
    fecha_expedicion: date
    cliente_id: uuid.UUID
    lineas: Annotated[list[LineaEntrada], Field(min_length=1, max_length=100)]


class AnulacionEntrada(EntradaBase):
    # Declaración obligatoria de que la factura no debió emitirse (FR-025): solo vale `true`.
    declaracion_no_debio_emitirse: Literal[True]
    motivo_texto: MotivoTexto


class ModificacionEntrada(EntradaBase):
    motivo: MotivoModificacion
    causa: CausaRectificacion | None = None
    motivo_texto: MotivoTexto
    cliente_id: uuid.UUID
    lineas: Annotated[list[LineaEntrada], Field(max_length=100)]
    # De la factura nueva (FR-018). Sin ella, la de hoy.
    fecha_expedicion: date | None = None


# ---------------------------------------------------------------------------- salida


class LineaSalida(SalidaBase):
    orden: int
    unidades: CantidadSalida
    descripcion: str
    precio_unitario: ImporteSalida
    tipo_iva: TipoIvaSalida
    importe: ImporteSalida


class DesgloseSalida(SalidaBase):
    tipo_iva: TipoIvaSalida
    base: ImporteSalida
    cuota: ImporteSalida


class TotalesSalida(SalidaBase):
    desglose: list[DesgloseSalida]
    base_total: ImporteSalida
    cuota_total: ImporteSalida
    importe_total: ImporteSalida


class ClienteFacturaSalida(SalidaBase):
    id: uuid.UUID
    nombre: str
    identificacion_pais: str
    identificacion_tipo: str
    identificacion_numero: str
    direccion: str | None
    codigo_postal: str | None
    localidad: str | None
    provincia: str | None
    pais: str
    activo: bool | None = None


class FacturaReferencia(SalidaBase):
    id: uuid.UUID
    num_serie: str


class RegistroResumen(SalidaBase):
    tipo: str
    secuencia: int
    huella: str
    fecha_hora_huso_gen: str
    estado_remision: str


class CorreccionSalida(SalidaBase):
    tipo: TipoCorreccion
    motivo: MotivoModificacion
    motivo_texto: str
    creada_en: datetime
    creada_por: UsuarioReferencia
    factura_nueva: FacturaReferencia | None
    en_vigor: bool


class RectificaA(SalidaBase):
    factura: FacturaReferencia
    base_rectificada: ImporteSalida
    cuota_rectificada: ImporteSalida
    causa: CausaRectificacion


class FacturaSalida(SalidaBase):
    id: uuid.UUID
    num_serie: str
    tipo_factura: TipoFactura
    tipo_rectificativa: str | None
    estado: EstadoFactura
    fecha_expedicion: date
    fecha_operacion: date | None
    emisor: DatosEmisorSalida
    cliente: ClienteFacturaSalida
    lineas: list[LineaSalida]
    totales: TotalesSalida
    descripcion_operacion: str
    rectifica_a: RectificaA | None
    sustituye_a: FacturaReferencia | None
    vigente_actual: FacturaReferencia | None
    correcciones: list[CorreccionSalida]
    emitida_en: datetime
    emitida_por: UsuarioReferencia
    registros: list[RegistroResumen]


class FacturaResumenSalida(SalidaBase):
    """Fila del listado (FR-033): un borrador no tiene número y sus totales son los previstos."""

    tipo_documento: Literal["borrador", "factura"]
    id: uuid.UUID
    num_serie: str | None
    fecha: date
    cliente_nombre: str | None
    identificacion: str | None
    base: ImporteSalida
    cuota: ImporteSalida
    total: ImporteSalida
    estado: EstadoFactura

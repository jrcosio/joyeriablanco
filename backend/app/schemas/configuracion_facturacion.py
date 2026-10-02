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
    # Opcional (research R-22). Admite espacios: se normaliza en el servicio.
    iban: Annotated[TextoOpcional, Field(max_length=42)] | None = None


class ContactoEntrada(EntradaBase):
    """Contacto no fiscal de la joyería, impreso en las facturas (003, FR-024; R-9)."""

    telefono: Annotated[TextoOpcional, Field(max_length=30)] | None = None
    correo: Annotated[TextoOpcional, Field(max_length=254)] | None = None
    web: Annotated[TextoOpcional, Field(max_length=200)] | None = None


class ConfiguracionFacturacionEntrada(EntradaBase):
    """Sin clave de régimen: la fija el sistema, 01 o 04 (research R-23).

    `contacto` y `pie_factura` (003), y `validez_presupuesto_dias` y `pie_presupuesto` (005), son
    opcionales: si no vienen, se conservan los actuales.
    """

    version: Annotated[int, Field(ge=1)]
    iva_por_defecto: TipoIvaEntrada
    # Confirma un tipo nuevo fuera de la lista oficial de hoy (research R-20).
    confirmar_tipo_iva: bool = False
    modalidad: Modalidad | None
    emisor: DatosEmisorEntrada
    contacto: ContactoEntrada | None = None
    pie_factura: Annotated[str, Field(max_length=600)] | None = None
    validez_presupuesto_dias: Annotated[int, Field(ge=1, le=365)] | None = None
    pie_presupuesto: Annotated[str, Field(max_length=600)] | None = None


class DatosEmisorSalida(SalidaBase):
    nombre: str | None
    nif: str | None
    direccion: str | None
    codigo_postal: str | None
    localidad: str | None
    iban: str | None
    provincia: str | None


class ContactoSalida(SalidaBase):
    telefono: str | None
    correo: str | None
    web: str | None


class ConfiguracionFacturacionSalida(SalidaBase):
    version: int
    iva_por_defecto: TipoIvaSalida
    modalidad: Modalidad | None
    emisor: DatosEmisorSalida
    emision_posible: bool
    faltan: list[str]
    proximo_numero: str
    modalidad_bloqueada: bool
    tipos_iva_oficiales: Annotated[
        list[TipoIvaSalida],
        Field(description="Lista de F-3 §15.1 para hoy. Solo para el aviso (research R-20)"),
    ]
    actualizado_en: datetime
    actualizado_por: UsuarioReferencia | None
    contacto: ContactoSalida
    pie_factura: str | None
    validez_presupuesto_dias: int
    pie_presupuesto: str | None


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
    mencion_exencion_oro_inversion: str

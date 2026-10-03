"""Contenido común de facturas y presupuestos: líneas, totales y copias de las partes (005, R-8).

Se extrajo de `emision.py` y `borradores.py` sin cambiar su comportamiento, para que los
presupuestos usen exactamente las mismas reglas de líneas e importes que las facturas (FR-007) y
la misma copia del emisor y del destinatario (FR-010).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Final, Protocol

from app.core.errors import CampoError, DatosNoValidos
from app.domain.importes import (
    MAX_LINEAS,
    MAX_PRECIO,
    MAX_UNIDADES,
    ImporteFueraDeRango,
    LineaCalculo,
    Totales,
    compute_totals,
)
from app.models.cliente import Cliente
from app.models.configuracion_facturacion import ConfiguracionFacturacion

CENTIMO: Final = Decimal("0.01")
SIN_LINEAS: Final = "La factura debe tener al menos una línea."


@dataclass(frozen=True, slots=True)
class DatosLinea:
    unidades: Decimal
    descripcion: str
    precio_unitario: Decimal


def check_lineas(
    lineas: tuple[DatosLinea, ...], *, permitir_vacio: bool = False, sin_lineas: str = SIN_LINEAS
) -> None:
    errores: list[CampoError] = []
    if not lineas and not permitir_vacio:
        errores.append(CampoError("lineas", sin_lineas))
    if len(lineas) > MAX_LINEAS:
        errores.append(CampoError("lineas", f"Como máximo {MAX_LINEAS} líneas."))
    for i, linea in enumerate(lineas):
        if not linea.descripcion.strip():
            errores.append(CampoError(f"lineas.{i}.descripcion", "Campo obligatorio."))
        if linea.unidades > MAX_UNIDADES:
            errores.append(CampoError(f"lineas.{i}.unidades", "Demasiadas unidades."))
        if linea.precio_unitario > MAX_PRECIO:
            errores.append(CampoError(f"lineas.{i}.precio_unitario", "Precio demasiado alto."))
    if errores:
        raise DatosNoValidos(errores=errores)


def normalize_lineas(lineas: tuple[DatosLinea, ...]) -> tuple[DatosLinea, ...]:
    """Unidades y precio al céntimo y descripción sin espacios en los extremos."""
    return tuple(
        DatosLinea(
            unidades=linea.unidades.quantize(CENTIMO),
            descripcion=linea.descripcion.strip(),
            precio_unitario=linea.precio_unitario.quantize(CENTIMO),
        )
        for linea in lineas
    )


def calcular_totales(lineas: tuple[DatosLinea, ...], tipo_iva: Decimal | None) -> Totales:
    """Totales con la política única de `domain/importes.py`. `tipo_iva=None`: oro de inversión."""
    try:
        return compute_totals(
            [LineaCalculo(linea.unidades, linea.precio_unitario, tipo_iva) for linea in lineas],
            tipo_iva_por_defecto=tipo_iva,
        )
    except ImporteFueraDeRango as exc:
        raise DatosNoValidos(errores=[CampoError("lineas", str(exc))]) from exc


def previstos(lineas: tuple[DatosLinea, ...], tipo_iva: Decimal | None) -> Totales:
    """Totales PREVISTOS de un borrador, que puede estar sin líneas (002, R-9; 005, FR-012)."""
    check_lineas(lineas, permitir_vacio=True)
    return calcular_totales(lineas, tipo_iva)


class LineaConContenido(Protocol):
    """Lo editable de una línea: lo cumplen `DatosLinea` y las líneas de los borradores."""

    @property
    def unidades(self) -> Decimal: ...
    @property
    def descripcion(self) -> str: ...
    @property
    def precio_unitario(self) -> Decimal: ...


def lineas_json(lineas: Sequence[LineaConContenido]) -> list[object]:
    """Las líneas como datos de auditoría (unidades, descripción y precio)."""
    return [
        {
            "unidades": linea.unidades,
            "descripcion": linea.descripcion,
            "precio_unitario": linea.precio_unitario,
        }
        for linea in lineas
    ]


def copia_emisor(config: ConfiguracionFacturacion) -> dict[str, str | None]:
    """Copia del emisor al emitir, IBAN incluido (002, FR-016; 005, FR-010).

    Exige los datos del emisor completos: quien llama lo comprueba antes.
    """
    return {
        "emisor_nif": config.emisor_nif,
        "emisor_nombre": config.emisor_nombre,
        "emisor_direccion": config.emisor_direccion,
        "emisor_codigo_postal": config.emisor_codigo_postal,
        "emisor_localidad": config.emisor_localidad,
        "emisor_provincia": config.emisor_provincia.nombre_visible
        if config.emisor_provincia
        else None,
        "emisor_iban": config.emisor_iban,
    }


def copia_destinatario(cliente: Cliente) -> dict[str, str | None]:
    """Copia del destinatario al emitir (002, FR-016; 005, FR-010)."""
    provincia = (
        cliente.provincia.nombre_visible
        if cliente.provincia is not None
        else cliente.provincia_texto
    )
    return {
        "dest_nombre": cliente.nombre,
        "dest_identificacion_pais": cliente.identificacion_pais,
        "dest_identificacion_tipo": cliente.identificacion_tipo,
        "dest_identificacion_numero": cliente.identificacion_numero,
        "dest_direccion": cliente.direccion,
        "dest_codigo_postal": cliente.codigo_postal,
        "dest_localidad": cliente.localidad,
        "dest_provincia": provincia,
        "dest_pais": cliente.pais_residencia,
    }

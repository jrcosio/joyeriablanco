"""Piezas comunes de los documentos impresos: factura y presupuesto (005, research R-8).

Se extrajeron de `services/impresion.py` (003) sin cambiar su comportamiento. Los modelos de vista
son inmutables y llevan el texto ya formateado: las plantillas solo pintan. Las copias del emisor
y del destinatario tienen los mismos nombres en `Factura` y en `Presupuesto` (`CopiaPartes`), así
que se componen igual.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Final, Protocol

from app.core.pdf import plantillas, render
from app.domain.formato import (
    format_euros,
    format_identificacion,
    format_porcentaje,
    format_unidades,
    format_web,
    nombre_pais,
)
from app.models.configuracion_facturacion import ConfiguracionFacturacion


@dataclass(frozen=True, slots=True)
class DocumentoPdf:
    nombre: str
    contenido: bytes


# ------------------------------------------------------------------ modelos de vista


@dataclass(frozen=True, slots=True)
class ParteImpresa:
    nombre: str
    identificacion: str
    domicilio: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ContactoImpreso:
    telefono: str | None
    correo: str | None
    web: str | None

    @property
    def vacio(self) -> bool:
        return not (self.telefono or self.correo or self.web)


@dataclass(frozen=True, slots=True)
class LineaImpresa:
    unidades: str
    descripcion: str
    precio_unitario: str
    importe: str


@dataclass(frozen=True, slots=True)
class DesgloseImpreso:
    etiqueta_base: str
    base: str
    etiqueta_cuota: str
    cuota: str


# ------------------------------------------------------------------ copias guardadas


class CopiaPartes(Protocol):
    """Copia del emisor y del destinatario guardada al emitir: la cumplen factura y presupuesto.

    Solo lectura y con el domicilio opcional, para que mypy acepte los dos aunque en la factura el
    domicilio del destinatario sea obligatorio (research R-8).
    """

    @property
    def emisor_nombre(self) -> str: ...
    @property
    def emisor_nif(self) -> str: ...
    @property
    def emisor_direccion(self) -> str: ...
    @property
    def emisor_codigo_postal(self) -> str: ...
    @property
    def emisor_localidad(self) -> str: ...
    @property
    def emisor_provincia(self) -> str | None: ...
    @property
    def dest_nombre(self) -> str: ...
    @property
    def dest_identificacion_tipo(self) -> str: ...
    @property
    def dest_identificacion_pais(self) -> str: ...
    @property
    def dest_identificacion_numero(self) -> str: ...
    @property
    def dest_direccion(self) -> str | None: ...
    @property
    def dest_codigo_postal(self) -> str | None: ...
    @property
    def dest_localidad(self) -> str | None: ...
    @property
    def dest_provincia(self) -> str | None: ...
    @property
    def dest_pais(self) -> str: ...


class LineaGuardada(Protocol):
    @property
    def orden(self) -> int: ...
    @property
    def unidades(self) -> Decimal: ...
    @property
    def descripcion(self) -> str: ...
    @property
    def precio_unitario(self) -> Decimal: ...
    @property
    def importe(self) -> Decimal: ...


class DesgloseGuardado(Protocol):
    @property
    def orden(self) -> int: ...
    @property
    def tipo_iva(self) -> Decimal | None: ...
    @property
    def base(self) -> Decimal: ...
    @property
    def cuota(self) -> Decimal: ...


# ------------------------------------------------------------------------ composición


def domicilio(
    direccion: str | None,
    codigo_postal: str | None,
    localidad: str | None,
    provincia: str | None,
    pais: str | None = None,
) -> tuple[str, ...]:
    lineas = [
        direccion,
        " ".join(p for p in (codigo_postal, localidad) if p) or None,
        provincia,
        nombre_pais(pais) if pais and pais.upper() != "ES" else None,
    ]
    return tuple(linea for linea in lineas if linea)


def emisor(d: CopiaPartes) -> ParteImpresa:
    return ParteImpresa(
        nombre=d.emisor_nombre,
        identificacion=f"NIF {d.emisor_nif}",
        domicilio=domicilio(
            d.emisor_direccion, d.emisor_codigo_postal, d.emisor_localidad, d.emisor_provincia
        ),
    )


def destinatario(d: CopiaPartes) -> ParteImpresa:
    return ParteImpresa(
        nombre=d.dest_nombre,
        identificacion=format_identificacion(
            d.dest_identificacion_tipo, d.dest_identificacion_pais, d.dest_identificacion_numero
        ),
        domicilio=domicilio(
            d.dest_direccion, d.dest_codigo_postal, d.dest_localidad, d.dest_provincia, d.dest_pais
        ),
    )


def contacto(config: ConfiguracionFacturacion) -> ContactoImpreso:
    return ContactoImpreso(
        telefono=config.emisor_telefono,
        correo=config.emisor_correo,
        web=format_web(config.emisor_web) if config.emisor_web else None,
    )


def lineas_impresas(lineas: Iterable[LineaGuardada]) -> tuple[LineaImpresa, ...]:
    return tuple(
        LineaImpresa(
            unidades=format_unidades(linea.unidades),
            descripcion=linea.descripcion,
            precio_unitario=format_euros(linea.precio_unitario),
            importe=format_euros(linea.importe),
        )
        for linea in sorted(lineas, key=lambda linea: linea.orden)
    )


def desglose_impreso(desgloses: Iterable[DesgloseGuardado]) -> tuple[DesgloseImpreso, ...]:
    desglose: list[DesgloseImpreso] = []
    for d in sorted(desgloses, key=lambda d: d.orden):
        if d.tipo_iva is None:  # base exenta de oro de inversión (002, FR-052)
            desglose.append(
                DesgloseImpreso("Base exenta", format_euros(d.base), "IVA", format_euros(d.cuota))
            )
        else:
            tipo = format_porcentaje(d.tipo_iva)
            desglose.append(
                DesgloseImpreso(
                    f"Base imponible al {tipo}",
                    format_euros(d.base),
                    f"IVA {tipo}",
                    format_euros(d.cuota),
                )
            )
    return tuple(desglose)


# ---------------------------------------------------------------------------- listado

# Máximo de filas del listado impreso (003, FR-018; 005, FR-030). La web lo repite para desactivar
# el botón (`lib/impresion.ts`), y aquí se exige siempre.
LIMITE_LISTADO_IMPRESO: Final = 5000

# Los textos del selector de orden de la web (`FiltrosDocumentos.tsx`).
TEXTO_ORDEN: Final = {
    "recientes": "Más recientes",
    "antiguas": "Más antiguas",
    "total_desc": "Total mayor",
    "total_asc": "Total menor",
}


@dataclass(frozen=True, slots=True)
class TextosListado:
    """Lo que cambia entre el listado de facturas y el de presupuestos (005, documentos-pdf)."""

    titulo: str
    sin_filas: str
    titulo_totales: str


@dataclass(frozen=True, slots=True)
class FiltroImpreso:
    busqueda: str
    anio: str
    mes: str
    orden: str


@dataclass(frozen=True, slots=True)
class FilaImpresa:
    numero: str
    marca: str | None
    fecha: str
    cliente: str
    identificacion: str
    base: str
    iva: str
    total: str


@dataclass(frozen=True, slots=True)
class ImportesImpresos:
    etiqueta: str
    base: str
    cuota: str
    total: str


@dataclass(frozen=True, slots=True)
class ListadoImpreso:
    emisor_nombre: str | None
    filtro: FiltroImpreso
    resumen: str
    filas: tuple[FilaImpresa, ...]
    desglose: tuple[ImportesImpresos, ...]
    totales: ImportesImpresos
    excluidas: str | None
    nombre_fichero: str
    textos: TextosListado


def cuenta(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def enumerar(partes: list[str]) -> str:
    return partes[0] if len(partes) == 1 else f"{', '.join(partes[:-1])} y {partes[-1]}"


def importes(etiqueta: str, base: Decimal, cuota: Decimal) -> ImportesImpresos:
    return ImportesImpresos(
        etiqueta=etiqueta,
        base=format_euros(base),
        cuota=format_euros(cuota),
        total=format_euros(base + cuota),
    )


def nombre_fichero(prefijo: str, anio: int | None, mes: int | None) -> str:
    periodo = "todos" if anio is None else str(anio)
    return f"{prefijo}-{periodo}-{mes:02d}.pdf" if mes else f"{prefijo}-{periodo}.pdf"


def html_bloque(
    modelo: ListadoImpreso,
    inicio: int,
    fin: int,
    primero: bool,
    ultimo: bool,
    paginacion: render.Paginacion | None,
) -> str:
    return plantillas.render_html(
        "listado.html",
        {
            "l": modelo,
            "filas": modelo.filas[inicio:fin],
            "cabecera": primero,
            "totales": ultimo,
            "paginacion": paginacion,
        },
    )


def pdf_listado(modelo: ListadoImpreso) -> bytes:
    return render.pdf_por_bloques(
        len(modelo.filas),
        lambda inicio, fin, primero, ultimo, paginacion: html_bloque(
            modelo, inicio, fin, primero, ultimo, paginacion
        ),
        titulo=modelo.textos.titulo,
        autor=modelo.emisor_nombre or "Joyería Blanco",
    )

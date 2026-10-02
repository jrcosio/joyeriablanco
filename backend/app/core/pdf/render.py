"""Renderizado de PDF con WeasyPrint (003, research R-4 y R-7).

WeasyPrint es síncrono y usa mucha CPU. Cada generación corre en un hilo, para no bloquear el bucle
de eventos, y bajo un limitador por proceso: 4 facturas y 1 listado a la vez. Así la memoria queda
acotada aunque varias personas impriman al mismo tiempo.

El listado se maqueta por bloques (`pdf_por_bloques`): un documento único de 5.000 filas llega a
unos 750 MB, y por bloques de 500 se queda en unos 270 MB (R-7). El pie se pinta
en cada bloque con su desfase; superponerlo después con pypdf duplicaba la fuente en cada página.
"""

import io
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

import anyio
import anyio.to_thread
from pypdf import PdfReader, PdfWriter
from weasyprint import HTML, Document
from weasyprint.text.fonts import FontConfiguration

from app.core.pdf.plantillas import directorio_recursos

LIMITE_FACTURAS: Final = anyio.CapacityLimiter(4)
LIMITE_LISTADOS: Final = anyio.CapacityLimiter(1)
# Filas por bloque (R-7). Medido en el contenedor con 5.000 filas: 1.000 → 381 MB de pico,
# 500 → 266 MB, 300 → 224 MB, con unos 19 s en los tres casos. Los tests lo reducen.
TAMANO_BLOQUE_LISTADO = 500


def html_a_documento(html: str) -> Document:
    """Maqueta el HTML. Las fuentes `@font-face` se resuelven contra `app/resources`."""
    return HTML(string=html, base_url=str(directorio_recursos()) + "/").render(
        font_config=FontConfiguration()
    )


def html_a_pdf(html: str) -> bytes:
    pdf: bytes = html_a_documento(html).write_pdf()
    return pdf


async def en_hilo[T](funcion: Callable[[], T], limitador: anyio.CapacityLimiter) -> T:
    return await anyio.to_thread.run_sync(funcion, limiter=limitador)


def _cajas(caja: Any) -> list[Any]:
    cajas = [caja]
    for hija in getattr(caja, "children", None) or []:
        cajas += _cajas(hija)
    return cajas


def _filas_en(pagina: Any) -> int:
    """Filas de datos (no de cabecera) de una tabla maquetadas en una página."""
    return sum(
        len(caja.children)
        for caja in _cajas(pagina._page_box)
        if type(caja).__name__ == "TableRowGroupBox" and not caja.is_header and not caja.is_footer
    )


@dataclass(frozen=True, slots=True)
class Paginacion:
    """Pie «Página n de m» de un bloque: su primera página es la `primera` de `total`."""

    primera: int
    total: int


def pdf_por_bloques(
    filas: int,
    html_bloque: Callable[[int, int, bool, bool, Paginacion | None], str],
    *,
    titulo: str,
    autor: str,
) -> bytes:
    """Maqueta un listado de `filas` filas por bloques, con el pie «Página n de m» exacto.

    `html_bloque(inicio, fin, primero, ultimo, paginacion)` es el HTML de las filas `[inicio, fin)`,
    con la cabecera del listado si es el primero y los totales si es el último. Con `paginacion`
    `None`, el pie usa los contadores propios del documento (`counter(pages)`).

    - Si cabe en un bloque (hasta `TAMANO_BLOQUE_LISTADO` filas), una sola pasada.
    - Si no, una primera pasada de maquetación fija los límites de cada bloque: de cada bloque que
      no es el último solo cuentan sus páginas completas, y las filas de su última página pasan al
      siguiente, así que ninguna página intermedia queda a medias. La segunda pasada escribe cada
      bloque con el número de su primera página y el total ya conocido.
    """
    limites: list[tuple[int, int, int]] = []  # (inicio, fin, páginas)
    inicio, tamano = 0, TAMANO_BLOQUE_LISTADO
    while True:
        fin = min(inicio + tamano, filas)
        ultimo = fin >= filas
        documento = html_a_documento(html_bloque(inicio, fin, inicio == 0, ultimo, None))
        if ultimo and not limites:  # un solo bloque: ya está listo
            pdf: bytes = documento.write_pdf()
            return pdf
        if ultimo:
            limites.append((inicio, fin, len(documento.pages)))
            break
        if len(documento.pages) < 2:  # el bloque cabe en una página: se amplía
            tamano *= 2
            continue
        completas = documento.pages[:-1]
        consumidas = sum(_filas_en(pagina) for pagina in completas)
        limites.append((inicio, inicio + consumidas, len(completas)))
        inicio += consumidas
    total = sum(paginas for _, _, paginas in limites)
    escritor = PdfWriter()
    primera = 1
    for inicio, fin, paginas in limites:
        documento = html_a_documento(
            html_bloque(inicio, fin, inicio == 0, fin >= filas, Paginacion(primera, total))
        )
        if len(documento.pages) != paginas:
            msg = f"El bloque {inicio}-{fin} tiene {len(documento.pages)} páginas y no {paginas}"
            raise RuntimeError(msg)
        escritor.append(PdfReader(io.BytesIO(documento.write_pdf())))
        primera += paginas
    escritor.add_metadata({"/Title": titulo, "/Author": autor})
    salida = io.BytesIO()
    escritor.write(salida)
    return salida.getvalue()

"""Renderizado de PDF con WeasyPrint (003, research R-4 y R-7).

WeasyPrint es síncrono y usa mucha CPU. Cada generación corre en un hilo, para no bloquear el bucle
de eventos, y bajo un limitador por proceso: 4 facturas y 1 listado a la vez. Así la memoria queda
acotada aunque varias personas impriman al mismo tiempo.

El listado se maqueta por bloques (`pdf_por_bloques`): un documento único de 5.000 filas llega a
unos 750 MB, y por bloques de 1.000 se queda en unos 250 MB (prueba previa de R-7).
"""

import io
from collections.abc import Callable
from typing import Any, Final

import anyio
import anyio.to_thread
from pypdf import PdfReader, PdfWriter
from weasyprint import HTML, Document
from weasyprint.text.fonts import FontConfiguration

from app.core.pdf.plantillas import directorio_recursos

LIMITE_FACTURAS: Final = anyio.CapacityLimiter(4)
LIMITE_LISTADOS: Final = anyio.CapacityLimiter(1)
TAMANO_BLOQUE_LISTADO = 1000  # filas por bloque (R-7); los tests lo reducen


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


def pdf_por_bloques(
    filas: int,
    html_bloque: Callable[[int, int, bool, bool], str],
    html_pie: Callable[[int], str],
    *,
    titulo: str,
    autor: str,
) -> bytes:
    """Maqueta un listado de `filas` filas por bloques y le superpone el pie «Página n de m».

    - `html_bloque(inicio, fin, primero, ultimo)` es el HTML de las filas `[inicio, fin)`: con la
      cabecera del listado si es el primero y con los totales si es el último.
    - De cada bloque que no es el último solo se escriben sus páginas completas. Las filas de su
      última página pasan al siguiente bloque, así que ninguna página intermedia queda a medias.
    - `html_pie(m)` es un documento de `m` páginas con solo el pie; se superpone a cada página.
    """
    escritor = PdfWriter()
    inicio, tamano = 0, TAMANO_BLOQUE_LISTADO
    while True:
        fin = min(inicio + tamano, filas)
        ultimo = fin >= filas
        documento = html_a_documento(html_bloque(inicio, fin, inicio == 0, ultimo))
        if ultimo:
            paginas, consumidas = documento.pages, fin - inicio
        elif len(documento.pages) < 2:  # el bloque cabe en una página: se amplía
            tamano *= 2
            continue
        else:
            paginas = documento.pages[:-1]
            consumidas = sum(_filas_en(pagina) for pagina in paginas)
        escritor.append(PdfReader(io.BytesIO(documento.copy(paginas).write_pdf())))
        inicio += consumidas
        if ultimo:
            break
    total = len(escritor.pages)
    pie = PdfReader(io.BytesIO(html_a_pdf(html_pie(total))))
    if len(pie.pages) != total:
        msg = f"El pie tiene {len(pie.pages)} páginas y el listado {total}"
        raise RuntimeError(msg)
    for pagina, pie_pagina in zip(escritor.pages, pie.pages, strict=True):
        pagina.merge_page(pie_pagina)
        pagina.compress_content_streams()  # sin esto, el PDF unido pesa 10 veces más
    escritor.add_metadata({"/Title": titulo, "/Author": autor})
    salida = io.BytesIO()
    escritor.write(salida)
    return salida.getvalue()

"""Renderizado de PDF con WeasyPrint (003, research R-4 y R-7).

WeasyPrint es síncrono y usa mucha CPU. Cada generación corre en un hilo, para no bloquear el bucle
de eventos, y bajo un limitador por proceso: 4 facturas y 1 listado a la vez. Así la memoria queda
acotada aunque varias personas impriman al mismo tiempo.
"""

from collections.abc import Callable
from typing import Final

import anyio
import anyio.to_thread
from weasyprint import HTML, Document
from weasyprint.text.fonts import FontConfiguration

from app.core.pdf.plantillas import directorio_recursos

LIMITE_FACTURAS: Final = anyio.CapacityLimiter(4)
LIMITE_LISTADOS: Final = anyio.CapacityLimiter(1)


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

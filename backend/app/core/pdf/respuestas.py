"""Respuestas HTTP de las rutas de PDF (003, research R-8).

- El PDF se sirve `inline`, con nombre de fichero, y con una CSP propia que deja abrirlo en el
  visor integrado del navegador (`object-src 'self'`). La CSP global de la SPA lleva
  `object-src 'none'`, y Caddy no se la aplica a estas rutas (deploy/caddy/Caddyfile).
- Si la petición es una navegación de documento (la pestaña nueva que abre «Imprimir»), los errores
  se devuelven como una página HTML en español, sin datos técnicos (FR-028). El resto de clientes
  de la API sigue recibiendo `application/problem+json`.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from fastapi import Request, Response
from fastapi.responses import HTMLResponse

from app.core.pdf import plantillas

CSP_PDF: Final = (
    "default-src 'none'; object-src 'self'; frame-ancestors 'none'; base-uri 'none'; "
    "form-action 'none'"
)
TITULO_ERROR: Final = "No se ha podido abrir el PDF"


def csp_error() -> str:
    return (
        f"default-src 'none'; style-src {plantillas.hash_estilo_error()}; "
        "frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    )


def respuesta_pdf(nombre: str, contenido: bytes) -> Response:
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{nombre}"',
            "Content-Security-Policy": CSP_PDF,
        },
    )


def es_ruta_pdf(request: Request) -> bool:
    ruta = request.url.path
    return ruta.startswith("/api/v1/") and ruta.endswith("/pdf")


def es_navegacion_pdf(request: Request) -> bool:
    """¿Es la pestaña nueva de «Imprimir» pidiendo uno de los PDF?"""
    if not es_ruta_pdf(request):
        return False
    destino = request.headers.get("sec-fetch-dest")
    if destino is not None:
        return destino == "document"
    return "text/html" in request.headers.get("accept", "")


@dataclass(frozen=True, slots=True)
class _Documento:
    no_existe: str
    enlace: str
    texto_enlace: str


_FACTURAS = _Documento("La factura no existe.", "/facturas", "Volver a las facturas")
_PRESUPUESTOS = _Documento(
    "El presupuesto no existe.", "/presupuestos", "Volver a los presupuestos"
)  # 005, contracts/documentos-pdf.md


def _documento(ruta: str) -> _Documento:
    return _PRESUPUESTOS if ruta.startswith("/api/v1/presupuestos/") else _FACTURAS


def _mensaje(cuerpo: Mapping[str, Any], status: int, ruta: str) -> tuple[str, str, str]:
    """(mensaje, enlace, texto del enlace) para cada error posible (R-8), según el documento."""
    tipo = str(cuerpo.get("type", "")).removeprefix("/problemas/")
    doc = _documento(ruta)
    if status == 401:
        return (
            "Tu sesión ha caducado. Vuelve a la aplicación e inicia sesión de nuevo.",
            "/",
            "Volver a la aplicación",
        )
    if status == 404:
        return doc.no_existe, doc.enlace, doc.texto_enlace
    if tipo in {
        "duplicado-no-disponible",
        "listado-demasiado-grande",
        "sin-permiso",
        "contrasena-temporal",
    }:
        return str(cuerpo.get("detail", "")), doc.enlace, doc.texto_enlace
    if status == 422:
        return (
            "Los datos de la petición no son válidos. Vuelve a imprimir desde la aplicación.",
            doc.enlace,
            doc.texto_enlace,
        )
    return (
        "No se ha podido generar el PDF. Vuelve a intentarlo dentro de un momento.",
        doc.enlace,
        doc.texto_enlace,
    )


def pagina_error(cuerpo: Mapping[str, Any], status: int, ruta: str) -> HTMLResponse:
    mensaje, enlace, texto_enlace = _mensaje(cuerpo, status, ruta)
    html = plantillas.render_error(
        titulo=TITULO_ERROR, mensaje=mensaje, enlace=enlace, texto_enlace=texto_enlace
    )
    return HTMLResponse(html, status_code=status, headers={"Content-Security-Policy": csp_error()})

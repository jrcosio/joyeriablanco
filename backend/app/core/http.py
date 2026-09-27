"""Utilidades HTTP transversales: request id, log de acceso sin query, caché y origen.

La IP del cliente es `request.client.host`. Detrás de Caddy, uvicorn la toma de
`X-Forwarded-For` gracias a `--proxy-headers`, y solo confía en la red interna (research R-8).
"""

import logging
import secrets
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import FastAPI, Request, Response

from app.core.config import get_settings
from app.core.errors import OrigenNoPermitido
from app.core.logging import request_id_var

logger = logging.getLogger("app.acceso")

MAX_AGENTE = 500


@dataclass(frozen=True, slots=True)
class Origen:
    """Procedencia de una petición, para la auditoría y el límite por origen."""

    ip: str | None
    agente: str | None


def request_origin(request: Request) -> Origen:
    agente = request.headers.get("user-agent")
    return Origen(
        ip=request.client.host if request.client else None,
        agente=agente[:MAX_AGENTE] if agente else None,
    )


def check_origin(request: Request) -> None:
    """Rechaza peticiones que modifican datos sin un `Origin` permitido (research R-6)."""
    origen = request.headers.get("origin")
    if origen is None or origen != get_settings().origen_permitido:
        raise OrigenNoPermitido


def register_middlewares(app: FastAPI) -> None:
    @app.middleware("http")
    async def _contexto(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id") or secrets.token_hex(8)
        token = request_id_var.set(request_id[:64])
        inicio = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        duracion_ms = round((time.perf_counter() - inicio) * 1000, 1)
        response.headers["X-Request-Id"] = request_id[:64]
        if request.url.path.startswith("/api/v1"):
            response.headers["Cache-Control"] = "no-store"
        token = request_id_var.set(request_id[:64])
        try:
            logger.info(
                "%s %s %s",
                request.method,
                request.url.path,  # sin query string (puede contener datos personales)
                response.status_code,
                extra={"estado": response.status_code, "duracion_ms": duracion_ms},
            )
        finally:
            request_id_var.reset(token)
        return response

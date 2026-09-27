"""Registro técnico en JSON a stdout, sin secretos ni datos personales (FR-053).

- Cada línea incluye `request_id` (contexto de la petición en curso).
- Un filtro redacta los campos `extra` cuyo nombre sugiere un secreto o un dato personal.
- El log de acceso de uvicorn se desactiva: registraría la query string, que puede contener un
  NIF buscado. El middleware de `app.core.http` registra un acceso propio sin query.
"""

import logging
import sys
from contextvars import ContextVar
from typing import Final, override

from pythonjsonlogger.json import JsonFormatter

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

CLAVES_SENSIBLES: Final = frozenset(
    {
        "password",
        "contrasena",
        "contrasena_actual",
        "contrasena_nueva",
        "contrasena_temporal",
        "hash_contrasena",
        "token",
        "csrf_token",
        "cookie",
        "authorization",
        "identificacion_numero",
        "nif",
        "correo",
        "telefono",
        "direccion",
        "nombre",
        "observaciones",
        "q",
    }
)
REDACTADO: Final = "[redactado]"

# Atributos estándar de LogRecord que no son `extra`.
_ATRIBUTOS_ESTANDAR: Final = frozenset(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__.keys() | {"message", "asctime"}
)


class RedactionFilter(logging.Filter):
    """Añade `request_id` y redacta los `extra` sensibles."""

    @override
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.__dict__.pop("color_message", None)  # duplicado con códigos ANSI de uvicorn
        for clave in list(record.__dict__):
            if clave not in _ATRIBUTOS_ESTANDAR and clave.lower() in CLAVES_SENSIBLES:
                setattr(record, clave, REDACTADO)
        return True


def configure_logging(nivel: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"asctime": "fecha", "levelname": "nivel", "name": "logger"},
        )
    )
    handler.addFilter(RedactionFilter())
    raiz = logging.getLogger()
    raiz.handlers[:] = [handler]
    raiz.setLevel(nivel)
    for nombre in ("uvicorn", "uvicorn.error"):
        logging.getLogger(nombre).handlers[:] = []
        logging.getLogger(nombre).propagate = True
    acceso = logging.getLogger("uvicorn.access")
    acceso.handlers[:] = []
    acceso.propagate = False
    acceso.disabled = True

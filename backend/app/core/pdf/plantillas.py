"""Plantillas Jinja2 de los documentos impresos y de la página de error (003, R-5, R-8).

- `autoescape` y `StrictUndefined`: ningún dato del usuario se interpreta como HTML y una
  variable que falte es un error, no un hueco silencioso.
- Las plantillas viven en `app/resources/pdf/` y las fuentes y el logotipo en `app/resources/`,
  que es la `base_url` del renderizado.
- La hoja `papel.css` solo usa los tokens de `tokens.py`, que se inyectan como variables CSS.
"""

import base64
import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any

import jinja2
from markupsafe import Markup

from app.core.pdf import tokens

_RECURSOS = Path(__file__).resolve().parents[2] / "resources"


def directorio_recursos() -> Path:
    """`app/resources`: `base_url` de WeasyPrint para `fuentes/` y `marca/`.

    Es un directorio real también en la imagen de producción (paquete instalado sin comprimir).
    `app.resources` no tiene `__init__`, así que `importlib.resources` daría una ruta múltiple.
    """
    return _RECURSOS


@lru_cache(maxsize=1)
def entorno() -> jinja2.Environment:
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(directorio_recursos() / "pdf"),
        autoescape=True,
        undefined=jinja2.StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


@lru_cache(maxsize=1)
def papel_css() -> str:
    return (directorio_recursos() / "pdf" / "papel.css").read_text(encoding="utf-8")


def _comun() -> dict[str, Any]:
    return {
        "variables_css": Markup(tokens.css_variables()),  # noqa: S704 — CSS propio, sin datos
        "papel_css": Markup(papel_css()),  # noqa: S704 — fichero del paquete, sin datos
    }


def render_html(nombre: str, contexto: dict[str, Any]) -> str:
    return entorno().get_template(nombre).render({**_comun(), **contexto})


def render_html_desde_texto(fuente: str, contexto: dict[str, Any]) -> str:
    """Para los tests: una plantilla en texto que extiende `base.html`."""
    return entorno().from_string(fuente).render({**_comun(), **contexto})


# ------------------------------------------------------------------- página de error

_ESTILO_ERROR = """
body { margin: 0; background: var(--paper); color: var(--paper-ink);
  font-family: Manrope, sans-serif; }
main { max-width: 36rem; margin: 4rem auto; padding: 0 1.5rem;
  border-top: 1px solid var(--paper-rule); }
h1 { font-family: 'Bodoni Moda', serif; font-weight: 400; font-size: 2rem; margin: 2rem 0 1rem; }
p { line-height: 1.6; }
a { color: var(--paper-accent); }
"""


@lru_cache(maxsize=1)
def estilo_error() -> str:
    """Contenido exacto del `<style>` de `error.html`: variables de papel + reglas propias."""
    return tokens.css_variables() + _ESTILO_ERROR


@lru_cache(maxsize=1)
def hash_estilo_error() -> str:
    """`'sha256-…'` del `<style>` de la página de error, para su CSP (research R-8)."""
    resumen = hashlib.sha256(estilo_error().encode("utf-8")).digest()
    return f"'sha256-{base64.b64encode(resumen).decode('ascii')}'"


def render_error(*, titulo: str, mensaje: str, enlace: str, texto_enlace: str) -> str:
    return (
        entorno()
        .get_template("error.html")
        .render(
            estilo=Markup(estilo_error()),  # noqa: S704 — CSS propio, sin datos
            titulo=titulo,
            mensaje=mensaje,
            enlace=enlace,
            texto_enlace=texto_enlace,
        )
    )

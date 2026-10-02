"""Tokens «Paper» definidos una sola vez y sincronizados con docs/DESIGN.md (003, FR-030, R-5)."""

import re
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from app.core.pdf import tokens

DESIGN = Path(__file__).resolve().parents[3] / "docs" / "DESIGN.md"


def _frontmatter() -> dict[str, Any]:
    texto = DESIGN.read_text(encoding="utf-8")
    datos: dict[str, Any] = yaml.safe_load(texto.split("---")[1])
    return datos


def test_colores_de_papel_iguales_que_design() -> None:
    colores = {k: v for k, v in _frontmatter()["colors"].items() if k.startswith("paper")}

    assert colores == tokens.COLORES


def test_tipografia_de_impresion_igual_que_design() -> None:
    tipografia = {k: v for k, v in _frontmatter()["typography"].items() if k.startswith("print-")}

    assert tipografia == {nombre: estilo.como_design() for nombre, estilo in tokens.TIPOS.items()}


def test_espaciado_de_impresion_igual_que_design() -> None:
    espaciado = {k: v for k, v in _frontmatter()["spacing"].items() if k.startswith("print-")}

    assert espaciado == tokens.ESPACIADO


def test_variables_css_cubren_todos_los_tokens() -> None:
    css = tokens.css_variables()

    for nombre in tokens.COLORES:
        assert f"--{nombre}:" in css
    for nombre in tokens.TIPOS:
        assert f"--{nombre}-size:" in css
    for nombre in [*tokens.ESPACIADO, *tokens.DIMENSIONES]:
        assert f"--{nombre}:" in css


def _declaraciones(css: str) -> list[str]:
    sin_comentarios = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    return [d.strip() for d in re.split(r"[;{}]", sin_comentarios) if ":" in d]


def test_papel_css_no_contiene_literales() -> None:
    """Como `check:tokens` en la web: colores y tamaños solo desde `var(--…)`."""
    css = (resources.files("app.resources") / "pdf" / "papel.css").read_text("utf-8")
    # Colores y tamaños tipográficos (pt) solo desde tokens; las medidas de maquetación en mm o %
    # son de cada documento (contracts/documentos-pdf.md).
    prohibidos = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(|\b\d+(\.\d+)?pt\b")
    # Excepción: el filete de 1 px (0.75pt, «hairline» de DESIGN.md).
    permitidos = re.compile(r"\b0\.75pt\b")

    for declaracion in _declaraciones(css):
        if declaracion.startswith("@") or declaracion.startswith("unicode-range"):
            continue
        valor = permitidos.sub("", declaracion.split(":", 1)[1])
        assert not prohibidos.search(valor), f"Literal fuera de los tokens: {declaracion!r}"

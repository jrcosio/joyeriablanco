"""Tokens «Paper» de los documentos impresos: fuente única en el backend (003, R-5, FR-030).

Son los del frontmatter de `docs/DESIGN.md` 1.2 (grupos `paper*`, `print-*`, `print-margin` y
`print-gutter`). `tests/unit/test_tokens_papel.py` comprueba que coinciden con el documento. La
hoja `papel.css` los consume como propiedades personalizadas generadas por `css_variables()`.
"""

from dataclasses import dataclass
from typing import Final

COLORES: Final[dict[str, str]] = {
    "paper": "#ffffff",
    "paper-ink": "#2d3037",
    "paper-ink-muted": "#434750",
    "paper-accent": "#7c580a",
    "paper-rule": "#b48a3c",
    "paper-alert": "#93000a",
    "paper-qr": "#000000",
}


@dataclass(frozen=True, slots=True)
class Tipo:
    familia: str
    tamano: str
    peso: str
    interlineado: str
    espaciado: str | None = None

    def como_design(self) -> dict[str, str]:
        """El estilo con las claves del frontmatter de DESIGN.md."""
        estilo = {
            "fontFamily": self.familia,
            "fontSize": self.tamano,
            "fontWeight": self.peso,
            "lineHeight": self.interlineado,
        }
        if self.espaciado is not None:
            estilo["letterSpacing"] = self.espaciado
        return estilo


TIPOS: Final[dict[str, Tipo]] = {
    "print-title": Tipo("Bodoni Moda", "22pt", "400", "26pt", "-0.01em"),
    "print-total": Tipo("Bodoni Moda", "15pt", "500", "18pt"),
    "print-heading": Tipo("Manrope", "8pt", "700", "11pt", "0.12em"),
    "print-body": Tipo("Manrope", "9pt", "400", "12pt"),
    "print-body-strong": Tipo("Manrope", "9pt", "600", "12pt"),
    "print-label": Tipo("Manrope", "7pt", "600", "9pt", "0.12em"),
    "print-small": Tipo("Manrope", "7.5pt", "400", "10pt"),
    "print-table": Tipo("Manrope", "8.5pt", "400", "11pt"),
}

ESPACIADO: Final[dict[str, str]] = {
    "print-margin": "15mm",
    "print-gutter": "6mm",
}

# Medidas normativas del QR, no de diseño (F-10, art. 21.1; F-12 §3; research R-2): lado de
# 35 mm, en el intervalo de 30 a 40 mm, y margen en blanco recomendado de 6 mm.
DIMENSIONES: Final[dict[str, str]] = {
    "qr-lado": "35mm",
    "qr-margen": "6mm",
}


def css_variables() -> str:
    """Bloque `:root` con todos los tokens como propiedades personalizadas."""
    lineas = [f"  --{nombre}: {valor};" for nombre, valor in COLORES.items()]
    for nombre, tipo in TIPOS.items():
        lineas += [
            f"  --{nombre}-family: '{tipo.familia}';",
            f"  --{nombre}-size: {tipo.tamano};",
            f"  --{nombre}-weight: {tipo.peso};",
            f"  --{nombre}-line: {tipo.interlineado};",
            f"  --{nombre}-tracking: {tipo.espaciado or 'normal'};",
        ]
    lineas += [f"  --{nombre}: {valor};" for nombre, valor in ESPACIADO.items()]
    lineas += [f"  --{nombre}: {valor};" for nombre, valor in DIMENSIONES.items()]
    return ":root {\n" + "\n".join(lineas) + "\n}\n"

"""CLI de operación: `joyeria <comando>` (Typer)."""

import json
from pathlib import Path
from typing import Annotated

import typer

from app.core.config import get_settings

app = typer.Typer(no_args_is_help=True, help="Operación de Joyería Blanco", add_completion=False)


@app.callback()
def main() -> None:
    """Comandos de operación de Joyería Blanco."""


@app.command("exportar-openapi")
def exportar_openapi(
    destino: Annotated[Path | None, typer.Option(help="Fichero de salida")] = None,
) -> None:
    """Escribe el esquema OpenAPI de la API (para generar los tipos de la web)."""
    from app.main import create_app  # importación diferida: no arranca la app al cargar la CLI

    ruta = destino or get_settings().openapi_destino
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps(create_app().openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    typer.echo(f"OpenAPI escrito en {ruta}")

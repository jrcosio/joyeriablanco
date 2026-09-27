"""CLI de operación: `joyeria <comando>` (Typer)."""

import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Annotated

import typer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_engine, get_sessionmaker
from app.core.errors import ProblemaError

app = typer.Typer(no_args_is_help=True, help="Operación de Joyería Blanco", add_completion=False)


@app.callback()
def main() -> None:
    """Comandos de operación de Joyería Blanco."""


def _ejecutar[T](operacion: Callable[[AsyncSession], Awaitable[T]]) -> T:
    """Ejecuta una operación en su propia transacción y traduce los errores de negocio."""

    async def _run() -> T:
        try:
            async with get_sessionmaker()() as session:
                resultado = await operacion(session)
                await session.commit()
                return resultado
        finally:
            await get_engine().dispose()

    try:
        return asyncio.run(_run())
    except ProblemaError as exc:
        mensaje = exc.detalle or exc.titulo
        if exc.errores:
            mensaje += " " + " ".join(f"{e.campo}: {e.mensaje}" for e in exc.errores)
        typer.secho(f"Error: {mensaje}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


def _mostrar_temporal(nombre_usuario: str, temporal: str) -> None:
    typer.echo(f"Usuario: {nombre_usuario}")
    typer.secho(f"Contraseña temporal: {temporal}", bold=True)
    typer.echo(
        "Se muestra UNA sola vez. Entrégala en persona; caduca en "
        f"{get_settings().contrasena_temporal_horas} h y habrá que cambiarla en el primer acceso."
    )


@app.command("crear-admin")
def crear_admin(
    usuario: Annotated[str, typer.Option(help="Nombre de usuario (minúsculas, sin espacios)")],
    nombre: Annotated[str, typer.Option(help="Nombre visible")],
) -> None:
    """Crea un administrador con contraseña temporal (FR-018)."""
    from app.services.usuarios import create_first_admin

    creado, temporal = _ejecutar(
        lambda db: create_first_admin(db, nombre_usuario=usuario, nombre=nombre)
    )
    _mostrar_temporal(creado.nombre_usuario, temporal)


@app.command("restablecer-admin")
def restablecer_admin(
    usuario: Annotated[str, typer.Option(help="Nombre de usuario del administrador")],
) -> None:
    """Restablece la contraseña de un administrador como último recurso (FR-018)."""
    from app.services.usuarios import reset_admin_from_console

    temporal = _ejecutar(lambda db: reset_admin_from_console(db, nombre_usuario=usuario))
    _mostrar_temporal(usuario, temporal)


@app.command("purgar-sesiones")
def purgar_sesiones() -> None:
    """Borra las sesiones caducadas o revocadas hace más de 30 días (FR-054)."""
    from app.services.auth import purge_sessions

    borradas = _ejecutar(purge_sessions)
    typer.echo(f"Sesiones purgadas: {borradas}")


@app.command("exportar-openapi")
def exportar_openapi(
    destino: Annotated[Path | None, typer.Option(help="Fichero de salida")] = None,
) -> None:
    """Escribe el esquema OpenAPI de la API (para generar los tipos de la web)."""
    from app.main import create_app

    ruta = destino or get_settings().openapi_destino
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps(create_app().openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    typer.echo(f"OpenAPI escrito en {ruta}")

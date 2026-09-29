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


@app.command("cargar-datos-ejemplo")
def cargar_datos_ejemplo(
    clientes: Annotated[int, typer.Option(min=1, help="Número de clientes ficticios")] = 40,
    facturas: Annotated[
        int, typer.Option(min=0, help="Número de facturas emitidas de los últimos 6 meses")
    ] = 50,
    borradores: Annotated[int, typer.Option(min=0, help="Número de borradores de factura")] = 5,
    contrasena_demo: Annotated[
        str | None,
        typer.Option(help="Contraseña conocida para los usuarios de ejemplo (solo desarrollo/E2E)"),
    ] = None,
) -> None:
    """Carga usuarios, clientes y facturas ficticios. Se niega en producción (FR-045)."""
    from app.services import datos_ejemplo

    resumen = _ejecutar(
        lambda db: datos_ejemplo.cargar(
            db,
            clientes=clientes,
            facturas=facturas,
            borradores=borradores,
            contrasena_demo=contrasena_demo,
        )
    )
    if resumen.ya_cargados:
        typer.echo("Los datos de ejemplo ya estaban cargados: no se ha hecho nada.")
        return
    typer.echo(f"Clientes de ejemplo creados: {resumen.clientes_creados}")
    typer.echo(f"Facturas de ejemplo emitidas: {resumen.facturas_emitidas}")
    typer.echo(f"Borradores de ejemplo: {resumen.borradores_creados}")
    for nombre_usuario, temporal in resumen.contrasenas_temporales.items():
        _mostrar_temporal(nombre_usuario, temporal)


@app.command("reiniciar-bd-e2e")
def reiniciar_bd_e2e() -> None:
    """Reconstruye el esquema de la BD de E2E (downgrade + upgrade). Solo con ENTORNO=e2e."""
    from alembic import command
    from alembic.config import Config

    from app.core.config import Entorno

    if get_settings().entorno is not Entorno.E2E:
        typer.secho("Error: solo se permite con ENTORNO=e2e.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.attributes["configurar_logging"] = False
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    typer.echo("Base de datos de E2E reconstruida.")


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

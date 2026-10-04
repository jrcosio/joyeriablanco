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
    presupuestos: Annotated[
        int, typer.Option(min=0, help="Número de presupuestos emitidos, en todos los estados")
    ] = 30,
    contrasena_demo: Annotated[
        str | None,
        typer.Option(help="Contraseña conocida para los usuarios de ejemplo (solo desarrollo/E2E)"),
    ] = None,
) -> None:
    """Carga usuarios, clientes, facturas y presupuestos ficticios. Se niega en producción."""
    from app.services import datos_ejemplo

    resumen = _ejecutar(
        lambda db: datos_ejemplo.cargar(
            db,
            clientes=clientes,
            facturas=facturas,
            borradores=borradores,
            presupuestos=presupuestos,
            contrasena_demo=contrasena_demo,
        )
    )
    if resumen.ya_cargados:
        typer.echo("Los datos de ejemplo ya estaban cargados: no se ha hecho nada.")
        return
    typer.echo(f"Clientes de ejemplo creados: {resumen.clientes_creados}")
    typer.echo(f"Facturas de ejemplo emitidas: {resumen.facturas_emitidas}")
    typer.echo(f"Correcciones de ejemplo: {resumen.correcciones}")
    typer.echo(f"Borradores de ejemplo: {resumen.borradores_creados}")
    typer.echo(f"Presupuestos de ejemplo emitidos: {resumen.presupuestos}")
    typer.echo(f"Borradores de presupuesto de ejemplo: {resumen.borradores_presupuesto}")
    for nombre_usuario, temporal in resumen.contrasenas_temporales.items():
        _mostrar_temporal(nombre_usuario, temporal)


@app.command("verificar-cadena")
def verificar_cadena(
    desde: Annotated[
        int | None, typer.Option(min=1, help="Primera secuencia de facturación a comprobar")
    ] = None,
    hasta: Annotated[
        int | None, typer.Option(min=1, help="Última secuencia de facturación a comprobar")
    ] = None,
) -> None:
    """Comprueba la integridad de los registros de facturación y de evento (004, FR-017, FR-021).

    Código 0 si todo es íntegro, 1 si hay anomalías y 2 si sus eventos no se han podido firmar.
    """
    from app.domain.eventos import TEXTO_ANOMALIA
    from app.services import integridad

    if desde is not None and hasta is not None and desde > hasta:
        typer.secho("Error: --desde no puede ser mayor que --hasta.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)
    resultado = _ejecutar(lambda db: integridad.verify_chain(db, desde=desde, hasta=hasta))
    if (primera := resultado.primera) is None:
        typer.echo(
            f"Cadena íntegra ({resultado.registros} registros de facturación y "
            f"{resultado.eventos} de evento)."
        )
    else:
        cadena = "facturación" if primera.cadena == "facturacion" else "evento"
        factura = f" ({primera.num_serie})" if primera.num_serie else ""
        typer.secho(
            f"Anomalía {primera.tipo.value} ({TEXTO_ANOMALIA[primera.tipo.value]}) en el registro "
            f"de {cadena} nº {primera.secuencia}{factura}: {primera.descripcion}. "
            f"Anomalías en total: {len(resultado.anomalias)}.",
            fg=typer.colors.RED,
            err=True,
        )
    if resultado.eventos_pendientes:
        typer.secho(
            "Sin certificado de firma utilizable: los eventos de esta comprobación quedan "
            "pendientes.",
            fg=typer.colors.YELLOW,
            err=True,
        )
        raise typer.Exit(code=2)
    if not resultado.integra:
        raise typer.Exit(code=1)


@app.command("exportar-registros")
def exportar_registros(
    tipo: Annotated[str, typer.Option(help="facturacion o eventos")],
    desde: Annotated[str, typer.Option(help="Primer día, AAAA-MM-DD (hora de Madrid)")],
    hasta: Annotated[str, typer.Option(help="Último día, AAAA-MM-DD (hora de Madrid)")],
    destino: Annotated[Path, typer.Option(help="Fichero ZIP que se crea")],
) -> None:
    """Exporta los registros de un periodo, tal como se firmaron (004, FR-022 a FR-026).

    Código 0 si exporta, 1 si el periodo no tiene registros, 2 si las fechas no son válidas y 3
    si no hay certificado para firmar el evento de la exportación.
    """
    import shutil
    from datetime import date

    from app.core.errors import SinRegistros
    from app.services import certificado, exportacion
    from app.services.certificado import TEXTO_MOTIVO

    inicio: date | None
    fin: date | None
    try:
        inicio, fin = date.fromisoformat(desde), date.fromisoformat(hasta)
    except ValueError:
        inicio = fin = None
    if tipo not in ("facturacion", "eventos") or inicio is None or fin is None or inicio > fin:
        typer.secho(
            "Error: --tipo es facturacion o eventos, y --desde y --hasta son fechas AAAA-MM-DD "
            "con «desde» no posterior a «hasta».",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=2)
    if (motivo := certificado.estado().motivo) is not None:
        typer.secho(
            "Error: el evento de la exportación se firma y el certificado de firma no es "
            f"utilizable ({TEXTO_MOTIVO[motivo]}).",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=3)

    async def _exportar(db: AsyncSession) -> exportacion.Exportacion | None:
        try:
            return await exportacion.export_records(
                db,
                tipo="facturacion" if tipo == "facturacion" else "eventos",
                desde=inicio,
                hasta=fin,
            )
        except SinRegistros:
            return None

    resultado = _ejecutar(_exportar)
    if resultado is None:
        typer.secho("No hay registros en ese periodo.", fg=typer.colors.YELLOW, err=True)
        raise typer.Exit(code=1)
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(resultado.ruta, destino)
    typer.echo(f"Exportado {destino}: {resultado.registros} registros, SHA-256 {resultado.sha256}")


@app.command("generar-certificado-pruebas")
def generar_certificado_pruebas(
    destino: Annotated[Path, typer.Option(help="Fichero PKCS#12 (.p12) que se crea")],
    contrasena: Annotated[str, typer.Option(help="Contraseña del PKCS#12")],
    dias: Annotated[int, typer.Option(min=1, max=3650, help="Días de validez")] = 365,
) -> None:
    """Crea un certificado de firma de PRUEBAS para desarrollo y E2E (004, R-6). Se niega en
    producción, donde además no sería utilizable."""
    from app.services.certificado import generar_pkcs12

    if get_settings().es_produccion:
        typer.secho(
            "Error: en producción se instala el certificado real de la empresa.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(generar_pkcs12(contrasena, nif=_nif_emisor(), dias=dias))
    typer.echo(f"Certificado de pruebas creado en {destino} ({dias} días). No vale en producción.")


def _nif_emisor() -> str:
    """El NIF del emisor configurado o, si aún no hay BD o emisor, uno ficticio de pruebas."""
    from app.repositories import configuracion_facturacion

    async def _leer(db: AsyncSession) -> str | None:
        return (await configuracion_facturacion.get(db)).emisor_nif

    try:
        nif = _ejecutar(_leer)
    except Exception:  # la BD de E2E todavía no existe cuando se genera el certificado
        nif = None
    return nif or "B12345674"


@app.command("estado-certificado")
def estado_certificado() -> None:
    """Estado del certificado de firma (004, FR-003). Nunca muestra la contraseña.

    Código 0 si es utilizable, 1 si no lo es y 3 si es utilizable pero caduca en 30 días o menos.
    """
    from app.services import certificado
    from app.services.certificado import TEXTO_MOTIVO

    estado = certificado.estado()
    if estado.titular is not None:
        typer.echo(f"Titular: {estado.titular} ({estado.identificacion or 'sin NIF'})")
        typer.echo(f"Emisor: {estado.emisor}")
        desde = estado.valido_desde.date() if estado.valido_desde else "?"
        hasta = estado.valido_hasta.date() if estado.valido_hasta else "?"
        typer.echo(f"Válido del {desde} al {hasta} ({estado.dias_restantes} días restantes)")
    if estado.motivo is not None:
        typer.secho(f"No utilizable: {TEXTO_MOTIVO[estado.motivo]}.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    if estado.caduca_pronto:
        typer.secho("Utilizable, pero caduca pronto.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=3)
    typer.echo("Utilizable.")


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

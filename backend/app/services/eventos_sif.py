"""Registro de eventos del sistema informático (004, research R-7 y R-8; Orden, art. 9).

**Cada evento** (`record_evento`) se genera en una sesión y una transacción **propias**, que se
confirman al terminar: un evento de anomalía o de exportación no se pierde aunque se deshaga la
operación que lo originó. Dentro de esa transacción:

1. Toma el cerrojo de la cadena de eventos («JBEVEN») y obtiene el certificado utilizable. Sin él
   el evento no se puede firmar: se deja un aviso en los logs y no se genera (la alarma de
   certificado ya lo señala; el siguiente resumen cubre el intervalo).
2. Comprueba el último evento, como el 7.i con los registros de facturación (art. 9.3; FR-015).
   Si su huella no cuadra o su hora es posterior a la actual en más de un minuto, genera antes el
   evento 06 de esa anomalía, si no estaba ya registrada.
3. Construye el contenido (F-17), calcula la huella (F-2 §3.c), genera el XML, lo firma, lo
   valida contra `EventosSIF.xsd` y lo inserta. El trigger `validar_encadenamiento_eventos` vuelve
   a exigir el encadenamiento.

**El obligado** (`ObligadoEmision`) es el emisor de la configuración. Hasta que se configura, el
productor, que en este sistema de uso propio es la misma Joyería Blanco.

**El líder** (`Lider`) genera los eventos del servicio (R-8): el 01 al arrancar, el 10 cada 6 horas
operativo (art. 9.2), y el 10 y el 02 al pararse. Con varios procesos (`uvicorn --workers 2`), solo
lo es el que consigue el cerrojo consultivo de sesión «JBSIFL»; los demás lo reintentan cada minuto.
"""

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession

from app.core.config import get_settings
from app.core.db import get_sessionmaker
from app.core.tiempo import ahora
from app.domain import eventos
from app.domain.huella import CamposHuellaEvento, compute_huella, format_timestamp
from app.domain.registro import Contenido
from app.domain.tipos import TipoAnomalia, TipoEventoSif, TipoRegistro
from app.domain.xml_registro import build_registro_evento
from app.models.registro_evento import RegistroEvento
from app.models.registro_facturacion import RegistroFacturacion
from app.repositories import configuracion_facturacion, registros
from app.repositories import eventos as repo
from app.services import cadena, certificado, firma
from app.services.certificado import CertificadoFirma, CertificadoNoUtilizable

logger = logging.getLogger(__name__)

PERIODO_RESUMEN: Final = timedelta(hours=6)  # Orden, art. 9.2
CLAVE_CERROJO_LIDER: Final = 0x4A42_5349_464C  # «JBSIFL»
TEXTO_PARADA: Final = "Parada ordenada del servicio"

type AbrirSesion = Callable[[AsyncSession | None], AsyncSession]
type CalcularDatos = Callable[[AsyncSession], Awaitable[Contenido]]


def _sesion_propia(origen: AsyncSession | None) -> AsyncSession:
    """Una sesión con su propia conexión y transacción (R-7). `origen` es la sesión de quien pide
    el evento: aquí no se usa, pero los tests la sustituyen por una sobre su misma conexión."""
    return get_sessionmaker()()


abrir_sesion: AbrirSesion = _sesion_propia


@dataclass(frozen=True, slots=True)
class NuevoEvento:
    tipo: TipoEventoSif
    datos_propios: Contenido | None = None
    otros_datos: str | None = None
    tipo_anomalia: TipoAnomalia | None = None
    secuencia_afectada: int | None = None
    # Para los datos que dependen de la cadena (el resumen): se calculan ya con el cerrojo.
    calcular_datos: CalcularDatos | None = None


# ------------------------------------------------------------------------ huella y comprobación


def recompute_huella(evento: RegistroEvento) -> str:
    """Huella a partir del contenido y las columnas del evento (F-2 §3.c)."""
    datos: dict[str, Any] = evento.contenido["Evento"]
    sistema: dict[str, Any] = datos["SistemaInformatico"]
    return compute_huella(
        CamposHuellaEvento(
            nif_sistema=str(sistema.get("NIF", "")),
            id_otro_sistema=str(sistema.get("IDOtro", {}).get("ID", "")),
            id_sistema=str(sistema["IdSistemaInformatico"]),
            version=str(sistema["Version"]),
            numero_instalacion=str(sistema["NumeroInstalacion"]),
            nif_obligado=str(datos["ObligadoEmision"]["NIF"]),
            tipo_evento=evento.tipo_evento,
            huella_anterior=evento.huella_anterior or "",
            fecha_hora_huso_gen=evento.fecha_hora_huso_gen,
        ).cadena()
    )


def tail_problem(ultimo: RegistroEvento, momento: datetime) -> tuple[TipoAnomalia, str] | None:
    """Por qué el último evento no permite seguir la cadena (por analogía con el 7.i), o `None`."""
    try:
        correcta = recompute_huella(ultimo) == ultimo.huella
    except (KeyError, TypeError, AttributeError):
        correcta = False
    if not correcta:
        return TipoAnomalia.HUELLA, "La huella del último evento no coincide con sus datos"
    if datetime.fromisoformat(ultimo.fecha_hora_huso_gen) > momento + cadena.MARGEN_HORA:
        return TipoAnomalia.FECHA_FUTURA, "El último evento tiene una hora posterior a la actual"
    return None


def referido(evento: RegistroEvento) -> eventos.EventoReferido:
    return eventos.EventoReferido(evento.tipo_evento, evento.fecha_hora_huso_gen, evento.huella)


def con_huella(registro: RegistroFacturacion) -> eventos.RegistroConHuella:
    factura = eventos.IdFactura(registro.id_emisor, registro.num_serie, registro.fecha_expedicion)
    return eventos.RegistroConHuella(factura, registro.huella)


# ------------------------------------------------------------------------------- generación


async def _obligado(session: AsyncSession) -> eventos.Obligado:
    config = await configuracion_facturacion.get(session)
    if config.emisor_nombre and config.emisor_nif:
        return eventos.Obligado(nombre=config.emisor_nombre, nif=config.emisor_nif)
    ajustes = get_settings()
    return eventos.Obligado(nombre=ajustes.sif_productor_nombre, nif=ajustes.sif_productor_nif)


async def _insertar(
    session: AsyncSession,
    nuevo: NuevoEvento,
    ultimo: RegistroEvento | None,
    firmante: CertificadoFirma,
    momento: datetime,
) -> RegistroEvento:
    sistema = cadena.sistema_informatico()
    obligado = await _obligado(session)
    fecha = format_timestamp(momento)
    anterior = (
        eventos.EventoAnterior(ultimo.tipo_evento, ultimo.fecha_hora_huso_gen, ultimo.huella)
        if ultimo
        else None
    )
    huella = compute_huella(
        eventos.campos_huella(
            sistema=sistema,
            obligado=obligado,
            tipo=nuevo.tipo,
            anterior=anterior,
            fecha_hora_huso_gen=fecha,
        ).cadena()
    )
    datos = await nuevo.calcular_datos(session) if nuevo.calcular_datos else nuevo.datos_propios
    contenido = eventos.build_contenido_evento(
        sistema=sistema,
        obligado=obligado,
        tipo=nuevo.tipo,
        fecha_hora_huso_gen=fecha,
        datos_propios=datos,
        otros_datos=nuevo.otros_datos,
        anterior=anterior,
        huella=huella,
    )
    xml = firma.sign_and_validate(
        build_registro_evento(contenido, con_hueco_firma=True),
        firma.Esquema.EVENTOS,
        firmante,
        momento,
    )
    evento = await repo.insert(
        session,
        RegistroEvento(
            secuencia=(ultimo.secuencia + 1) if ultimo else 1,
            tipo_evento=nuevo.tipo.value,
            fecha_hora_huso_gen=fecha,
            primer_evento=anterior is None,
            tipo_evento_anterior=anterior.tipo_evento if anterior else None,
            fecha_hora_huso_gen_anterior=anterior.fecha_hora_huso_gen if anterior else None,
            huella_anterior=anterior.huella if anterior else None,
            tipo_huella="01",
            huella=huella,
            tipo_anomalia=nuevo.tipo_anomalia.value if nuevo.tipo_anomalia else None,
            secuencia_afectada=nuevo.secuencia_afectada,
            contenido=contenido,
            xml_firmado=xml,
            certificado_titular=firmante.titular,
            certificado_huella=firmante.huella,
        ),
    )
    logger.info(
        "Evento del sistema registrado",
        extra={"tipo_evento": nuevo.tipo.value, "secuencia": evento.secuencia},
    )
    return evento


async def _generar(session: AsyncSession, nuevo: NuevoEvento) -> RegistroEvento | None:
    await repo.lock_events(session)
    momento = ahora()
    try:
        firmante = certificado.utilizable(momento)
    except CertificadoNoUtilizable as exc:
        logger.warning(
            "Evento del sistema sin generar: certificado no utilizable",
            extra={"tipo_evento": nuevo.tipo.value, "motivo": exc.motivo.value},
        )
        return None
    ultimo = await repo.get_last(session)
    if ultimo is not None and (problema := tail_problem(ultimo, momento)) is not None:
        tipo_anomalia, descripcion = problema
        logger.error(
            "Cadena de eventos inconsistente",
            extra={"secuencia": ultimo.secuencia, "tipo_anomalia": tipo_anomalia.value},
        )
        if not await repo.exists_anomaly(
            session,
            tipo_evento=TipoEventoSif.ANOMALIA_EVENTOS.value,
            tipo_anomalia=tipo_anomalia.value,
            secuencia_afectada=ultimo.secuencia,
        ):
            anomalia = NuevoEvento(
                TipoEventoSif.ANOMALIA_EVENTOS,
                datos_propios=eventos.anomalia_eventos(
                    tipo_anomalia, descripcion=descripcion, evento=referido(ultimo)
                ),
                tipo_anomalia=tipo_anomalia,
                secuencia_afectada=ultimo.secuencia,
            )
            ultimo = await _insertar(session, anomalia, ultimo, firmante, momento)
    return await _insertar(session, nuevo, ultimo, firmante, momento)


async def record_evento(origen: AsyncSession | None, nuevo: NuevoEvento) -> RegistroEvento | None:
    """Genera un evento en su propia transacción (R-7). `None` si no hay certificado utilizable."""
    session = abrir_sesion(origen)
    try:
        evento = await _generar(session, nuevo)
        await session.commit()
        return evento
    except BaseException:
        await session.rollback()
        raise
    finally:
        await session.close()


# --------------------------------------------------------------------------- resumen (9.2)


async def _ultimo_registro_resumido(session: AsyncSession) -> int:
    """La secuencia del último registro de facturación que cubrió un resumen anterior."""
    for resumen in await repo.list_of_type_desc(session, TipoEventoSif.RESUMEN.value):
        propios: dict[str, Any] = resumen.contenido["Evento"].get("DatosPropiosEvento", {})
        final = propios.get("ResumenEventos", {}).get("RegistroFacturacionFinalPeriodo")
        if final and (registro := await registros.get_by_huella(session, str(final["Huella"]))):
            return registro.secuencia
    return 0


async def summary_data(session: AsyncSession) -> Contenido:
    """`ResumenEventos` desde el resumen anterior: eventos por tipo, y altas y anulaciones con su
    primer y su último registro y las sumas de las altas (art. 9.2; data-model)."""
    anterior = await repo.last_of_types(session, [TipoEventoSif.RESUMEN.value])
    por_tipo = await repo.count_by_type_after(session, anterior.secuencia if anterior else 0)
    nuevos = await registros.list_after(session, await _ultimo_registro_resumido(session))
    altas = [r for r in nuevos if r.tipo == TipoRegistro.ALTA]
    return eventos.resumen(
        eventos_por_tipo=por_tipo,
        inicial=con_huella(nuevos[0]) if nuevos else None,
        final=con_huella(nuevos[-1]) if nuevos else None,
        altas=len(altas),
        suma_cuota=sum((r.cuota_total or Decimal(0) for r in altas), Decimal(0)),
        suma_importe=sum((r.importe_total or Decimal(0) for r in altas), Decimal(0)),
        anulaciones=len(nuevos) - len(altas),
    )


async def record_resumen(origen: AsyncSession | None) -> RegistroEvento | None:
    return await record_evento(
        origen, NuevoEvento(TipoEventoSif.RESUMEN, calcular_datos=summary_data)
    )


# ------------------------------------------------------------------------------ líder (R-8)


class Lider:
    """Genera el inicio, los resúmenes periódicos y el fin del servicio. Nunca impide arrancar ni
    parar la API: los errores quedan en los logs y se reintenta en la siguiente vuelta."""

    def __init__(
        self,
        engine: AsyncEngine,
        *,
        vuelta: timedelta = timedelta(minutes=1),
        periodo: timedelta = PERIODO_RESUMEN,
        reloj: Callable[[], datetime] = ahora,
    ) -> None:
        self._engine = engine
        self._vuelta = vuelta
        self._periodo = periodo
        self._reloj = reloj
        self._conexion: AsyncConnection | None = None
        self._tarea: asyncio.Task[None] | None = None

    @property
    def es_lider(self) -> bool:
        return self._conexion is not None

    async def _ser_lider(self) -> bool:
        if self._conexion is not None:
            return True
        conexion = await self._engine.connect()
        try:
            conseguido = bool(
                await conexion.scalar(select(func.pg_try_advisory_lock(CLAVE_CERROJO_LIDER)))
            )
            await conexion.commit()  # el cerrojo es de sesión: sigue mientras viva la conexión
        except BaseException:
            await conexion.close()
            raise
        if not conseguido:
            await conexion.close()
            return False
        self._conexion = conexion
        logger.info("Este proceso genera los eventos del servicio")
        await record_evento(None, NuevoEvento(TipoEventoSif.INICIO))
        return True

    async def _resumen_si_toca(self) -> None:
        session = abrir_sesion(None)
        try:
            ultimo = await repo.last_of_types(
                session, [TipoEventoSif.INICIO.value, TipoEventoSif.RESUMEN.value]
            )
        finally:
            await session.close()
        if ultimo is None or (
            self._reloj() - datetime.fromisoformat(ultimo.fecha_hora_huso_gen) >= self._periodo
        ):
            await record_resumen(None)

    async def tick(self) -> None:
        """Una vuelta: intentar ser el líder y, si lo es, el resumen si han pasado 6 horas."""
        if await self._ser_lider():
            await self._resumen_si_toca()

    async def _seguro(self, accion: Callable[[], Awaitable[object]]) -> None:
        try:
            await accion()
        except Exception:
            logger.exception("No se han podido generar los eventos del servicio")

    async def _bucle(self) -> None:
        while True:
            await asyncio.sleep(self._vuelta.total_seconds())
            await self._seguro(self.tick)

    async def iniciar(self) -> None:
        await self._seguro(self.tick)
        self._tarea = asyncio.create_task(self._bucle())

    async def detener(self) -> None:
        """Antes de parar: el resumen y el fin (art. 9.2 y 9.1.b), y suelta el cerrojo."""
        if self._tarea is not None:
            self._tarea.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._tarea
            self._tarea = None
        if self._conexion is None:
            return
        await self._seguro(lambda: record_resumen(None))
        await self._seguro(
            lambda: record_evento(None, NuevoEvento(TipoEventoSif.FIN, otros_datos=TEXTO_PARADA))
        )
        try:
            await self._conexion.execute(select(func.pg_advisory_unlock(CLAVE_CERROJO_LIDER)))
        finally:
            await self._conexion.close()
            self._conexion = None

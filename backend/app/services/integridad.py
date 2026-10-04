"""Comprobación de integridad de los registros de facturación y de evento (002 US6; 004 US3).

Orden HAC/1177/2024, arts. 6.b a 6.f y 7.h (y 9.3 para los eventos), research R-9 y R-10 de 004.
Bajo demanda (F-4, p. 30), desde la web o la consola, sobre toda la cadena de facturación o un
rango de secuencias, y siempre sobre toda la cadena de eventos. Cuatro comprobaciones:

1. **Huellas** (01): la huella recalculada (F-2) es la guardada.
2. **Firmas** (02): la firma XAdES se verifica en la fecha de generación y es del certificado
   guardado. En No VERI*FACTU, un registro sin firma también es la anomalía 02.
3. **Cadena**: secuencias consecutivas (04 y 05) y huella del anterior (08, o 07 si lo alterado es
   la huella del propio anterior).
4. **Fechas**: no anteriores a las del anterior (11) ni posteriores a la hora actual en más de un
   minuto (13).

Además, «Integridad - Otros» (03): el XML firmado coincide con el contenido guardado, y el
contenido, las columnas y los totales coinciden con la factura (la comprobación de 002).

Genera el 03 y el 05 con los recuentos, y un 04 o un 06 por cada anomalía que no estuviera ya
registrada. Guarda la comprobación (alcance y resultado), que apaga la alarma (R-11), y la
auditoría `INTEGRIDAD_COMPROBADA` con quién la lanzó (FR-033). Sin certificado (solo desde la
consola) comprueba igual, pero sus eventos quedan pendientes.
"""

import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.http import Origen
from app.core.tiempo import ahora
from app.domain import eventos as eventos_dominio
from app.domain.exenciones import is_oro_inversion
from app.domain.huella import format_date
from app.domain.importes import LineaCalculo, compute_totals, line_amount
from app.domain.registro import (
    SistemaInformatico,
    build_contenido_alta,
    build_contenido_anulacion,
)
from app.domain.tipos import Modalidad, TipoAnomalia, TipoEvento, TipoEventoSif, TipoRegistro
from app.domain.xml_registro import (
    build_registro_alta,
    build_registro_anulacion,
    build_registro_evento,
    canonical,
    without_signature,
)
from app.models.comprobacion_integridad import ComprobacionIntegridad
from app.models.factura import Factura
from app.models.registro_evento import RegistroEvento
from app.models.registro_facturacion import RegistroFacturacion
from app.models.usuario import Usuario
from app.repositories import comprobaciones, facturas
from app.repositories import eventos as eventos_repo
from app.repositories import registros as registros_repo
from app.services import cadena, certificado, eventos_sif, firma
from app.services.auditoria import ACTOR_CONSOLA, record_event
from app.services.eventos_sif import NuevoEvento

logger = logging.getLogger(__name__)

type Cadena = Literal["facturacion", "eventos"]


@dataclass(frozen=True, slots=True)
class Anomalia:
    cadena: Cadena
    tipo: TipoAnomalia
    descripcion: str
    secuencia: int | None
    num_serie: str | None = None  # la factura del registro, para mostrarla


@dataclass(frozen=True, slots=True)
class ResultadoIntegridad:
    registros: int
    eventos: int
    anomalias: tuple[Anomalia, ...]
    eventos_pendientes: bool = False  # sin certificado: los eventos no se han podido firmar

    @property
    def integra(self) -> bool:
        return not self.anomalias

    @property
    def primera(self) -> Anomalia | None:
        return self.anomalias[0] if self.anomalias else None


@dataclass(frozen=True, slots=True)
class ComprobacionRegistro:
    """Comprobación inmediata de un registro (004, FR-011; Orden, arts. 6.b y 6.d)."""

    huella_correcta: bool
    firma_correcta: bool | None  # None: el registro no lleva firma (VERI*FACTU)


def check_signature(
    xml: bytes | None, certificado_huella: str | None, fecha_hora_huso_gen: str
) -> bool | None:
    """La firma verifica en la fecha de generación y es del certificado guardado (R-9)."""
    if xml is None:
        return None
    try:
        verificada = firma.verificar(xml, en=datetime.fromisoformat(fecha_hora_huso_gen))
    except firma.FirmaNoValida:
        return False
    return verificada.huella == certificado_huella


def check_registro(registro: RegistroFacturacion) -> ComprobacionRegistro:
    try:
        huella_correcta = cadena.recompute_huella(registro) == registro.huella
    except ValueError:
        huella_correcta = False
    return ComprobacionRegistro(
        huella_correcta=huella_correcta,
        firma_correcta=check_signature(
            registro.xml_firmado, registro.certificado_huella, registro.fecha_hora_huso_gen
        ),
    )


# ------------------------------------------------------------------ datos de la factura (002)


def _problema_de_totales(factura: Factura) -> str | None:
    """Totales y desglose de la factura frente a los que resultan de sus líneas (FR-015)."""
    for linea in factura.lineas:
        if linea.importe != line_amount(linea.unidades, linea.precio_unitario):
            return f"el importe de la línea {linea.orden} no resulta de sus unidades y su precio"
    if not factura.desgloses:
        return "la factura no tiene desglose"
    # Oro de inversión (R-21): todas las líneas sin tipo si y solo si la factura lleva la clave 04.
    exenta = is_oro_inversion(factura.clave_regimen)
    if any((linea.tipo_iva is None) != exenta for linea in factura.lineas):
        return "el tipo de IVA de las líneas no corresponde al de la factura"
    totales = compute_totals(
        [LineaCalculo(li.unidades, li.precio_unitario, li.tipo_iva) for li in factura.lineas],
        tipo_iva_por_defecto=factura.desgloses[0].tipo_iva,
    )
    esperado = [(d.tipo_iva, d.base, d.cuota) for d in totales.desglose]
    guardado = [(d.tipo_iva, d.base, d.cuota) for d in factura.desgloses]
    if guardado != esperado:
        return "el desglose no resulta de las líneas"
    if (factura.base_total, factura.cuota_total, factura.importe_total) != (
        totales.base_total,
        totales.cuota_total,
        totales.importe_total,
    ):
        return "los totales no resultan de las líneas"
    return None


def _problema_de_columnas(registro: RegistroFacturacion, factura: Factura) -> str | None:
    """Las columnas de la huella deben ser las de la factura (F-2)."""
    esperadas: dict[str, object] = {
        "id_emisor": factura.emisor_nif,
        "num_serie": factura.num_serie,
        "fecha_expedicion": format_date(factura.fecha_expedicion),
    }
    if registro.tipo == TipoRegistro.ALTA:
        esperadas |= {
            "tipo_factura": factura.tipo_factura,
            "cuota_total": factura.cuota_total,
            "importe_total": factura.importe_total,
        }
    for campo, valor in esperadas.items():
        if getattr(registro, campo) != valor:
            return f"el campo {campo} del registro no coincide con la factura"
    return None


async def _contenido_esperado(
    db: AsyncSession,
    registro: RegistroFacturacion,
    factura: Factura,
    anterior: RegistroFacturacion | None,
) -> dict[str, object]:
    sistema = SistemaInformatico.from_bloque(registro.contenido["SistemaInformatico"])
    enlace = cadena.registro_anterior(anterior)
    if registro.tipo == TipoRegistro.ANULACION:
        return build_contenido_anulacion(
            emisor_nif=factura.emisor_nif,
            num_serie=factura.num_serie,
            fecha_expedicion=factura.fecha_expedicion,
            anterior=enlace,
            sistema=sistema,
            fecha_hora_huso_gen=registro.fecha_hora_huso_gen,
            huella=registro.huella,
        )
    rectificada = (
        await facturas.get(db, factura.factura_rectificada_id)
        if factura.factura_rectificada_id
        else None
    )
    return build_contenido_alta(
        cadena.datos_alta(factura, rectificada),
        anterior=enlace,
        sistema=sistema,
        fecha_hora_huso_gen=registro.fecha_hora_huso_gen,
        huella=registro.huella,
    )


async def _problema_de_documento(
    db: AsyncSession,
    registro: RegistroFacturacion,
    anterior: RegistroFacturacion | None,
    revisadas: set[uuid.UUID],
) -> str | None:
    """Columnas, contenido y totales frente a la factura (la comprobación de 002, FR-031)."""
    factura = await facturas.get(db, registro.factura_id)
    if factura is None:  # pragma: no cover — FK
        return "no existe su factura"
    if problema := _problema_de_columnas(registro, factura):
        return problema
    try:
        esperado = await _contenido_esperado(db, registro, factura, anterior)
    except (KeyError, ValueError) as exc:
        return f"el contenido guardado no se puede reconstruir ({exc})"
    if esperado != registro.contenido:
        return "el contenido guardado no coincide con el de su factura"
    if registro.tipo == TipoRegistro.ALTA and factura.id not in revisadas:
        revisadas.add(factura.id)
        if problema := _problema_de_totales(factura):
            return f"factura {factura.num_serie}: {problema}"
    return None


def _xml_no_coincide(xml: bytes, esperado: bytes) -> bool:
    try:
        return canonical(without_signature(xml)) != esperado
    except ValueError:
        return True


# ------------------------------------------------------------------------- facturación


def _fuera_de_hora(fecha: str, limite: datetime) -> bool:
    return datetime.fromisoformat(fecha) > limite


async def _anomalias_registro(
    db: AsyncSession,
    registro: RegistroFacturacion,
    anterior: RegistroFacturacion | None,
    revisadas: set[uuid.UUID],
    limite: datetime,
) -> list[Anomalia]:
    def anomalia(tipo: TipoAnomalia, descripcion: str) -> Anomalia:
        return Anomalia("facturacion", tipo, descripcion, registro.secuencia, registro.num_serie)

    halladas: list[Anomalia] = []
    revision = check_registro(registro)
    if not revision.huella_correcta:
        halladas.append(anomalia(TipoAnomalia.HUELLA, "La huella no coincide con los datos"))
    if revision.firma_correcta is False or (
        revision.firma_correcta is None and registro.modalidad == Modalidad.NO_VERIFACTU
    ):
        halladas.append(anomalia(TipoAnomalia.FIRMA, "La firma no se verifica"))
    if registro.xml_firmado is not None:
        construir = (
            build_registro_alta if registro.tipo == TipoRegistro.ALTA else build_registro_anulacion
        )
        try:
            esperado = canonical(construir(registro.contenido))
        except (ValueError, TypeError):
            esperado = b""
        if _xml_no_coincide(registro.xml_firmado, esperado):
            halladas.append(
                anomalia(
                    TipoAnomalia.INTEGRIDAD_OTROS, "El XML firmado no coincide con el registro"
                )
            )
    if problema := await _problema_de_documento(db, registro, anterior, revisadas):
        halladas.append(anomalia(TipoAnomalia.INTEGRIDAD_OTROS, _frase(problema)))
    if anterior is None:
        if registro.secuencia != 1 or not registro.primer_registro:
            halladas.append(anomalia(TipoAnomalia.SIN_ANTERIOR, "El registro anterior no existe"))
    elif registro.secuencia != anterior.secuencia + 1:
        halladas.append(anomalia(TipoAnomalia.SIN_ANTERIOR, "El registro anterior no existe"))
    else:
        if registro.huella_anterior != anterior.huella or registro.primer_registro:
            halladas.append(_anomalia_de_enlace(registro, anterior))
        if datetime.fromisoformat(registro.fecha_hora_huso_gen) < datetime.fromisoformat(
            anterior.fecha_hora_huso_gen
        ):
            halladas.append(
                anomalia(
                    TipoAnomalia.FECHA_ANTERIOR_A_LA_PREVIA,
                    "La fecha de generación es anterior a la del registro anterior",
                )
            )
    if _fuera_de_hora(registro.fecha_hora_huso_gen, limite):
        halladas.append(
            anomalia(TipoAnomalia.FECHA_FUTURA, "La fecha de generación es posterior a la actual")
        )
    return halladas


def _anomalia_de_enlace(registro: RegistroFacturacion, anterior: RegistroFacturacion) -> Anomalia:
    """07 si lo alterado es la huella del anterior (el registro apunta a la que debería tener),
    y 08 si lo alterado es la «huella del anterior» de este registro (R-10)."""
    try:
        original = cadena.recompute_huella(anterior)
    except ValueError:
        original = None
    if (
        original is not None
        and original != anterior.huella
        and original == registro.huella_anterior
    ):
        return Anomalia(
            "facturacion",
            TipoAnomalia.HUELLA_NO_ENLAZA_CON_POSTERIOR,
            "La huella no coincide con la «huella del anterior» del registro posterior",
            anterior.secuencia,
            anterior.num_serie,
        )
    return Anomalia(
        "facturacion",
        TipoAnomalia.HUELLA_ANTERIOR_ERRONEA,
        "La huella del anterior no coincide con la del registro anterior",
        registro.secuencia,
        registro.num_serie,
    )


async def _check_facturacion(
    db: AsyncSession, desde: int | None, hasta: int | None, limite: datetime
) -> tuple[list[RegistroFacturacion], list[Anomalia]]:
    cola = await registros_repo.list_in_order(db)
    revisar = [
        r
        for r in cola
        if (desde is None or r.secuencia >= desde) and (hasta is None or r.secuencia <= hasta)
    ]
    anomalias: list[Anomalia] = []
    revisadas: set[uuid.UUID] = set()
    posicion = {r.secuencia: i for i, r in enumerate(cola)}
    for registro in revisar:
        i = posicion[registro.secuencia]
        anterior = cola[i - 1] if i > 0 else None
        anomalias += await _anomalias_registro(db, registro, anterior, revisadas, limite)
        posterior = cola[i + 1] if i + 1 < len(cola) else None
        if posterior is not None and posterior.secuencia != registro.secuencia + 1:
            anomalias.append(
                Anomalia(
                    "facturacion",
                    TipoAnomalia.SIN_POSTERIOR,
                    "El registro posterior no existe",
                    registro.secuencia,
                    registro.num_serie,
                )
            )
    return revisar, _ordenadas(anomalias)


# ---------------------------------------------------------------------------------- eventos


def _anomalias_evento(
    evento: RegistroEvento, anterior: RegistroEvento | None, limite: datetime
) -> list[Anomalia]:
    def anomalia(tipo: TipoAnomalia, descripcion: str) -> Anomalia:
        return Anomalia("eventos", tipo, descripcion, evento.secuencia)

    from app.services.registro_fiscal import event_fingerprint_ok  # evita el ciclo de imports

    halladas: list[Anomalia] = []
    if not event_fingerprint_ok(evento):
        halladas.append(anomalia(TipoAnomalia.HUELLA, "La huella no coincide con los datos"))
    if not check_signature(
        evento.xml_firmado, evento.certificado_huella, evento.fecha_hora_huso_gen
    ):
        halladas.append(anomalia(TipoAnomalia.FIRMA, "La firma no se verifica"))
    try:
        esperado = canonical(build_registro_evento(evento.contenido))
        datos = evento.contenido["Evento"]
        columnas = (
            datos["TipoEvento"] == evento.tipo_evento
            and datos["FechaHoraHusoGenEvento"] == evento.fecha_hora_huso_gen
        )
    except (KeyError, ValueError, TypeError):
        esperado, columnas = b"", False
    if not columnas or _xml_no_coincide(evento.xml_firmado, esperado):
        halladas.append(
            anomalia(TipoAnomalia.INTEGRIDAD_OTROS, "El XML firmado no coincide con el evento")
        )
    if anterior is None:
        if evento.secuencia != 1 or not evento.primer_evento:
            halladas.append(anomalia(TipoAnomalia.SIN_ANTERIOR, "El evento anterior no existe"))
    elif evento.secuencia != anterior.secuencia + 1:
        halladas.append(anomalia(TipoAnomalia.SIN_ANTERIOR, "El evento anterior no existe"))
    else:
        if (
            evento.huella_anterior != anterior.huella
            or evento.tipo_evento_anterior != anterior.tipo_evento
            or evento.fecha_hora_huso_gen_anterior != anterior.fecha_hora_huso_gen
        ):
            try:
                original: str | None = eventos_sif.recompute_huella(anterior)
            except (KeyError, TypeError, AttributeError):
                original = None
            if (
                original is not None
                and original != anterior.huella
                and original == evento.huella_anterior
            ):
                halladas.append(
                    Anomalia(
                        "eventos",
                        TipoAnomalia.HUELLA_NO_ENLAZA_CON_POSTERIOR,
                        "La huella no coincide con la «huella del anterior» del evento posterior",
                        anterior.secuencia,
                    )
                )
            else:
                halladas.append(
                    anomalia(
                        TipoAnomalia.HUELLA_ANTERIOR_ERRONEA,
                        "El encadenamiento no coincide con el evento anterior",
                    )
                )
        if datetime.fromisoformat(evento.fecha_hora_huso_gen) < datetime.fromisoformat(
            anterior.fecha_hora_huso_gen
        ):
            halladas.append(
                anomalia(
                    TipoAnomalia.FECHA_ANTERIOR_A_LA_PREVIA,
                    "La fecha de generación es anterior a la del evento anterior",
                )
            )
    if _fuera_de_hora(evento.fecha_hora_huso_gen, limite):
        halladas.append(
            anomalia(TipoAnomalia.FECHA_FUTURA, "La fecha de generación es posterior a la actual")
        )
    return halladas


def _check_eventos(cola: Sequence[RegistroEvento], limite: datetime) -> list[Anomalia]:
    anomalias: list[Anomalia] = []
    for i, evento in enumerate(cola):
        anterior = cola[i - 1] if i > 0 else None
        anomalias += _anomalias_evento(evento, anterior, limite)
        posterior = cola[i + 1] if i + 1 < len(cola) else None
        if posterior is not None and posterior.secuencia != evento.secuencia + 1:
            anomalias.append(
                Anomalia(
                    "eventos",
                    TipoAnomalia.SIN_POSTERIOR,
                    "El evento posterior no existe",
                    evento.secuencia,
                )
            )
    return _ordenadas(anomalias)


def _frase(texto: str) -> str:
    return texto[:1].upper() + texto[1:]


def _ordenadas(anomalias: list[Anomalia]) -> list[Anomalia]:
    """Por secuencia y tipo, una por tipo y registro: si hay varias, con sus descripciones."""
    unicas: dict[tuple[int | None, TipoAnomalia], Anomalia] = {}
    for a in anomalias:
        if (previa := unicas.get((a.secuencia, a.tipo))) is not None:
            a = Anomalia(
                a.cadena, a.tipo, f"{previa.descripcion}. {a.descripcion}", a.secuencia, a.num_serie
            )
        unicas[(a.secuencia, a.tipo)] = a
    return sorted(unicas.values(), key=lambda a: (a.secuencia or 0, a.tipo.value))


# ------------------------------------------------------------------------------ comprobación


async def _registrar_eventos(
    db: AsyncSession,
    *,
    revisados: list[RegistroFacturacion],
    eventos: int,
    anomalias: Sequence[Anomalia],
    cola_eventos: Sequence[RegistroEvento],
) -> tuple[RegistroEvento | None, list[Anomalia]]:
    """El 03 y el 05 con los recuentos, y un 04 o un 06 por cada anomalía nueva (FR-018).
    Devuelve el 03 y las anomalías que no estaban ya registradas."""
    n = len(revisados)
    lanzamiento = await eventos_sif.record_evento(
        db,
        NuevoEvento(
            TipoEventoSif.LANZAMIENTO_ANOMALIAS_FACTURACION,
            datos_propios=eventos_dominio.lanzamiento(
                TipoEventoSif.LANZAMIENTO_ANOMALIAS_FACTURACION,
                eventos_dominio.Recuentos(huellas=n, firmas=n, cadena=n, fechas=n),
            ),
        ),
    )
    if lanzamiento is None:
        return None, []
    await eventos_sif.record_evento(
        db,
        NuevoEvento(
            TipoEventoSif.LANZAMIENTO_ANOMALIAS_EVENTOS,
            datos_propios=eventos_dominio.lanzamiento(
                TipoEventoSif.LANZAMIENTO_ANOMALIAS_EVENTOS,
                eventos_dominio.Recuentos(
                    huellas=eventos, firmas=eventos, cadena=eventos, fechas=eventos
                ),
            ),
        ),
    )
    nuevas: list[Anomalia] = []
    por_secuencia = {r.secuencia: r for r in revisados}
    eventos_por_secuencia = {e.secuencia: e for e in cola_eventos}
    for a in anomalias:
        if a.cadena == "facturacion":
            registro = por_secuencia.get(a.secuencia or 0)
            factura = (
                eventos_dominio.IdFactura(
                    registro.id_emisor, registro.num_serie, registro.fecha_expedicion
                )
                if registro
                else None
            )
            nuevo = NuevoEvento(
                TipoEventoSif.ANOMALIA_FACTURACION,
                datos_propios=eventos_dominio.anomalia_facturacion(
                    a.tipo, descripcion=a.descripcion, factura=factura
                ),
                tipo_anomalia=a.tipo,
                secuencia_afectada=a.secuencia,
                solo_si_nueva=True,
            )
        else:
            afectado = eventos_por_secuencia.get(a.secuencia or 0)
            nuevo = NuevoEvento(
                TipoEventoSif.ANOMALIA_EVENTOS,
                datos_propios=eventos_dominio.anomalia_eventos(
                    a.tipo,
                    descripcion=a.descripcion,
                    evento=eventos_sif.referido(afectado) if afectado else None,
                ),
                tipo_anomalia=a.tipo,
                secuencia_afectada=a.secuencia,
                solo_si_nueva=True,
            )
        if await eventos_sif.record_evento(db, nuevo) is not None:
            nuevas.append(a)
    return lanzamiento, nuevas


async def verify_chain(
    db: AsyncSession,
    *,
    desde: int | None = None,
    hasta: int | None = None,
    origen: Origen | None = None,
    actor: Usuario | None = None,
) -> ResultadoIntegridad:
    """Comprueba las dos cadenas (R-9), genera sus eventos y guarda la comprobación."""
    limite = ahora() + cadena.MARGEN_HORA
    cola_eventos = await eventos_repo.list_in_order(db)
    revisados, anomalias_facturacion = await _check_facturacion(db, desde, hasta, limite)
    anomalias_eventos = _check_eventos(cola_eventos, limite)
    anomalias = (*anomalias_facturacion, *anomalias_eventos)

    lanzamiento, nuevas = await _registrar_eventos(
        db,
        revisados=revisados,
        eventos=len(cola_eventos),
        anomalias=anomalias,
        cola_eventos=cola_eventos,
    )
    if lanzamiento is not None:
        ultimo = await registros_repo.get_last(db)
        await comprobaciones.insert(
            db,
            ComprobacionIntegridad(
                origen="consola" if actor is None else "web",
                actor_id=actor.id if actor else None,
                desde_secuencia=revisados[0].secuencia if revisados else None,
                hasta_secuencia=revisados[-1].secuencia if revisados else None,
                llega_al_final=(
                    ultimo is None
                    or (bool(revisados) and revisados[-1].secuencia >= ultimo.secuencia)
                ),
                registros=len(revisados),
                eventos=len(cola_eventos),
                anomalias=len(anomalias),
                # Solo las anomalías nuevas: las ya registradas no impiden apagar la alarma (R-11).
                max_secuencia_anomala=max(
                    (a.secuencia or 0 for a in nuevas if a.cadena == "facturacion"), default=None
                ),
                max_evento_anomalo=max(
                    (a.secuencia or 0 for a in nuevas if a.cadena == "eventos"), default=None
                ),
                evento_lanzamiento_id=lanzamiento.id,
            ),
        )
    resultado = ResultadoIntegridad(
        registros=len(revisados),
        eventos=len(cola_eventos),
        anomalias=anomalias,
        eventos_pendientes=lanzamiento is None,
    )
    primera = resultado.primera
    await record_event(
        db,
        TipoEvento.INTEGRIDAD_COMPROBADA,
        origen=origen,
        actor=actor,
        actor_nombre_usuario=None if actor else ACTOR_CONSOLA,
        detalle={
            "registros": resultado.registros,
            "eventos": resultado.eventos,
            "anomalias": len(anomalias),
            **({"desde": desde} if desde is not None else {}),
            **({"hasta": hasta} if hasta is not None else {}),
            **(
                {
                    "primera": {
                        "cadena": primera.cadena,
                        "tipo_anomalia": primera.tipo.value,
                        "secuencia": primera.secuencia,
                    }
                }
                if primera
                else {}
            ),
        },
    )
    if resultado.integra:
        logger.info(
            "Integridad comprobada sin anomalías",
            extra={"registros": resultado.registros, "eventos": resultado.eventos},
        )
    else:
        logger.error(
            "Integridad comprobada con anomalías",
            extra={"anomalias": len(anomalias), "registros": resultado.registros},
        )
    return resultado


def requires_certificate() -> None:
    """La comprobación desde la web exige poder firmar sus eventos (contrato: 409)."""
    from app.core.errors import EmisionNoDisponible
    from app.services.certificado import TEXTO_MOTIVO

    estado = certificado.estado()
    if estado.motivo is not None:
        raise EmisionNoDisponible(
            "No se puede comprobar: sus eventos se firman y el certificado de firma no es "
            f"utilizable ({TEXTO_MOTIVO[estado.motivo]}).",
            extra={"faltan": ["certificado"], "motivo": estado.motivo.value},
        )

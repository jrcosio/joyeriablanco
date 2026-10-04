"""Único generador de registros de facturación (research R-6; plan).

Solo lo llama `services/emision.py`, siempre dentro de su transacción y con este orden:

1. `lock_and_verify`: toma el cerrojo de la cadena y hace la comprobación previa de F-10, art. 7.i
   sobre el último registro (huella recalculada y hora no más de un minuto posterior a la
   actual). Va ANTES de asignar número o insertar nada. Si falla, se audita y:
   - en No VERI*FACTU (004, R-5) se genera el evento 04 con su anomalía, en su propia
     transacción, y **la emisión sigue**: la facturación nunca se interrumpe por esto (F-4, p. 28;
     Orden, art. 7.j). El nuevo registro encadena con la huella guardada del último;
   - en VERI*FACTU se confirma solo el aviso y se lanza `CadenaInconsistente` sin haber emitido
     nada (F-8, art. 8.2.a: «detecte y avise»).
2. `create_registro_alta` / `create_registro_anulacion`: encadenan con el último registro,
   construyen el contenido F-1 (`domain/registro.py`), calculan la huella (`domain/huella.py`) e
   insertan con la secuencia siguiente. El trigger `validar_encadenamiento` lo vuelve a exigir.

En No VERI*FACTU (feature 004, research R-4), el registro se genera en XML, se firma con XAdES-EPES
y se valida contra el XSD ANTES de insertarlo, en la misma transacción: un registro sin firma no
existe (F-4, p. 13). Sin un certificado utilizable en la fecha de generación, la operación entera
se rechaza con `emision-no-disponible` y no se consume número.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final

from lxml import etree
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.core.config import Settings, get_settings
from app.core.errors import CadenaInconsistente, EmisionNoDisponible
from app.core.http import Origen
from app.core.tiempo import ahora
from app.domain import eventos
from app.domain.huella import (
    CamposHuellaAlta,
    CamposHuellaAnulacion,
    compute_huella,
    format_amount,
    format_date,
    format_timestamp,
)
from app.domain.registro import (
    DatosAlta,
    Destinatario,
    DetalleDesglose,
    Emisor,
    FacturaRectificada,
    RegistroAnterior,
    SistemaInformatico,
    build_contenido_alta,
    build_contenido_anulacion,
)
from app.domain.tipos import (
    EstadoRemision,
    Modalidad,
    TipoAnomalia,
    TipoEvento,
    TipoEventoSif,
    TipoFactura,
    TipoRegistro,
)
from app.domain.xml_registro import build_registro_alta, build_registro_anulacion
from app.models.factura import Factura
from app.models.registro_facturacion import RegistroFacturacion
from app.models.usuario import Usuario
from app.repositories import registros as repo
from app.services import certificado, firma
from app.services.auditoria import record_event
from app.services.certificado import CertificadoNoUtilizable

logger = logging.getLogger(__name__)

MARGEN_HORA: Final = timedelta(minutes=1)  # F-10, art. 7.f: margen de error máximo de un minuto


def sistema_informatico(settings: Settings | None = None) -> SistemaInformatico:
    ajustes = settings or get_settings()
    return SistemaInformatico(
        nombre_razon=ajustes.sif_productor_nombre,
        nif=ajustes.sif_productor_nif,
        nombre_sistema=ajustes.sif_nombre_sistema,
        id_sistema=ajustes.sif_id_sistema,
        version=__version__,
        numero_instalacion=ajustes.sif_numero_instalacion,
    )


def recompute_huella(registro: RegistroFacturacion) -> str:
    """Huella a partir de las columnas del registro, que son exactamente los campos de F-2."""
    anterior = registro.huella_anterior or ""
    if registro.tipo == TipoRegistro.ALTA:
        if (
            registro.tipo_factura is None
            or registro.cuota_total is None
            or registro.importe_total is None
        ):
            msg = f"Registro de alta incompleto (secuencia {registro.secuencia})"
            raise ValueError(msg)
        campos: CamposHuellaAlta | CamposHuellaAnulacion = CamposHuellaAlta(
            id_emisor=registro.id_emisor,
            num_serie=registro.num_serie,
            fecha_expedicion=registro.fecha_expedicion,
            tipo_factura=registro.tipo_factura,
            cuota_total=format_amount(registro.cuota_total),
            importe_total=format_amount(registro.importe_total),
            huella_anterior=anterior,
            fecha_hora_huso_gen=registro.fecha_hora_huso_gen,
        )
    else:
        campos = CamposHuellaAnulacion(
            id_emisor=registro.id_emisor,
            num_serie=registro.num_serie,
            fecha_expedicion=registro.fecha_expedicion,
            huella_anterior=anterior,
            fecha_hora_huso_gen=registro.fecha_hora_huso_gen,
        )
    return compute_huella(campos.cadena())


def tail_problem(ultimo: RegistroFacturacion, momento: datetime) -> tuple[TipoAnomalia, str] | None:
    """La anomalía (R-10) por la que el último registro no permite seguir la cadena, o `None`."""
    try:
        correcta = recompute_huella(ultimo) == ultimo.huella
    except ValueError:
        correcta = False
    if not correcta:
        return TipoAnomalia.HUELLA, "la huella del último registro no coincide con su contenido"
    if datetime.fromisoformat(ultimo.fecha_hora_huso_gen) > momento + MARGEN_HORA:
        return (
            TipoAnomalia.FECHA_FUTURA,
            "el último registro tiene una hora posterior a la actual en más de un minuto",
        )
    return None


async def lock_and_verify(
    session: AsyncSession, *, origen: Origen | None, actor: Usuario | None
) -> None:
    await repo.lock_chain(session)
    await verify_tail(session, origen=origen, actor=actor)


async def verify_tail(
    session: AsyncSession, *, origen: Origen | None, actor: Usuario | None
) -> None:
    """Comprobación previa de F-10, art. 7.i. Exige tener ya el cerrojo de la cadena."""
    ultimo = await repo.get_last(session)
    if ultimo is None:
        return
    problema = tail_problem(ultimo, ahora())
    if problema is None:
        return
    tipo_anomalia, motivo = problema
    logger.error(
        "Cadena de registros inconsistente en la secuencia %s: %s", ultimo.secuencia, motivo
    )
    await record_event(
        session,
        TipoEvento.CADENA_INCONSISTENTE,
        origen=origen,
        actor=actor,
        detalle={"secuencia": ultimo.secuencia, "motivo": motivo, "momento": "antes_de_registrar"},
    )
    if ultimo.modalidad == Modalidad.NO_VERIFACTU:  # la de la cadena: se bloquea con el primero
        from app.services import eventos_sif  # evita el ciclo de imports

        await eventos_sif.record_evento(
            session,
            eventos_sif.NuevoEvento(
                TipoEventoSif.ANOMALIA_FACTURACION,
                datos_propios=eventos.anomalia_facturacion(
                    tipo_anomalia,
                    descripcion=motivo[:1].upper() + motivo[1:],
                    factura=eventos.IdFactura(
                        ultimo.id_emisor, ultimo.num_serie, ultimo.fecha_expedicion
                    ),
                ),
                tipo_anomalia=tipo_anomalia,
                secuencia_afectada=ultimo.secuencia,
                solo_si_nueva=True,
            ),
        )
        return
    await session.commit()  # que el aviso quede aunque la operación se rechace
    raise CadenaInconsistente


@dataclass(frozen=True, slots=True)
class Firma:
    """Lo que se guarda de la firma junto al registro (data-model, `registros_facturacion`)."""

    xml: bytes
    titular: str
    huella_certificado: str


def signing_certificate(momento: datetime) -> certificado.CertificadoFirma:
    """El certificado utilizable en la fecha de generación, o el 409 con su motivo (FR-004)."""
    try:
        return certificado.utilizable(momento)
    except CertificadoNoUtilizable as exc:
        logger.warning("Registro rechazado: certificado no utilizable (%s)", exc.motivo.value)
        raise EmisionNoDisponible(
            f"No se puede emitir: el certificado de firma no es utilizable ({exc}).",
            extra={"faltan": ["certificado"], "motivo": exc.motivo.value},
        ) from exc


def _firmar(elemento: etree._Element, momento: datetime) -> Firma:
    firmante = signing_certificate(momento)
    xml = firma.sign_and_validate(elemento, firma.Esquema.SUMINISTRO, firmante, momento)
    return Firma(xml=xml, titular=firmante.titular, huella_certificado=firmante.huella)


def _columnas_firma(firma_registro: Firma | None) -> dict[str, object]:
    if firma_registro is None:  # VERI*FACTU: sin firma y pendiente de remisión (002)
        return {"estado_remision": EstadoRemision.PENDIENTE.value}
    return {
        "estado_remision": EstadoRemision.NO_APLICA.value,
        "xml_firmado": firma_registro.xml,
        "certificado_titular": firma_registro.titular,
        "certificado_huella": firma_registro.huella_certificado,
    }


def registro_anterior(ultimo: RegistroFacturacion | None) -> RegistroAnterior | None:
    """Bloque `Encadenamiento/RegistroAnterior` a partir del registro previo (o `None`)."""
    if ultimo is None:
        return None
    return RegistroAnterior(
        id_emisor=ultimo.id_emisor,
        num_serie=ultimo.num_serie,
        fecha_expedicion=ultimo.fecha_expedicion,
        huella=ultimo.huella,
    )


def datos_alta(factura: Factura, rectificada: Factura | None = None) -> DatosAlta:
    """Datos del alta a partir de la factura emitida (también para reconstruirla, FR-031)."""
    if factura.factura_rectificada_id is not None and rectificada is None:
        msg = "Una rectificativa necesita la factura que rectifica"
        raise ValueError(msg)
    datos_rectificada = None
    if rectificada is not None:
        if factura.base_rectificada is None or factura.cuota_rectificada is None:
            msg = "Una rectificativa necesita la base y la cuota rectificadas"
            raise ValueError(msg)
        datos_rectificada = FacturaRectificada(
            num_serie=rectificada.num_serie,
            fecha_expedicion=rectificada.fecha_expedicion,
            base=factura.base_rectificada,
            cuota=factura.cuota_rectificada,
        )
    return DatosAlta(
        emisor=Emisor(nif=factura.emisor_nif, nombre=factura.emisor_nombre),
        num_serie=factura.num_serie,
        fecha_expedicion=factura.fecha_expedicion,
        tipo_factura=TipoFactura(factura.tipo_factura),
        fecha_operacion=factura.fecha_operacion,
        descripcion=factura.descripcion_operacion,
        destinatario=Destinatario(
            nombre=factura.dest_nombre,
            identificacion_pais=factura.dest_identificacion_pais,
            identificacion_tipo=factura.dest_identificacion_tipo,
            identificacion_numero=factura.dest_identificacion_numero,
        ),
        # Clave, calificación y exención de cada fila del desglose, no de la cabecera (R-21): en
        # las facturas anteriores al ajuste coinciden, así que el contenido se reconstruye igual.
        desglose=tuple(
            DetalleDesglose(
                clave_regimen=d.clave_regimen,
                base=d.base,
                cuota=d.cuota,
                tipo_iva=d.tipo_iva,
                calificacion_operacion=d.calificacion_operacion,
                operacion_exenta=d.operacion_exenta,
            )
            for d in factura.desgloses
        ),
        cuota_total=factura.cuota_total,
        importe_total=factura.importe_total,
        rectificada=datos_rectificada,
    )


async def create_registro_alta(
    session: AsyncSession, factura: Factura, *, rectificada: Factura | None = None
) -> RegistroFacturacion:
    ultimo = await repo.get_last(session)
    anterior = registro_anterior(ultimo)
    momento = ahora()
    fecha_hora = format_timestamp(momento)
    fecha_expedicion = format_date(factura.fecha_expedicion)
    huella = compute_huella(
        CamposHuellaAlta(
            id_emisor=factura.emisor_nif,
            num_serie=factura.num_serie,
            fecha_expedicion=fecha_expedicion,
            tipo_factura=factura.tipo_factura,
            cuota_total=format_amount(factura.cuota_total),
            importe_total=format_amount(factura.importe_total),
            huella_anterior=anterior.huella if anterior else "",
            fecha_hora_huso_gen=fecha_hora,
        ).cadena()
    )
    contenido = build_contenido_alta(
        datos_alta(factura, rectificada),
        anterior=anterior,
        sistema=sistema_informatico(),
        fecha_hora_huso_gen=fecha_hora,
        huella=huella,
    )
    firma_registro = (
        _firmar(build_registro_alta(contenido), momento)
        if factura.modalidad == Modalidad.NO_VERIFACTU
        else None
    )
    return await repo.insert(
        session,
        RegistroFacturacion(
            secuencia=(ultimo.secuencia + 1) if ultimo else 1,
            tipo=TipoRegistro.ALTA.value,
            factura_id=factura.id,
            modalidad=factura.modalidad,
            id_emisor=factura.emisor_nif,
            num_serie=factura.num_serie,
            fecha_expedicion=fecha_expedicion,
            tipo_factura=factura.tipo_factura,
            cuota_total=factura.cuota_total,
            importe_total=factura.importe_total,
            primer_registro=anterior is None,
            huella_anterior=anterior.huella if anterior else None,
            fecha_hora_huso_gen=fecha_hora,
            tipo_huella="01",
            huella=huella,
            contenido=contenido,
            **_columnas_firma(firma_registro),
        ),
    )


async def create_registro_anulacion(
    session: AsyncSession, factura: Factura, *, modalidad: str
) -> RegistroFacturacion:
    ultimo = await repo.get_last(session)
    anterior = registro_anterior(ultimo)
    momento = ahora()
    fecha_hora = format_timestamp(momento)
    fecha_expedicion = format_date(factura.fecha_expedicion)
    huella = compute_huella(
        CamposHuellaAnulacion(
            id_emisor=factura.emisor_nif,
            num_serie=factura.num_serie,
            fecha_expedicion=fecha_expedicion,
            huella_anterior=anterior.huella if anterior else "",
            fecha_hora_huso_gen=fecha_hora,
        ).cadena()
    )
    contenido = build_contenido_anulacion(
        emisor_nif=factura.emisor_nif,
        num_serie=factura.num_serie,
        fecha_expedicion=factura.fecha_expedicion,
        anterior=anterior,
        sistema=sistema_informatico(),
        fecha_hora_huso_gen=fecha_hora,
        huella=huella,
    )
    firma_registro = (
        _firmar(build_registro_anulacion(contenido), momento)
        if modalidad == Modalidad.NO_VERIFACTU
        else None
    )
    return await repo.insert(
        session,
        RegistroFacturacion(
            secuencia=(ultimo.secuencia + 1) if ultimo else 1,
            tipo=TipoRegistro.ANULACION.value,
            factura_id=factura.id,
            modalidad=modalidad,
            id_emisor=factura.emisor_nif,
            num_serie=factura.num_serie,
            fecha_expedicion=fecha_expedicion,
            tipo_factura=None,
            cuota_total=None,
            importe_total=None,
            primer_registro=anterior is None,
            huella_anterior=anterior.huella if anterior else None,
            fecha_hora_huso_gen=fecha_hora,
            tipo_huella="01",
            huella=huella,
            contenido=contenido,
            **_columnas_firma(firma_registro),
        ),
    )

"""Único generador de registros de facturación (research R-6; plan).

Solo lo llama `services/emision.py`, siempre dentro de su transacción y con este orden:

1. `lock_and_verify`: toma el cerrojo de la cadena y hace la comprobación previa de F-10, art. 7.i
   sobre el último registro (huella recalculada y hora no más de un minuto posterior a la
   actual). Va ANTES de asignar número o insertar nada: si falla, se audita, se confirma solo ese
   evento y se lanza `CadenaInconsistente` sin haber emitido nada (F-8, art. 8.2.a: «detecte y
   avise»).
2. `create_registro_alta` / `create_registro_anulacion`: encadenan con el último registro,
   construyen el contenido F-1 (`domain/registro.py`), calculan la huella (`domain/huella.py`) e
   insertan con la secuencia siguiente. El trigger `validar_encadenamiento` lo vuelve a exigir.
"""

import logging
from datetime import datetime, timedelta
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.core.config import Settings, get_settings
from app.core.errors import CadenaInconsistente
from app.core.http import Origen
from app.core.tiempo import ahora
from app.domain.huella import (
    CamposHuellaAlta,
    CamposHuellaAnulacion,
    compute_huella,
    format_amount,
    format_date,
    format_timestamp,
)
from app.domain.importes import DesgloseTipo
from app.domain.registro import (
    DatosAlta,
    Destinatario,
    Emisor,
    FacturaRectificada,
    RegistroAnterior,
    SistemaInformatico,
    build_contenido_alta,
    build_contenido_anulacion,
)
from app.domain.tipos import EstadoRemision, TipoEvento, TipoFactura, TipoRegistro
from app.models.factura import Factura
from app.models.registro_facturacion import RegistroFacturacion
from app.models.usuario import Usuario
from app.repositories import registros as repo
from app.services.auditoria import record_event

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


def tail_problem(ultimo: RegistroFacturacion, momento: datetime) -> str | None:
    """Motivo por el que el último registro no permite seguir la cadena, o `None`."""
    if recompute_huella(ultimo) != ultimo.huella:
        return "la huella del último registro no coincide con su contenido"
    if datetime.fromisoformat(ultimo.fecha_hora_huso_gen) > momento + MARGEN_HORA:
        return "el último registro tiene una hora posterior a la actual en más de un minuto"
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
    motivo = tail_problem(ultimo, ahora())
    if motivo is None:
        return
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
    await session.commit()  # que el aviso quede aunque la operación se rechace
    raise CadenaInconsistente


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
        clave_regimen=factura.clave_regimen,
        desglose=tuple(
            DesgloseTipo(tipo_iva=d.tipo_iva, base=d.base, cuota=d.cuota) for d in factura.desgloses
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
    fecha_hora = format_timestamp(ahora())
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
            estado_remision=EstadoRemision.PENDIENTE.value,
        ),
    )


async def create_registro_anulacion(
    session: AsyncSession, factura: Factura, *, modalidad: str
) -> RegistroFacturacion:
    ultimo = await repo.get_last(session)
    anterior = registro_anterior(ultimo)
    fecha_hora = format_timestamp(ahora())
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
            estado_remision=EstadoRemision.PENDIENTE.value,
        ),
    )

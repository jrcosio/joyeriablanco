"""/v1/registro-fiscal: registro de eventos y cadena de registros, solo administradores (004).

RRSIF, art. 8.3: los eventos se consultan desde el propio sistema. Orden, art. 7.h: desde
cualquier registro o evento se salta al anterior y al siguiente.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.deps import AdminSession, DbDep, OrigenDep, require_admin
from app.domain.tipos import TipoEventoSif, TipoRegistro
from app.models.registro_evento import RegistroEvento
from app.schemas.comunes import Pagina
from app.schemas.registro_fiscal import (
    AnomaliaSalida,
    ComprobacionEntrada,
    ComprobacionSalida,
    EventoSifDetalle,
    EventoSifResumen,
    RegistroCadenaDetalle,
    Salto,
)
from app.services import registro_fiscal as servicio

router = APIRouter(
    prefix="/registro-fiscal", tags=["registro-fiscal"], dependencies=[Depends(require_admin)]
)

Secuencia = Annotated[int, Path(ge=1)]


def _salto(salto: servicio.Salto | None) -> Salto | None:
    if salto is None:
        return None
    return Salto(
        secuencia=salto.secuencia,
        encadenamiento_correcto=salto.encadenamiento_correcto,
        fechas_en_orden=salto.fechas_en_orden,
    )


def _resumen(evento: RegistroEvento) -> EventoSifResumen:
    return EventoSifResumen(
        secuencia=evento.secuencia,
        tipo_evento=TipoEventoSif(evento.tipo_evento),
        fecha_hora_huso_gen=evento.fecha_hora_huso_gen,
        huella=evento.huella,
        certificado_titular=evento.certificado_titular,
        resumen=servicio.describe(evento),
    )


@router.get("/eventos")
async def listar_eventos(
    db: DbDep,
    tipo: TipoEventoSif | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 25,
) -> Pagina[EventoSifResumen]:
    """Registro de eventos, del más reciente al más antiguo (FR-016)."""
    elementos, total = await servicio.list_events(
        db,
        tipo=tipo.value if tipo else None,
        desde=desde,
        hasta=hasta,
        pagina=pagina,
        tamano=tamano,
    )
    return Pagina[EventoSifResumen](
        elementos=[_resumen(e) for e in elementos], total=total, pagina=pagina, tamano=tamano
    )


@router.get("/eventos/{secuencia}")
async def obtener_evento(db: DbDep, secuencia: Secuencia) -> EventoSifDetalle:
    """Un evento con sus datos propios y los saltos al anterior y al siguiente (arts. 7.h, 9.3)."""
    detalle = await servicio.get_event(db, secuencia)
    resumen = _resumen(detalle.evento)
    return EventoSifDetalle(
        **resumen.model_dump(),
        datos=detalle.datos,
        huella_correcta=detalle.huella_correcta,
        firma_correcta=detalle.firma_correcta,
        anterior=_salto(detalle.anterior),
        siguiente=_salto(detalle.siguiente),
    )


@router.get("/registros/{secuencia}")
async def obtener_registro(db: DbDep, secuencia: Secuencia) -> RegistroCadenaDetalle:
    """Un registro de facturación con los saltos al anterior y al siguiente (Orden, art. 7.h)."""
    detalle = await servicio.get_record(db, secuencia)
    r = detalle.registro
    return RegistroCadenaDetalle(
        secuencia=r.secuencia,
        tipo="alta" if r.tipo == TipoRegistro.ALTA else "anulacion",
        num_serie=r.num_serie,
        factura_id=r.factura_id,
        fecha_hora_huso_gen=r.fecha_hora_huso_gen,
        huella=r.huella,
        certificado_titular=r.certificado_titular,
        huella_correcta=detalle.comprobacion.huella_correcta,
        firma_correcta=detalle.comprobacion.firma_correcta,
        anterior=_salto(detalle.anterior),
        siguiente=_salto(detalle.siguiente),
    )


@router.post("/comprobaciones", status_code=status.HTTP_201_CREATED)
async def comprobar_integridad(
    db: DbDep,
    sesion: AdminSession,
    origen: OrigenDep,
    datos: ComprobacionEntrada | None = None,
) -> ComprobacionSalida:
    """Comprueba la integridad, bajo demanda (Orden, arts. 6.b a 6.e). Genera sus eventos."""
    entrada = datos or ComprobacionEntrada()
    resultado = await servicio.check_integrity(
        db,
        desde=entrada.desde_secuencia,
        hasta=entrada.hasta_secuencia,
        actor=sesion.usuario,
        origen=origen,
    )
    return ComprobacionSalida(
        integra=resultado.integra,
        registros=resultado.registros,
        eventos=resultado.eventos,
        anomalias=[
            AnomaliaSalida(
                cadena=a.cadena,
                tipo_anomalia=a.tipo.value,
                descripcion=a.descripcion,
                secuencia=a.secuencia,
            )
            for a in resultado.anomalias
        ],
    )

"""/v1/registro-fiscal: registro de eventos y cadena de registros, solo administradores (004).

RRSIF, art. 8.3: los eventos se consultan desde el propio sistema. Orden, art. 7.h: desde
cualquier registro o evento se salta al anterior y al siguiente.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.deps import DbDep, require_admin
from app.domain.tipos import TipoEventoSif
from app.models.registro_evento import RegistroEvento
from app.schemas.comunes import Pagina
from app.schemas.registro_fiscal import EventoSifDetalle, EventoSifResumen, Salto
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

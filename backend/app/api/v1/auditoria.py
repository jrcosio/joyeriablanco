"""/v1/auditoria: consulta de solo lectura para administradores (US5; FR-051)."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbDep, require_admin
from app.domain.tipos import TipoEvento
from app.schemas.auditoria import EventoSalida
from app.schemas.comunes import Pagina
from app.services import auditoria

router = APIRouter(tags=["auditoria"], dependencies=[Depends(require_admin)])


@router.get("/auditoria")
async def consultar_auditoria(
    db: DbDep,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    usuario_id: uuid.UUID | None = None,
    tipo: TipoEvento | None = None,
    cliente_id: uuid.UUID | None = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 25,
) -> Pagina[EventoSalida]:
    eventos, total = await auditoria.query_events(
        db,
        desde=desde,
        hasta=hasta,
        usuario_id=usuario_id,
        tipo=tipo,
        cliente_id=cliente_id,
        pagina=pagina,
        tamano=tamano,
    )
    return Pagina[EventoSalida](
        elementos=[EventoSalida.from_model(e) for e in eventos],
        total=total,
        pagina=pagina,
        tamano=tamano,
    )

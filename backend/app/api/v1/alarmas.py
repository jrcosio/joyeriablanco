"""/v1/alarmas: alarmas activas de integridad y de certificado, para cualquier sesión (004).

Orden, art. 6.f: la alarma se muestra a todos los usuarios en todas las pantallas (FR-019).
"""

from fastapi import APIRouter, Depends

from app.api.deps import DbDep, get_current_session
from app.schemas.registro_fiscal import Alarma, AlarmasSalida
from app.services import alarmas

router = APIRouter(tags=["registro-fiscal"], dependencies=[Depends(get_current_session)])


@router.get("/alarmas")
async def obtener_alarmas(db: DbDep) -> AlarmasSalida:
    activas = await alarmas.active_alarms(db)
    return AlarmasSalida(
        alarmas=[
            Alarma(
                tipo=a.tipo,
                mensaje=a.mensaje,
                desde=a.desde,
                secuencia_afectada=a.secuencia_afectada,
            )
            for a in activas
        ]
    )

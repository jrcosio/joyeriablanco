"""/v1/facturas: parámetros del modal (US1); emisión, detalle, listado y correcciones (US2–US5)."""

from fastapi import APIRouter, Depends

from app.api.deps import DbDep, get_current_session
from app.schemas.configuracion_facturacion import ParametrosFacturacionSalida
from app.services import configuracion_facturacion

router = APIRouter(
    prefix="/facturas", tags=["facturas"], dependencies=[Depends(get_current_session)]
)


@router.get("/parametros")
async def obtener_parametros(db: DbDep) -> ParametrosFacturacionSalida:
    parametros = await configuracion_facturacion.get_parametros(db)
    return ParametrosFacturacionSalida(
        iva_por_defecto=parametros.iva_por_defecto,
        emision_posible=not parametros.faltan,
        faltan=parametros.faltan,
        proximo_numero=parametros.proximo_numero,
        hoy=parametros.hoy,
        fecha_minima=parametros.fecha_minima,
    )

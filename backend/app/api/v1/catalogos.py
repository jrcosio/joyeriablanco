"""/v1/catalogos: datos de apoyo para los formularios."""

from fastapi import APIRouter, Depends

from app.api.deps import DbDep, get_current_session
from app.schemas.catalogos import CatalogosSalida, ProvinciaSalida, TipoIdentificacionSalida
from app.services import catalogos

router = APIRouter(tags=["catalogos"], dependencies=[Depends(get_current_session)])


@router.get("/catalogos")
async def obtener_catalogos(db: DbDep) -> CatalogosSalida:
    datos = await catalogos.get_catalogos(db)
    return CatalogosSalida(
        provincias=[ProvinciaSalida.model_validate(p) for p in datos.provincias],
        paises=list(datos.paises),
        paises_nif_iva=list(datos.paises_nif_iva),
        tipos_identificacion=[
            TipoIdentificacionSalida(codigo=t.codigo, descripcion=t.descripcion, ambito=t.ambito)
            for t in datos.tipos_identificacion
        ],
    )

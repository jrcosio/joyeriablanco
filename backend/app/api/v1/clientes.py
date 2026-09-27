"""/v1/clientes: alta, ficha y edición (US2); listado e indicadores (US3); ciclo de vida (US4)."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentSession, DbDep, OrigenDep, get_current_session
from app.domain.tipos import TipoCliente
from app.schemas.cliente import (
    ClienteEdicionEntrada,
    ClienteEntrada,
    ClienteResumenSalida,
    ClienteSalida,
    IndicadoresSalida,
)
from app.schemas.comunes import Pagina
from app.services import clientes

router = APIRouter(
    prefix="/clientes", tags=["clientes"], dependencies=[Depends(get_current_session)]
)


@router.get("")
async def listar_clientes(
    db: DbDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    provincia: Annotated[str | None, Query(pattern=r"^[0-9]{2}$")] = None,
    tipo: TipoCliente | None = None,
    estado: Literal["activos", "inactivos", "todos"] = "activos",
    orden: Literal["nombre_asc", "nombre_desc", "recientes", "antiguos"] = "nombre_asc",
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 25,
) -> Pagina[ClienteResumenSalida]:
    filtros = clientes.FiltrosClientes(
        q=q,
        provincia=provincia,
        tipo=tipo.value if tipo else None,
        estado=estado,
        orden=orden,
        pagina=pagina,
        tamano=tamano,
    )
    elementos, total = await clientes.list_clientes(db, filtros)
    return Pagina[ClienteResumenSalida](
        elementos=[ClienteResumenSalida.from_model(c) for c in elementos],
        total=total,
        pagina=pagina,
        tamano=tamano,
    )


@router.get("/indicadores")
async def obtener_indicadores(db: DbDep) -> IndicadoresSalida:
    activos, nuevos = await clientes.indicadores(db)
    return IndicadoresSalida(activos=activos, nuevos_este_anio=nuevos)


@router.post("", status_code=status.HTTP_201_CREATED)
async def crear_cliente(
    datos: ClienteEntrada, sesion: CurrentSession, db: DbDep, origen: OrigenDep
) -> ClienteSalida:
    cliente = await clientes.create_cliente(db, datos, actor=sesion.usuario, origen=origen)
    return ClienteSalida.from_model(cliente)


@router.get("/{cliente_id}")
async def obtener_cliente(cliente_id: uuid.UUID, db: DbDep) -> ClienteSalida:
    return ClienteSalida.from_model(await clientes.get_cliente(db, cliente_id))


@router.put("/{cliente_id}")
async def editar_cliente(
    cliente_id: uuid.UUID,
    datos: ClienteEdicionEntrada,
    sesion: CurrentSession,
    db: DbDep,
    origen: OrigenDep,
) -> ClienteSalida:
    cliente = await clientes.update_cliente(
        db, cliente_id, datos, actor=sesion.usuario, origen=origen
    )
    return ClienteSalida.from_model(cliente)

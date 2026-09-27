"""/v1/clientes: alta, ficha y edición (US2); listado e indicadores (US3); ciclo de vida (US4)."""

import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentSession, DbDep, OrigenDep, get_current_session
from app.schemas.cliente import ClienteEdicionEntrada, ClienteEntrada, ClienteSalida
from app.services import clientes

router = APIRouter(
    prefix="/clientes", tags=["clientes"], dependencies=[Depends(get_current_session)]
)


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

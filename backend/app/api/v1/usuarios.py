"""/v1/usuarios: gestión de usuarios, solo administradores (US5; FR-012 a FR-017)."""

import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import AdminSession, DbDep, OrigenDep, require_admin
from app.schemas.usuario import (
    UsuarioAltaEntrada,
    UsuarioConContrasenaTemporalSalida,
    UsuarioEdicionEntrada,
    UsuarioSalida,
)
from app.services import usuarios

router = APIRouter(prefix="/usuarios", tags=["usuarios"], dependencies=[Depends(require_admin)])


@router.get("")
async def listar_usuarios(db: DbDep) -> list[UsuarioSalida]:
    return [UsuarioSalida.from_model(u) for u in await usuarios.list_usuarios(db)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    datos: UsuarioAltaEntrada, sesion: AdminSession, db: DbDep, origen: OrigenDep
) -> UsuarioConContrasenaTemporalSalida:
    usuario, temporal = await usuarios.create_usuario(
        db,
        nombre_usuario=datos.nombre_usuario,
        nombre=datos.nombre,
        rol=datos.rol,
        actor=sesion.usuario,
        origen=origen,
    )
    return UsuarioConContrasenaTemporalSalida(
        usuario=UsuarioSalida.from_model(usuario), contrasena_temporal=temporal
    )


@router.get("/{usuario_id}")
async def obtener_usuario(usuario_id: uuid.UUID, db: DbDep) -> UsuarioSalida:
    return UsuarioSalida.from_model(await usuarios.get_usuario(db, usuario_id))


@router.patch("/{usuario_id}")
async def editar_usuario(
    usuario_id: uuid.UUID,
    datos: UsuarioEdicionEntrada,
    sesion: AdminSession,
    db: DbDep,
    origen: OrigenDep,
) -> UsuarioSalida:
    usuario = await usuarios.update_usuario(
        db, usuario_id, nombre=datos.nombre, rol=datos.rol, actor=sesion.usuario, origen=origen
    )
    return UsuarioSalida.from_model(usuario)


@router.post("/{usuario_id}/desactivacion")
async def desactivar_usuario(
    usuario_id: uuid.UUID, sesion: AdminSession, db: DbDep, origen: OrigenDep
) -> UsuarioSalida:
    usuario = await usuarios.deactivate_usuario(db, usuario_id, actor=sesion.usuario, origen=origen)
    return UsuarioSalida.from_model(usuario)


@router.post("/{usuario_id}/reactivacion")
async def reactivar_usuario(
    usuario_id: uuid.UUID, sesion: AdminSession, db: DbDep, origen: OrigenDep
) -> UsuarioSalida:
    usuario = await usuarios.reactivate_usuario(db, usuario_id, actor=sesion.usuario, origen=origen)
    return UsuarioSalida.from_model(usuario)


@router.post("/{usuario_id}/restablecimiento-contrasena")
async def restablecer_contrasena(
    usuario_id: uuid.UUID, sesion: AdminSession, db: DbDep, origen: OrigenDep
) -> UsuarioConContrasenaTemporalSalida:
    usuario, temporal = await usuarios.reset_password(
        db, usuario_id, actor=sesion.usuario, origen=origen
    )
    return UsuarioConContrasenaTemporalSalida(
        usuario=UsuarioSalida.from_model(usuario), contrasena_temporal=temporal
    )

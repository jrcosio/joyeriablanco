"""Operaciones de consola: primer administrador, rescate y purga (FR-018, FR-020, FR-054)."""

import asyncio
import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from typer.testing import CliRunner

from app.cli import app as cli
from app.core.errors import NoEncontrado
from app.core.http import Origen
from app.core.security import verify_password
from app.core.tiempo import ahora
from app.domain.contrasenas import validate_password
from app.domain.tipos import Rol, TipoEvento
from app.models import Sesion
from app.services import auth, usuarios
from app.services.auditoria import ACTOR_CONSOLA
from tests.conftest import CrearUsuario, eventos


async def test_crear_primer_administrador(db: AsyncSession) -> None:
    usuario, temporal = await usuarios.create_first_admin(
        db, nombre_usuario="Admin", nombre="Administrador"
    )

    assert usuario.nombre_usuario == "admin"
    assert usuario.rol == Rol.ADMINISTRADOR
    assert usuario.contrasena_temporal is True
    assert usuario.contrasena_temporal_expira_en is not None
    assert (
        timedelta(hours=71) < usuario.contrasena_temporal_expira_en - ahora() <= timedelta(hours=72)
    )
    assert validate_password(temporal) == []
    assert verify_password(usuario.hash_contrasena, temporal)
    (evento,) = await eventos(db, TipoEvento.USUARIO_CREADO)
    assert evento.actor_id is None
    assert evento.actor_nombre_usuario == ACTOR_CONSOLA
    assert evento.detalle["origen"] == "consola"


async def test_restablecer_administrador_levanta_bloqueo_y_revoca_sesiones(
    db: AsyncSession, crear_usuario: CrearUsuario
) -> None:
    admin = await crear_usuario("jefa", rol=Rol.ADMINISTRADOR)
    admin.bloqueado_hasta = ahora() + timedelta(minutes=10)
    admin.intentos_fallidos = 5
    db.add(
        Sesion(
            usuario_id=admin.id,
            token_hash="a" * 64,
            csrf_token="c",
            expira_en=ahora() + timedelta(hours=1),
        )
    )
    await db.commit()

    temporal = await usuarios.reset_admin_from_console(db, nombre_usuario="jefa")

    await db.refresh(admin)
    bloqueo: datetime | None = admin.bloqueado_hasta
    assert verify_password(admin.hash_contrasena, temporal)
    assert admin.contrasena_temporal is True
    assert bloqueo is None
    assert admin.intentos_fallidos == 0
    vigentes = await db.scalar(
        select(func.count()).where(Sesion.usuario_id == admin.id, Sesion.revocada_en.is_(None))
    )
    assert vigentes == 0
    (evento,) = await eventos(db, TipoEvento.CONTRASENA_RESTABLECIDA)
    assert evento.actor_nombre_usuario == ACTOR_CONSOLA


async def test_restablecer_no_alcanza_a_un_administrador_eliminado(
    db: AsyncSession, crear_usuario: CrearUsuario
) -> None:
    eliminada = await crear_usuario("antigua.jefa", rol=Rol.ADMINISTRADOR, activo=False)
    actor = await crear_usuario("jefa", rol=Rol.ADMINISTRADOR)
    await usuarios.delete_usuario(
        db, eliminada.id, actor=actor, origen=Origen(ip=None, agente=None)
    )

    with pytest.raises(NoEncontrado):
        await usuarios.reset_admin_from_console(db, nombre_usuario="antigua.jefa")


async def test_purgar_solo_sesiones_caducadas_o_revocadas_hace_mas_de_30_dias(
    db: AsyncSession, crear_usuario: CrearUsuario
) -> None:
    usuario = await crear_usuario()
    for sufijo, revocada, expira in [
        ("1", ahora() - timedelta(days=31), ahora() + timedelta(hours=1)),  # se purga
        ("2", None, ahora() - timedelta(days=31)),  # se purga
        ("3", ahora() - timedelta(days=1), ahora() + timedelta(hours=1)),  # se conserva
        ("4", None, ahora() + timedelta(hours=5)),  # vigente
    ]:
        db.add(
            Sesion(
                usuario_id=usuario.id,
                token_hash=sufijo * 64,
                csrf_token="c",
                expira_en=expira,
                revocada_en=revocada,
            )
        )
    await db.commit()
    await db.execute(text("UPDATE sesiones SET ultima_actividad_en = now()"))

    purgadas = await auth.purge_sessions(db)

    assert purgadas == 2
    restantes = await db.scalar(select(func.count()).where(Sesion.usuario_id == usuario.id))
    assert restantes == 2


async def test_comando_crear_admin_muestra_la_contrasena_una_vez(
    engine_owner: AsyncEngine,
) -> None:
    """Prueba de humo del comando real: confirma en la BD, así que limpia al terminar."""
    nombre = f"admin.{uuid.uuid4().hex[:8]}"
    argumentos = ["crear-admin", "--usuario", nombre, "--nombre", "Jefa"]
    try:
        # La CLI usa su propio bucle de eventos: se ejecuta en otro hilo.
        resultado = await asyncio.to_thread(CliRunner().invoke, cli, argumentos)
        repetido = await asyncio.to_thread(CliRunner().invoke, cli, argumentos)

        assert resultado.exit_code == 0, resultado.output
        assert nombre in resultado.output
        assert "temporal" in resultado.output.lower()
        assert repetido.exit_code != 0
    finally:
        # Que este administrador no cuente en las pruebas de la regla del último administrador.
        async with engine_owner.begin() as conn:
            await conn.execute(
                text("UPDATE usuarios SET activo = false WHERE nombre_usuario = :n"), {"n": nombre}
            )

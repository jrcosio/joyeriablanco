"""Eliminación de usuarios desactivados (ajuste de cierre; FR-061, SC-013, research R-21)."""

import asyncio
import uuid
from collections.abc import Callable
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession

from app.core.errors import NoEncontrado, UsuarioActivo
from app.core.http import Origen
from app.core.security import hash_password, verify_password
from app.domain.tipos import Rol, TipoEvento
from app.models import EventoAuditoria, Sesion, Usuario
from app.services import usuarios
from tests.conftest import CONTRASENA_VALIDA, CrearUsuario, IniciarSesion, eventos

URL = "/api/v1/usuarios"
CLIENTE: dict[str, Any] = {
    "tipo": "particular",
    "nombre": "Ana Beltrán Torres",
    "identificacion_pais": "ES",
    "identificacion_tipo": "NIF",
    "identificacion_numero": "12345678Z",
    "pais_residencia": "ES",
}


@pytest.fixture
async def admin(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> Usuario:
    usuario = await crear_usuario("jefa", rol=Rol.ADMINISTRADOR, nombre="Jefa Blanco")
    client.headers["X-CSRF-Token"] = await iniciar_sesion(client, "jefa")
    return usuario


async def _desactivado(client: AsyncClient, crear_usuario: CrearUsuario) -> Usuario:
    empleado = await crear_usuario("lucia", nombre="Lucía Moreno")
    assert (await client.post(f"{URL}/{empleado.id}/desactivacion")).status_code == 200
    return empleado


async def test_eliminar_un_usuario_desactivado(
    client: AsyncClient,
    otro_cliente: Callable[[], AsyncClient],
    admin: Usuario,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    db: AsyncSession,
) -> None:
    empleado = await crear_usuario("lucia", nombre="Lucía Moreno")
    async with otro_cliente() as navegador:
        await iniciar_sesion(navegador, "lucia")  # deja una sesión que la desactivación revoca
    await client.post(f"{URL}/{empleado.id}/desactivacion")

    respuesta = await client.delete(f"{URL}/{empleado.id}")

    assert respuesta.status_code == 204, respuesta.text
    visibles = [u["id"] for u in (await client.get(URL)).json()]
    con_eliminados = await client.get(URL, params={"incluir_eliminados": True})
    todos = {u["id"]: u for u in con_eliminados.json()}
    assert str(empleado.id) not in visibles
    assert todos[str(empleado.id)]["eliminado"] is True
    assert todos[str(empleado.id)]["activo"] is False
    assert todos[str(admin.id)]["eliminado"] is False
    sesiones = await db.scalar(select(func.count()).where(Sesion.usuario_id == empleado.id))
    assert sesiones == 0
    await db.refresh(empleado)
    assert empleado.eliminado_en is not None
    assert not verify_password(empleado.hash_contrasena, CONTRASENA_VALIDA)
    assert empleado.contrasena_temporal is False
    assert empleado.bloqueado_hasta is None
    (evento,) = await eventos(db, TipoEvento.USUARIO_ELIMINADO)
    assert evento.actor_id == admin.id
    assert evento.usuario_afectado_id == empleado.id
    assert evento.detalle == {
        "nombre_usuario": "lucia",
        "nombre": "Lucía Moreno",
        "rol": "empleado",
    }


async def test_un_eliminado_no_puede_entrar(
    client: AsyncClient,
    otro_cliente: Callable[[], AsyncClient],
    admin: Usuario,
    crear_usuario: CrearUsuario,
) -> None:
    empleado = await _desactivado(client, crear_usuario)
    await client.delete(f"{URL}/{empleado.id}")

    async with otro_cliente() as navegador:
        acceso = await navegador.post(
            "/api/v1/sesion", json={"nombre_usuario": "lucia", "contrasena": CONTRASENA_VALIDA}
        )

    assert acceso.status_code == 401
    assert acceso.json()["type"] == "/problemas/credenciales"


async def test_lo_que_registro_se_conserva_intacto(
    client: AsyncClient,
    otro_cliente: Callable[[], AsyncClient],
    admin: Usuario,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    db: AsyncSession,
) -> None:
    empleado = await crear_usuario("lucia", nombre="Lucía Moreno")
    async with otro_cliente() as navegador:
        navegador.headers["X-CSRF-Token"] = await iniciar_sesion(navegador, "lucia")
        creado = await navegador.post("/api/v1/clientes", json=CLIENTE)
    assert creado.status_code == 201, creado.text
    cliente_id = creado.json()["id"]
    eventos_previos = await db.scalar(
        select(func.count()).where(
            (EventoAuditoria.actor_id == empleado.id)
            | (EventoAuditoria.usuario_afectado_id == empleado.id)
        )
    )
    await client.post(f"{URL}/{empleado.id}/desactivacion")

    await client.delete(f"{URL}/{empleado.id}")

    ficha = (await client.get(f"/api/v1/clientes/{cliente_id}")).json()
    assert ficha["version"] == creado.json()["version"]
    for campo in ("creado_por", "actualizado_por"):
        assert ficha[campo] == {"id": str(empleado.id), "nombre": "Lucía Moreno", "eliminado": True}
    eventos_despues = await db.scalar(
        select(func.count()).where(
            (EventoAuditoria.actor_id == empleado.id)
            | (EventoAuditoria.usuario_afectado_id == empleado.id)
        )
    )
    # Los anteriores siguen y se suman la desactivación y la eliminación.
    assert eventos_despues == (eventos_previos or 0) + 2
    consulta = await client.get("/api/v1/auditoria", params={"usuario_id": str(empleado.id)})
    actores = [e["actor"] for e in consulta.json()["elementos"] if e["tipo"] == "cliente_creado"]
    assert actores == [{"id": str(empleado.id), "nombre": "Lucía Moreno", "eliminado": True}]


async def test_no_se_elimina_un_usuario_activo(
    client: AsyncClient, admin: Usuario, crear_usuario: CrearUsuario, db: AsyncSession
) -> None:
    empleado = await crear_usuario("lucia")

    respuesta = await client.delete(f"{URL}/{empleado.id}")

    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == "/problemas/usuario-activo"
    assert "desactiva" in respuesta.json()["detail"].lower()
    await db.refresh(empleado)
    assert empleado.eliminado_en is None
    assert await eventos(db, TipoEvento.USUARIO_ELIMINADO) == []


async def test_un_administrador_no_puede_eliminarse(client: AsyncClient, admin: Usuario) -> None:
    respuesta = await client.delete(f"{URL}/{admin.id}")

    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == "/problemas/autogestion"


async def test_inexistente_o_ya_eliminado(
    client: AsyncClient, admin: Usuario, crear_usuario: CrearUsuario
) -> None:
    empleado = await _desactivado(client, crear_usuario)
    primera = await client.delete(f"{URL}/{empleado.id}")

    segunda = await client.delete(f"{URL}/{empleado.id}")
    inexistente = await client.delete(f"{URL}/{uuid.uuid4()}")

    assert primera.status_code == 204
    assert segunda.status_code == 404
    assert inexistente.status_code == 404


async def test_un_eliminado_queda_fuera_de_la_gestion(
    client: AsyncClient, admin: Usuario, crear_usuario: CrearUsuario
) -> None:
    empleado = await _desactivado(client, crear_usuario)
    await client.delete(f"{URL}/{empleado.id}")

    respuestas = [
        await client.get(f"{URL}/{empleado.id}"),
        await client.patch(f"{URL}/{empleado.id}", json={"nombre": "Otra"}),
        await client.post(f"{URL}/{empleado.id}/desactivacion"),
        await client.post(f"{URL}/{empleado.id}/reactivacion"),
        await client.post(f"{URL}/{empleado.id}/restablecimiento-contrasena"),
    ]

    assert [r.status_code for r in respuestas] == [404] * 5


async def test_el_nombre_de_usuario_queda_libre(
    client: AsyncClient,
    otro_cliente: Callable[[], AsyncClient],
    admin: Usuario,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
) -> None:
    antiguo = await _desactivado(client, crear_usuario)
    await client.delete(f"{URL}/{antiguo.id}")

    alta = await client.post(
        URL, json={"nombre_usuario": "Lucia", "nombre": "Lucía Pérez", "rol": "empleado"}
    )

    assert alta.status_code == 201, alta.text
    nuevo_id = alta.json()["usuario"]["id"]
    assert nuevo_id != str(antiguo.id)
    async with otro_cliente() as navegador:
        await iniciar_sesion(navegador, "lucia", alta.json()["contrasena_temporal"])
    duplicado = await client.post(
        URL, json={"nombre_usuario": "lucia", "nombre": "Tercera", "rol": "empleado"}
    )
    assert duplicado.status_code == 409  # la unicidad sigue viva entre los no eliminados

    tipos: dict[str, set[str]] = {}
    for usuario_id in (str(antiguo.id), nuevo_id):
        consulta = await client.get("/api/v1/auditoria", params={"usuario_id": usuario_id})
        tipos[usuario_id] = {e["tipo"] for e in consulta.json()["elementos"]}
    assert "usuario_eliminado" in tipos[str(antiguo.id)]
    assert "usuario_eliminado" not in tipos[nuevo_id]
    assert "acceso_correcto" in tipos[nuevo_id]


async def test_la_bd_impone_las_reglas_de_la_lapida(
    conexion: AsyncConnection, crear_usuario: CrearUsuario
) -> None:
    await crear_usuario("lucia")

    with pytest.raises(DBAPIError) as activo:
        async with conexion.begin_nested():
            await conexion.execute(
                text("UPDATE usuarios SET eliminado_en = now() WHERE nombre_usuario = 'lucia'")
            )
    with pytest.raises(DBAPIError) as duplicado:
        async with conexion.begin_nested():
            await conexion.execute(
                text(
                    "INSERT INTO usuarios (nombre_usuario, nombre, rol, hash_contrasena) "
                    "VALUES ('lucia', 'Otra', 'empleado', 'x')"
                )
            )
    await conexion.execute(
        text(
            "UPDATE usuarios SET activo = false, eliminado_en = now() "
            "WHERE nombre_usuario = 'lucia'"
        )
    )
    await conexion.execute(
        text(
            "INSERT INTO usuarios (nombre_usuario, nombre, rol, hash_contrasena) "
            "VALUES ('lucia', 'Otra', 'empleado', 'x')"
        )
    )

    assert "ck_usuarios_eliminado_inactivo" in str(activo.value)
    assert "uq_usuarios_nombre_usuario_lower" in str(duplicado.value)


async def test_reactivar_y_eliminar_a_la_vez_deja_un_estado_coherente(
    engine_app: AsyncEngine, engine_owner: AsyncEngine
) -> None:
    """La segunda operación en obtener el bloqueo ve el resultado de la primera (R-21)."""
    sufijo = uuid.uuid4().hex[:6]
    async with AsyncSession(engine_app, expire_on_commit=False) as preparacion:
        actor = Usuario(
            nombre_usuario=f"conc.actor.{sufijo}",
            nombre="Actor",
            rol="empleado",  # el servicio no depende del rol del actor
            hash_contrasena=hash_password("x" * 12),
            contrasena_temporal=False,
        )
        objetivo = Usuario(
            nombre_usuario=f"conc.obj.{sufijo}",
            nombre="Objetivo",
            rol="empleado",
            hash_contrasena=hash_password("x" * 12),
            contrasena_temporal=False,
            activo=False,
        )
        preparacion.add_all([actor, objetivo])
        await preparacion.commit()

    async def operar(nombre: str) -> str:
        async with AsyncSession(engine_app, expire_on_commit=False) as sesion:
            actor_obj = await sesion.get(Usuario, actor.id)
            assert actor_obj is not None
            origen = Origen(ip=None, agente=None)
            try:
                if nombre == "eliminar":
                    await usuarios.delete_usuario(
                        sesion, objetivo.id, actor=actor_obj, origen=origen
                    )
                else:
                    await usuarios.reactivate_usuario(
                        sesion, objetivo.id, actor=actor_obj, origen=origen
                    )
                await asyncio.sleep(0.2)  # mantiene el bloqueo mientras la otra espera
                await sesion.commit()
            except (NoEncontrado, UsuarioActivo) as error:
                await sesion.rollback()
                return type(error).__name__
            return nombre

    try:
        resultados = await asyncio.gather(operar("eliminar"), operar("reactivar"))
        async with AsyncSession(engine_app) as lectura:
            final = await lectura.get(Usuario, objetivo.id)
            assert final is not None
            assert not (final.activo and final.eliminado_en is not None)
        assert sorted(resultados) in (
            ["NoEncontrado", "eliminar"],  # la eliminación llegó antes
            ["UsuarioActivo", "reactivar"],  # la reactivación llegó antes
        )
    finally:
        async with engine_owner.begin() as conn:
            await conn.execute(
                text("UPDATE usuarios SET activo = false WHERE nombre_usuario LIKE :p"),
                {"p": f"conc.%.{sufijo}"},
            )

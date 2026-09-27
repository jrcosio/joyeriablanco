"""Gestión de usuarios por el administrador (US5; FR-012 a FR-017, FR-020)."""

import asyncio
import uuid
from collections.abc import Callable
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.errors import UltimoAdministrador
from app.core.http import Origen
from app.core.security import hash_password, verify_password
from app.domain.contrasenas import validate_password
from app.domain.tipos import Rol, TipoEvento
from app.models import Sesion, Usuario
from app.services import usuarios
from tests.conftest import CONTRASENA_VALIDA, CrearUsuario, IniciarSesion, eventos

URL = "/api/v1/usuarios"


@pytest.fixture
async def admin(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> Usuario:
    usuario = await crear_usuario("jefa", rol=Rol.ADMINISTRADOR, nombre="Jefa Blanco")
    client.headers["X-CSRF-Token"] = await iniciar_sesion(client, "jefa")
    return usuario


async def _vigentes(db: AsyncSession, usuario_id: uuid.UUID) -> int:
    total = await db.scalar(
        select(func.count()).where(Sesion.usuario_id == usuario_id, Sesion.revocada_en.is_(None))
    )
    return int(total or 0)


async def test_alta_con_contrasena_temporal_mostrada_una_vez(
    client: AsyncClient, admin: Usuario, db: AsyncSession
) -> None:
    respuesta = await client.post(
        URL, json={"nombre_usuario": "Lucia.Moreno", "nombre": "Lucía Moreno", "rol": "empleado"}
    )

    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["usuario"]["nombre_usuario"] == "lucia.moreno"
    assert cuerpo["usuario"]["contrasena_temporal"] is True
    temporal = cuerpo["contrasena_temporal"]
    assert validate_password(temporal) == []
    ficha = await client.get(f"{URL}/{cuerpo['usuario']['id']}")
    assert 'contrasena_temporal": "' not in ficha.text  # nunca se vuelve a mostrar
    assert ficha.json()["contrasena_temporal"] is True
    (evento,) = await eventos(db, TipoEvento.USUARIO_CREADO)
    assert evento.actor_id == admin.id
    assert temporal not in str(evento.detalle)


async def test_nombre_de_usuario_duplicado_sin_distinguir_mayusculas(
    client: AsyncClient, admin: Usuario, crear_usuario: CrearUsuario
) -> None:
    await crear_usuario("lucia.moreno")

    respuesta = await client.post(
        URL, json={"nombre_usuario": "LUCIA.MORENO", "nombre": "Otra", "rol": "empleado"}
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == "/problemas/duplicado"


async def test_listado_y_validacion(client: AsyncClient, admin: Usuario) -> None:
    listado = await client.get(URL)
    invalido = await client.post(URL, json={"nombre_usuario": "a b", "nombre": "", "rol": "jefe"})

    assert "jefa" in [u["nombre_usuario"] for u in listado.json()]
    assert invalido.status_code == 422
    assert {e["campo"] for e in invalido.json()["errores"]} >= {"nombre_usuario", "nombre", "rol"}


@pytest.mark.parametrize("operacion", ["rol", "desactivar", "restablecer"])
async def test_las_operaciones_sobre_un_usuario_revocan_sus_sesiones(
    client: AsyncClient,
    otro_cliente: Callable[[], AsyncClient],
    admin: Usuario,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    db: AsyncSession,
    operacion: str,
) -> None:
    empleado = await crear_usuario("lucia", rol=Rol.EMPLEADO)
    async with otro_cliente() as navegador_empleado:
        await iniciar_sesion(navegador_empleado, "lucia")
        assert await _vigentes(db, empleado.id) == 1

        if operacion == "rol":
            respuesta = await client.patch(f"{URL}/{empleado.id}", json={"rol": "administrador"})
        elif operacion == "desactivar":
            respuesta = await client.post(f"{URL}/{empleado.id}/desactivacion")
        else:
            respuesta = await client.post(f"{URL}/{empleado.id}/restablecimiento-contrasena")

        assert respuesta.status_code == 200, respuesta.text
        assert await _vigentes(db, empleado.id) == 0
        assert (await navegador_empleado.get("/api/v1/sesion")).status_code == 401


async def test_restablecer_levanta_el_bloqueo(
    client: AsyncClient, admin: Usuario, crear_usuario: CrearUsuario, db: AsyncSession
) -> None:
    empleado = await crear_usuario("lucia")
    await db.execute(
        text(
            "UPDATE usuarios SET intentos_fallidos = 5, "
            "bloqueado_hasta = now() + interval '10 minutes' WHERE nombre_usuario = 'lucia'"
        )
    )
    await db.commit()

    respuesta = await client.post(f"{URL}/{empleado.id}/restablecimiento-contrasena")

    temporal = respuesta.json()["contrasena_temporal"]
    await db.refresh(empleado)
    assert empleado.bloqueado_hasta is None
    assert empleado.intentos_fallidos == 0
    assert verify_password(empleado.hash_contrasena, temporal)
    assert respuesta.json()["usuario"]["bloqueado"] is False
    assert len(await eventos(db, TipoEvento.CONTRASENA_RESTABLECIDA)) == 1


async def test_reactivar_permite_volver_a_entrar(
    client: AsyncClient,
    otro_cliente: Callable[[], AsyncClient],
    admin: Usuario,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    db: AsyncSession,
) -> None:
    empleado = await crear_usuario("lucia")
    await client.post(f"{URL}/{empleado.id}/desactivacion")

    reactivado = await client.post(f"{URL}/{empleado.id}/reactivacion")

    assert reactivado.json()["activo"] is True
    async with otro_cliente() as navegador:
        await iniciar_sesion(navegador, "lucia", CONTRASENA_VALIDA)
    assert len(await eventos(db, TipoEvento.USUARIO_DESACTIVADO)) == 1
    assert len(await eventos(db, TipoEvento.USUARIO_REACTIVADO)) == 1


async def test_cambio_de_rol_auditado(
    client: AsyncClient, admin: Usuario, crear_usuario: CrearUsuario, db: AsyncSession
) -> None:
    empleado = await crear_usuario("lucia")

    respuesta = await client.patch(
        f"{URL}/{empleado.id}", json={"rol": "administrador", "nombre": "Lucía M."}
    )

    assert respuesta.json()["rol"] == "administrador"
    assert respuesta.json()["nombre"] == "Lucía M."
    (evento,) = await eventos(db, TipoEvento.USUARIO_ROL_CAMBIADO)
    assert evento.detalle["rol"] == ["empleado", "administrador"]
    assert evento.usuario_afectado_id == empleado.id


@pytest.mark.parametrize(
    ("operacion", "tipo"),
    [
        ({"metodo": "patch", "json": {"rol": "empleado"}}, "autogestion"),
        ({"metodo": "post", "ruta": "desactivacion"}, "autogestion"),
    ],
)
async def test_un_administrador_no_puede_desactivarse_ni_cambiar_su_rol(
    client: AsyncClient, admin: Usuario, operacion: dict[str, Any], tipo: str
) -> None:
    await admin_extra(client)  # hay otro administrador: la regla aplicada es la de autogestión
    if operacion["metodo"] == "patch":
        respuesta = await client.patch(f"{URL}/{admin.id}", json=operacion["json"])
    else:
        respuesta = await client.post(f"{URL}/{admin.id}/{operacion['ruta']}")

    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == f"/problemas/{tipo}"


async def admin_extra(client: AsyncClient) -> str:
    creado = await client.post(
        URL, json={"nombre_usuario": "segunda.jefa", "nombre": "Segunda", "rol": "administrador"}
    )
    return str(creado.json()["usuario"]["id"])


async def test_no_se_puede_dejar_el_sistema_sin_administrador(
    db: AsyncSession, crear_usuario: CrearUsuario
) -> None:
    unico = await crear_usuario("unica", rol=Rol.ADMINISTRADOR)
    actor = await crear_usuario("empleado.x")  # el servicio no depende del rol del actor
    origen = Origen(ip=None, agente=None)

    with pytest.raises(UltimoAdministrador):
        await usuarios.update_usuario(db, unico.id, rol=Rol.EMPLEADO, actor=actor, origen=origen)
    with pytest.raises(UltimoAdministrador):
        await usuarios.deactivate_usuario(db, unico.id, actor=actor, origen=origen)


async def test_regla_del_ultimo_administrador_bajo_concurrencia(
    engine_app: AsyncEngine, engine_owner: AsyncEngine
) -> None:
    """Dos degradaciones simultáneas de los dos únicos administradores: solo una prospera."""
    sufijo = uuid.uuid4().hex[:6]
    async with AsyncSession(engine_app, expire_on_commit=False) as preparacion:
        # Aislamos la prueba: ningún otro administrador activo cuenta durante ella.
        existentes = list(
            (
                await preparacion.execute(
                    select(Usuario.id).where(Usuario.rol == "administrador", Usuario.activo)
                )
            ).scalars()
        )
        a = Usuario(
            nombre_usuario=f"conc.a.{sufijo}",
            nombre="A",
            rol="administrador",
            hash_contrasena=hash_password("x" * 12),
            contrasena_temporal=False,
        )
        b = Usuario(
            nombre_usuario=f"conc.b.{sufijo}",
            nombre="B",
            rol="administrador",
            hash_contrasena=hash_password("x" * 12),
            contrasena_temporal=False,
        )
        preparacion.add_all([a, b])
        await preparacion.commit()
    assert existentes == [], "La prueba necesita que no haya otros administradores activos"

    async def degradar(objetivo: uuid.UUID, actor: uuid.UUID) -> str:
        async with AsyncSession(engine_app, expire_on_commit=False) as sesion:
            actor_obj = await sesion.get(Usuario, actor)
            assert actor_obj is not None
            try:
                await usuarios.update_usuario(
                    sesion,
                    objetivo,
                    rol=Rol.EMPLEADO,
                    actor=actor_obj,
                    origen=Origen(ip=None, agente=None),
                )
                await asyncio.sleep(0.2)  # mantiene el bloqueo mientras la otra espera
                await sesion.commit()
            except UltimoAdministrador:
                await sesion.rollback()
                return "rechazada"
            return "aplicada"

    try:
        resultados = await asyncio.gather(degradar(a.id, b.id), degradar(b.id, a.id))
        assert sorted(resultados) == ["aplicada", "rechazada"]
    finally:
        async with engine_owner.begin() as conn:  # limpieza: que no cuenten para otras pruebas
            await conn.execute(
                text("UPDATE usuarios SET activo = false WHERE nombre_usuario LIKE :p"),
                {"p": f"conc.%.{sufijo}"},
            )


async def test_un_empleado_no_accede_a_la_gestion_de_usuarios(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> None:
    empleado = await crear_usuario("lucia")
    client.headers["X-CSRF-Token"] = await iniciar_sesion(client, "lucia")

    respuestas = [
        await client.get(URL),
        await client.post(URL, json={"nombre_usuario": "x.y", "nombre": "X", "rol": "empleado"}),
        await client.get(f"{URL}/{empleado.id}"),
        await client.patch(f"{URL}/{empleado.id}", json={"nombre": "Otro"}),
        await client.post(f"{URL}/{empleado.id}/desactivacion"),
        await client.post(f"{URL}/{empleado.id}/reactivacion"),
        await client.post(f"{URL}/{empleado.id}/restablecimiento-contrasena"),
    ]

    assert {r.status_code for r in respuestas} == {403}

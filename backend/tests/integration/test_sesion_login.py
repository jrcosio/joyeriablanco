"""Inicio de sesión: cookie, mensajes genéricos, bloqueos y límite por origen.

FR-006, FR-007, FR-015, FR-020; research R-5 a R-8.
"""

from datetime import timedelta

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.http import Origen
from app.core.tiempo import ahora
from app.domain.tipos import Rol, TipoEvento
from app.repositories.auditoria import count_by_origin_since
from app.services.auditoria import record_event
from tests.conftest import CONTRASENA_VALIDA, CrearUsuario, eventos

URL = "/api/v1/sesion"
IP_CLIENTE = "127.0.0.1"  # la que asigna ASGITransport


async def _login(
    client: AsyncClient, usuario: str, contrasena: str = CONTRASENA_VALIDA
) -> Response:
    return await client.post(URL, json={"nombre_usuario": usuario, "contrasena": contrasena})


async def test_login_correcto_crea_sesion_con_cookie_segura(
    client: AsyncClient, crear_usuario: CrearUsuario, db: AsyncSession
) -> None:
    await crear_usuario("ana.garcia", rol=Rol.ADMINISTRADOR)

    respuesta = await _login(client, "Ana.Garcia")  # sin distinguir mayúsculas

    assert respuesta.status_code == 200
    cookie = respuesta.headers["set-cookie"]
    assert cookie.startswith("__Host-jb_sesion=")
    for atributo in ("HttpOnly", "Secure", "SameSite=strict", "Path=/"):
        assert atributo.lower() in cookie.lower()
    cuerpo = respuesta.json()
    assert cuerpo["csrf_token"]
    assert cuerpo["usuario"]["nombre_usuario"] == "ana.garcia"
    assert cuerpo["usuario"]["rol"] == "administrador"
    assert cuerpo["inactividad_segundos"] == 30 * 60
    assert len(await eventos(db, TipoEvento.ACCESO_CORRECTO)) == 1


async def test_la_cookie_no_es_secure_si_se_desactiva_en_desarrollo(
    client: AsyncClient, crear_usuario: CrearUsuario, monkeypatch: pytest.MonkeyPatch
) -> None:
    await crear_usuario()
    monkeypatch.setenv("SESION_COOKIE_SEGURA", "false")
    get_settings.cache_clear()
    try:
        respuesta = await _login(client, "ana.garcia")
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()

    cookie = respuesta.headers["set-cookie"]
    assert cookie.startswith("jb_sesion=")
    assert "secure" not in cookie.lower()


async def test_mensajes_genericos_identicos(
    client: AsyncClient, crear_usuario: CrearUsuario, db: AsyncSession
) -> None:
    await crear_usuario("activa")
    await crear_usuario("inactiva", activo=False)
    await crear_usuario("bloqueada")
    await crear_usuario("temporal.caducada", temporal=True)
    await db.execute(
        text(
            "UPDATE usuarios SET bloqueado_hasta = now() + interval '10 minutes' "
            "WHERE nombre_usuario = 'bloqueada'"
        )
    )
    await db.execute(
        text(
            "UPDATE usuarios SET contrasena_temporal_expira_en = now() - interval '1 minute' "
            "WHERE nombre_usuario = 'temporal.caducada'"
        )
    )
    await db.commit()

    respuestas = [
        await _login(client, "no.existe"),
        await _login(client, "activa", "contraseña-incorrecta"),
        await _login(client, "inactiva"),
        await _login(client, "bloqueada"),  # contraseña correcta, pero bloqueada
        await _login(client, "temporal.caducada"),
    ]

    assert {r.status_code for r in respuestas} == {401}
    assert len({r.text for r in respuestas}) == 1
    assert respuestas[0].json()["detail"] == "Usuario o contraseña incorrectos."
    assert "set-cookie" not in respuestas[0].headers
    fallidos = await eventos(db, TipoEvento.ACCESO_FALLIDO)
    assert {e.actor_nombre_usuario for e in fallidos} == {
        "no.existe",
        "activa",
        "inactiva",
        "bloqueada",
        "temporal.caducada",
    }
    motivos = {e.actor_nombre_usuario: e.detalle["motivo"] for e in fallidos}
    assert motivos["no.existe"] == "usuario_inexistente"
    assert motivos["temporal.caducada"] == "contrasena_temporal_caducada"
    assert all(e.origen_ip == IP_CLIENTE for e in fallidos)


async def test_bloqueo_tras_cinco_fallos_consecutivos(
    client: AsyncClient, crear_usuario: CrearUsuario, db: AsyncSession
) -> None:
    usuario = await crear_usuario()

    for _ in range(5):
        assert (await _login(client, "ana.garcia", "mala-contraseña-x")).status_code == 401

    # Bloqueada: ni siquiera la contraseña correcta sirve durante 15 minutos.
    assert (await _login(client, "ana.garcia")).status_code == 401
    await db.refresh(usuario)
    assert usuario.bloqueado_hasta is not None
    restante = usuario.bloqueado_hasta - ahora()
    assert timedelta(minutes=14) < restante <= timedelta(minutes=15)
    (bloqueo,) = await eventos(db, TipoEvento.ACCESO_BLOQUEADO)
    assert bloqueo.usuario_afectado_id == usuario.id

    # Al expirar el bloqueo, el acceso correcto funciona y el contador se reinicia.
    usuario.bloqueado_hasta = ahora() - timedelta(seconds=1)
    await db.commit()
    assert (await _login(client, "ana.garcia")).status_code == 200
    await db.refresh(usuario)
    assert usuario.intentos_fallidos == 0
    assert usuario.bloqueado_hasta is None


async def test_un_acceso_correcto_reinicia_el_contador(
    client: AsyncClient, crear_usuario: CrearUsuario, db: AsyncSession
) -> None:
    usuario = await crear_usuario()
    for _ in range(4):
        await _login(client, "ana.garcia", "mala-contraseña-x")
    assert (await _login(client, "ana.garcia")).status_code == 200

    for _ in range(4):
        await _login(client, "ana.garcia", "mala-contraseña-x")

    await db.refresh(usuario)
    assert usuario.intentos_fallidos == 4
    assert usuario.bloqueado_hasta is None


async def test_limite_por_origen(
    client: AsyncClient, crear_usuario: CrearUsuario, db: AsyncSession
) -> None:
    await crear_usuario()
    origen = Origen(ip=IP_CLIENTE, agente="pytest")
    for _ in range(19):
        await record_event(db, TipoEvento.ACCESO_FALLIDO, origen=origen, actor_nombre_usuario="x")
    for _ in range(30):  # los rechazos por límite no suman al límite
        await record_event(db, TipoEvento.ACCESO_LIMITADO, origen=origen, actor_nombre_usuario="x")
    await db.commit()

    assert (await _login(client, "ana.garcia", "mala-contraseña-x")).status_code == 401  # fallo 20
    respuesta = await _login(client, "ana.garcia")  # correcta, pero el origen está limitado

    assert respuesta.status_code == 429
    assert respuesta.json()["type"] == "/problemas/limite-origen"
    assert respuesta.json()["detail"] == (
        "Demasiados intentos desde este equipo. Inténtalo de nuevo en unos minutos."
    )
    assert len(await eventos(db, TipoEvento.ACCESO_LIMITADO)) == 31


async def test_la_ventana_del_limite_por_origen_solo_cuenta_fallos_recientes(
    db: AsyncSession,
) -> None:
    origen = Origen(ip="10.0.0.9", agente=None)
    for _ in range(3):
        await record_event(db, TipoEvento.ACCESO_FALLIDO, origen=origen, actor_nombre_usuario="x")
    await db.flush()

    recientes = await count_by_origin_since(
        db,
        origen_ip="10.0.0.9",
        tipo=TipoEvento.ACCESO_FALLIDO,
        desde=ahora() - timedelta(minutes=10),
    )
    posteriores = await count_by_origin_since(
        db,
        origen_ip="10.0.0.9",
        tipo=TipoEvento.ACCESO_FALLIDO,
        desde=ahora() + timedelta(seconds=1),
    )

    assert (recientes, posteriores) == (3, 0)


@pytest.mark.parametrize("origen", [None, "https://malicioso.example"])
async def test_login_exige_origen_permitido(
    client: AsyncClient, crear_usuario: CrearUsuario, origen: str | None
) -> None:
    await crear_usuario()
    cabeceras = {"Origin": origen} if origen else {}
    if origen is None:
        client.headers.pop("Origin", None)

    respuesta = await client.post(
        URL,
        json={"nombre_usuario": "ana.garcia", "contrasena": CONTRASENA_VALIDA},
        headers=cabeceras,
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["type"] == "/problemas/origen"


async def test_validacion_de_entrada_en_espanol(client: AsyncClient) -> None:
    respuesta = await client.post(URL, json={"nombre_usuario": ""})

    assert respuesta.status_code == 422
    errores = {e["campo"]: e["mensaje"] for e in respuesta.json()["errores"]}
    assert errores == {
        "nombre_usuario": "Debe tener al menos 1 caracteres.",
        "contrasena": "Campo obligatorio.",
    }

"""Ciclo de vida de la sesión: caducidad, cierre, CSRF, contraseña temporal y cambio.

FR-001, FR-003 a FR-005, FR-009 a FR-011, FR-016, FR-019, FR-020.
"""

from collections.abc import Callable
from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.core.tiempo import ahora
from app.domain.tipos import TipoEvento
from app.models import Sesion, Usuario
from tests.conftest import CONTRASENA_VALIDA, CrearUsuario, IniciarSesion, eventos

NUEVA = "Zafiro-Topacio-Granate-77"

pytestmark = pytest.mark.usefixtures("ruta_protegida")


async def _sesion_actual(db: AsyncSession, usuario: Usuario) -> Sesion:
    resultado = await db.execute(
        select(Sesion).where(Sesion.usuario_id == usuario.id).order_by(Sesion.creada_en.desc())
    )
    return resultado.scalars().first()  # type: ignore[return-value]


async def test_sin_sesion_no_hay_acceso(client: AsyncClient) -> None:
    for ruta in ("/api/v1/sesion", "/api/v1/_prueba"):
        respuesta = await client.get(ruta)
        assert respuesta.status_code == 401
        assert respuesta.json()["type"] == "/problemas/no-autenticado"


async def test_sesion_vigente(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> None:
    await crear_usuario()
    csrf = await iniciar_sesion(client, "ana.garcia")

    respuesta = await client.get("/api/v1/sesion")

    assert respuesta.status_code == 200
    assert respuesta.json()["csrf_token"] == csrf
    assert respuesta.headers["cache-control"] == "no-store"
    assert (await client.get("/api/v1/_prueba")).json() == {"usuario": "ana.garcia"}


async def test_caduca_tras_30_minutos_de_inactividad(
    client: AsyncClient,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    db: AsyncSession,
) -> None:
    await crear_usuario()
    await iniciar_sesion(client, "ana.garcia")
    await db.execute(
        text("UPDATE sesiones SET ultima_actividad_en = now() - interval '31 minutes'")
    )
    await db.commit()

    assert (await client.get("/api/v1/_prueba")).status_code == 401


async def test_caduca_a_las_10_horas_aunque_haya_actividad(
    client: AsyncClient,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    db: AsyncSession,
) -> None:
    usuario = await crear_usuario()
    await iniciar_sesion(client, "ana.garcia")
    sesion = await _sesion_actual(db, usuario)
    assert timedelta(hours=9, minutes=59) < sesion.expira_en - ahora() <= timedelta(hours=10)

    sesion.expira_en = ahora() - timedelta(seconds=1)
    await db.commit()

    assert (await client.get("/api/v1/_prueba")).status_code == 401


async def test_la_actividad_se_registra_como_mucho_una_vez_por_minuto(
    client: AsyncClient,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    db: AsyncSession,
) -> None:
    usuario = await crear_usuario()
    await iniciar_sesion(client, "ana.garcia")
    sesion = await _sesion_actual(db, usuario)
    reciente = ahora() - timedelta(seconds=20)
    sesion.ultima_actividad_en = reciente
    await db.commit()

    await client.get("/api/v1/_prueba")
    await db.refresh(sesion)
    assert sesion.ultima_actividad_en == reciente  # menos de 60 s: no se escribe

    sesion.ultima_actividad_en = ahora() - timedelta(minutes=5)
    await db.commit()
    await client.get("/api/v1/_prueba")
    await db.refresh(sesion)
    assert ahora() - sesion.ultima_actividad_en < timedelta(seconds=5)


async def test_cerrar_sesion_la_invalida_en_el_servidor(
    client: AsyncClient,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    db: AsyncSession,
) -> None:
    usuario = await crear_usuario()
    csrf = await iniciar_sesion(client, "ana.garcia")
    cookie = client.cookies.get("__Host-jb_sesion")

    respuesta = await client.delete("/api/v1/sesion", headers={"X-CSRF-Token": csrf})

    assert respuesta.status_code == 204
    assert "__Host-jb_sesion=" in respuesta.headers["set-cookie"]
    sesion = await _sesion_actual(db, usuario)
    assert sesion.revocada_en is not None
    # Aunque alguien reutilice la cookie antigua, ya no sirve.
    client.cookies.set("__Host-jb_sesion", cookie or "")
    assert (await client.get("/api/v1/sesion")).status_code == 401
    assert len(await eventos(db, TipoEvento.CIERRE_SESION)) == 1


@pytest.mark.parametrize("csrf", [None, "token-falso"])
async def test_peticiones_que_modifican_datos_exigen_csrf(
    client: AsyncClient,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    csrf: str | None,
) -> None:
    await crear_usuario()
    await iniciar_sesion(client, "ana.garcia")
    cabeceras = {"X-CSRF-Token": csrf} if csrf else {}

    for respuesta in (
        await client.post("/api/v1/_prueba", headers=cabeceras),
        await client.delete("/api/v1/sesion", headers=cabeceras),
    ):
        assert respuesta.status_code == 403
        assert respuesta.json()["type"] == "/problemas/csrf"


async def test_peticiones_que_modifican_datos_exigen_origen(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> None:
    await crear_usuario()
    csrf = await iniciar_sesion(client, "ana.garcia")

    respuesta = await client.post(
        "/api/v1/_prueba", headers={"X-CSRF-Token": csrf, "Origin": "https://otro.example"}
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["type"] == "/problemas/origen"


async def test_con_contrasena_temporal_solo_se_permite_cambiarla(
    client: AsyncClient,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    db: AsyncSession,
) -> None:
    usuario = await crear_usuario(temporal=True)
    csrf = await iniciar_sesion(client, "ana.garcia")

    assert (await client.get("/api/v1/sesion")).json()["usuario"]["contrasena_temporal"] is True
    bloqueada = await client.get("/api/v1/_prueba")
    assert bloqueada.status_code == 403
    assert bloqueada.json()["type"] == "/problemas/contrasena-temporal"

    cambio = await client.put(
        "/api/v1/cuenta/contrasena",
        json={"contrasena_actual": CONTRASENA_VALIDA, "contrasena_nueva": NUEVA},
        headers={"X-CSRF-Token": csrf},
    )

    assert cambio.status_code == 204
    await db.refresh(usuario)
    assert usuario.contrasena_temporal is False
    assert usuario.contrasena_temporal_expira_en is None
    assert (await client.get("/api/v1/_prueba")).status_code == 200


async def test_cambiar_la_propia_contrasena_cierra_las_demas_sesiones(
    client: AsyncClient,
    otro_cliente: Callable[[], AsyncClient],
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    db: AsyncSession,
) -> None:
    usuario = await crear_usuario()
    csrf = await iniciar_sesion(client, "ana.garcia")
    async with otro_cliente() as otro:
        await iniciar_sesion(otro, "ana.garcia")

        respuesta = await client.put(
            "/api/v1/cuenta/contrasena",
            json={"contrasena_actual": CONTRASENA_VALIDA, "contrasena_nueva": NUEVA},
            headers={"X-CSRF-Token": csrf},
        )

        assert respuesta.status_code == 204
        assert (await otro.get("/api/v1/sesion")).status_code == 401
    assert (await client.get("/api/v1/sesion")).status_code == 200
    await db.refresh(usuario)
    assert verify_password(usuario.hash_contrasena, NUEVA)
    assert len(await eventos(db, TipoEvento.CONTRASENA_CAMBIADA)) == 1


@pytest.mark.parametrize(
    ("actual", "nueva", "campo", "mensaje"),
    [
        ("incorrecta-actual", NUEVA, "contrasena_actual", "La contraseña actual no es correcta."),
        (CONTRASENA_VALIDA, "qwertyuiopasdfghjkl", "contrasena_nueva", "común"),
        (CONTRASENA_VALIDA, "clave-de-ana.garcia-2026", "contrasena_nueva", "nombre de usuario"),
        (CONTRASENA_VALIDA, "corta", "contrasena_nueva", "al menos 12"),
        (CONTRASENA_VALIDA, CONTRASENA_VALIDA, "contrasena_nueva", "distinta"),
    ],
)
async def test_cambio_de_contrasena_rechazado_con_motivo(
    client: AsyncClient,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    actual: str,
    nueva: str,
    campo: str,
    mensaje: str,
) -> None:
    await crear_usuario()
    csrf = await iniciar_sesion(client, "ana.garcia")

    respuesta = await client.put(
        "/api/v1/cuenta/contrasena",
        json={"contrasena_actual": actual, "contrasena_nueva": nueva},
        headers={"X-CSRF-Token": csrf},
    )

    assert respuesta.status_code == 422
    errores = {e["campo"]: e["mensaje"] for e in respuesta.json()["errores"]}
    assert mensaje in errores[campo]


async def test_un_usuario_desactivado_pierde_el_acceso_al_instante(
    client: AsyncClient,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    db: AsyncSession,
) -> None:
    usuario = await crear_usuario()
    await iniciar_sesion(client, "ana.garcia")

    usuario.activo = False
    await db.commit()

    assert (await client.get("/api/v1/_prueba")).status_code == 401


async def test_las_rutas_de_administracion_rechazan_a_empleados(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> None:
    await crear_usuario()
    await iniciar_sesion(client, "ana.garcia")

    respuesta = await client.get("/api/v1/_prueba/admin")

    assert respuesta.status_code == 403
    assert respuesta.json()["type"] == "/problemas/sin-permiso"

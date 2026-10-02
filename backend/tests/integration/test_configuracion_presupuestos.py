"""Validez por defecto y pie de presupuesto en la configuración (005: FR-031; research R-9)."""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.tipos import Rol, TipoEvento
from tests.conftest import CrearUsuario, IniciarSesion, eventos

URL = "/api/v1/configuracion/facturacion"


@pytest.fixture
async def csrf(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> str:
    await crear_usuario("admin.presupuestos", rol=Rol.ADMINISTRADOR)
    return await iniciar_sesion(client, "admin.presupuestos")


async def _actual(client: AsyncClient) -> dict[str, Any]:
    respuesta = await client.get(URL)
    assert respuesta.status_code == 200, respuesta.text
    return dict(respuesta.json())


def _cuerpo(actual: dict[str, Any], **cambios: Any) -> dict[str, Any]:
    cuerpo: dict[str, Any] = {
        "version": actual["version"],
        "iva_por_defecto": actual["iva_por_defecto"],
        "modalidad": actual["modalidad"],
        "emisor": {
            k: actual["emisor"][k]
            for k in ("nombre", "nif", "direccion", "codigo_postal", "localidad", "iban")
        },
    }
    cuerpo.update(cambios)
    return cuerpo


async def _guardar(client: AsyncClient, csrf: str, **cambios: Any) -> Any:
    return await client.put(
        URL, json=_cuerpo(await _actual(client), **cambios), headers={"X-CSRF-Token": csrf}
    )


async def test_valores_al_instalar(client: AsyncClient, csrf: str) -> None:
    datos = await _actual(client)

    assert datos["validez_presupuesto_dias"] == 30
    assert datos["pie_presupuesto"] is None


async def test_guardar_validez_y_pie(client: AsyncClient, csrf: str) -> None:
    respuesta = await _guardar(
        client,
        csrf,
        validez_presupuesto_dias=15,
        pie_presupuesto="  El precio del oro puede variar.\r\nEncargo con señal del 30 %.  ",
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["validez_presupuesto_dias"] == 15
    assert respuesta.json()["pie_presupuesto"] == (
        "El precio del oro puede variar.\nEncargo con señal del 30 %."
    )


@pytest.mark.parametrize(
    ("cambios", "campo"),
    [
        ({"validez_presupuesto_dias": 0}, "validez_presupuesto_dias"),
        ({"validez_presupuesto_dias": 366}, "validez_presupuesto_dias"),
        ({"pie_presupuesto": "x" * 601}, "pie_presupuesto"),
    ],
)
async def test_validaciones_en_su_campo(
    client: AsyncClient, csrf: str, cambios: dict[str, Any], campo: str
) -> None:
    respuesta = await _guardar(client, csrf, **cambios)

    assert respuesta.status_code == 422, respuesta.text
    assert any(campo in e["campo"] for e in respuesta.json()["errores"])


async def test_sin_los_campos_se_conservan_y_el_pie_se_vacia(
    client: AsyncClient, csrf: str
) -> None:
    await _guardar(client, csrf, validez_presupuesto_dias=45, pie_presupuesto="Condiciones")

    sin_campos = await _guardar(client, csrf)  # un cliente que no conoce los campos nuevos
    assert sin_campos.status_code == 200, sin_campos.text
    assert sin_campos.json()["validez_presupuesto_dias"] == 45
    assert sin_campos.json()["pie_presupuesto"] == "Condiciones"

    vaciado = await _guardar(client, csrf, pie_presupuesto="   ")
    assert vaciado.json()["pie_presupuesto"] is None
    assert vaciado.json()["validez_presupuesto_dias"] == 45


async def test_auditoria_con_el_antes_y_el_despues(
    client: AsyncClient, csrf: str, db: AsyncSession
) -> None:
    await _guardar(client, csrf, validez_presupuesto_dias=20, pie_presupuesto="Gracias")

    [evento] = await eventos(db, TipoEvento.CONFIGURACION_FACTURACION_CAMBIADA)
    cambios = evento.detalle["cambios"]
    assert cambios["validez_presupuesto_dias"] == [30, 20]  # [antes, después]
    assert cambios["pie_presupuesto"] == [None, "Gracias"]


async def test_version_desfasada_y_empleado(
    client: AsyncClient,
    csrf: str,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
) -> None:
    actual = await _actual(client)
    await _guardar(client, csrf, validez_presupuesto_dias=10)

    conflicto = await client.put(
        URL,
        json=_cuerpo(actual, validez_presupuesto_dias=12),
        headers={"X-CSRF-Token": csrf},
    )
    assert conflicto.status_code == 409

    await crear_usuario("empleado.presupuestos")
    csrf_empleado = await iniciar_sesion(client, "empleado.presupuestos")
    prohibido = await client.put(
        URL,
        json=_cuerpo(actual, validez_presupuesto_dias=60),
        headers={"X-CSRF-Token": csrf_empleado},
    )
    assert prohibido.status_code == 403

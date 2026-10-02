"""US3 — Contacto y pie de factura en la configuración (003; FR-024 a FR-027; research R-9)."""

import io
import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tiempo import hoy
from app.domain.tipos import Rol, TipoEvento
from tests.conftest import CrearUsuario, IniciarSesion, eventos
from tests.integration.facturacion_datos import cabeceras, configurar_facturacion, crear_cliente

URL = "/api/v1/configuracion/facturacion"
CONTACTO = {
    "telefono": "+34 942 000 000",
    "correo": "Info@JoyeriaBlanco.es",
    "web": "https://www.joyeriablanco.es/",
}
PIE = "Responsable del tratamiento: Joyería Blanco.\r\nPuede ejercer sus derechos en la tienda."


@pytest.fixture
async def csrf(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> str:
    await crear_usuario("admin.contacto", rol=Rol.ADMINISTRADOR)
    return await iniciar_sesion(client, "admin.contacto")


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


async def test_guardar_y_leer_contacto_y_pie(client: AsyncClient, csrf: str) -> None:
    inicial = await _actual(client)
    assert inicial["contacto"] == {"telefono": None, "correo": None, "web": None}
    assert inicial["pie_factura"] is None

    respuesta = await _guardar(client, csrf, contacto=CONTACTO, pie_factura=PIE)

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["contacto"] == {
        "telefono": "+34 942 000 000",
        "correo": "info@joyeriablanco.es",  # en minúsculas (001, FR-055)
        "web": "https://www.joyeriablanco.es/",
    }
    assert datos["pie_factura"] == (
        "Responsable del tratamiento: Joyería Blanco.\nPuede ejercer sus derechos en la tienda."
    )


async def test_no_se_exigen_para_emitir(client: AsyncClient, csrf: str, db: AsyncSession) -> None:
    await configurar_facturacion(db)

    datos = await _actual(client)

    assert datos["emision_posible"] is True
    assert datos["contacto"]["telefono"] is None
    assert not any("contacto" in f or "pie" in f for f in datos["faltan"])


@pytest.mark.parametrize(
    ("cambios", "campo"),
    [
        ({"contacto": {"telefono": "abc"}}, "contacto.telefono"),
        ({"contacto": {"telefono": "+34 94"}}, "contacto.telefono"),
        ({"contacto": {"correo": "x@"}}, "contacto.correo"),
        ({"contacto": {"web": "ftp://joyeriablanco.es"}}, "contacto.web"),
        ({"contacto": {"telefono": "9" * 31}}, "contacto.telefono"),
        ({"pie_factura": "x" * 601}, "pie_factura"),
    ],
)
async def test_validaciones_en_su_campo(
    client: AsyncClient, csrf: str, cambios: dict[str, Any], campo: str
) -> None:
    respuesta = await _guardar(client, csrf, **cambios)

    assert respuesta.status_code == 422, respuesta.text
    assert campo in [e["campo"] for e in respuesta.json()["errores"]]


async def test_sin_los_campos_se_conservan_y_con_null_se_borran(
    client: AsyncClient, csrf: str
) -> None:
    await _guardar(client, csrf, contacto=CONTACTO, pie_factura=PIE)

    sin_campos = await _guardar(client, csrf)  # un cliente que no conoce los campos nuevos
    assert sin_campos.status_code == 200, sin_campos.text
    assert sin_campos.json()["contacto"]["telefono"] == "+34 942 000 000"
    assert sin_campos.json()["pie_factura"] is not None

    vaciado = await _guardar(
        client, csrf, contacto={"telefono": None, "correo": "", "web": None}, pie_factura="  "
    )
    assert vaciado.status_code == 200, vaciado.text
    assert vaciado.json()["contacto"] == {"telefono": None, "correo": None, "web": None}
    assert vaciado.json()["pie_factura"] is None


async def test_auditoria_con_el_antes_y_el_despues(
    client: AsyncClient, csrf: str, db: AsyncSession
) -> None:
    await _guardar(client, csrf, contacto={"telefono": "942 000 000"}, pie_factura="Gracias")

    [evento] = await eventos(db, TipoEvento.CONFIGURACION_FACTURACION_CAMBIADA)
    cambios = evento.detalle["cambios"]
    assert cambios["emisor_telefono"] == [None, "942 000 000"]  # [antes, después]
    assert cambios["pie_factura"] == [None, "Gracias"]


async def test_version_desfasada_y_empleado(
    client: AsyncClient,
    csrf: str,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
) -> None:
    actual = await _actual(client)
    await _guardar(client, csrf, contacto={"telefono": "942 000 000"})

    conflicto = await client.put(
        URL,
        json=_cuerpo(actual, contacto={"telefono": "942 111 111"}),
        headers={"X-CSRF-Token": csrf},
    )
    assert conflicto.status_code == 409

    await crear_usuario("empleado.contacto")
    csrf_empleado = await iniciar_sesion(client, "empleado.contacto")
    prohibido = await client.put(
        URL, json=_cuerpo(actual, contacto=CONTACTO), headers={"X-CSRF-Token": csrf_empleado}
    )
    assert prohibido.status_code == 403


async def test_reimprimir_una_factura_antigua_lleva_el_contacto_nuevo(
    client: AsyncClient, csrf: str, db: AsyncSession, crear_usuario: CrearUsuario
) -> None:
    await configurar_facturacion(db)
    actor = await crear_usuario("actor.contacto")
    cliente = await crear_cliente(db, actor.id)
    emitida = await client.post(
        "/api/v1/facturas",
        json={
            "fecha_expedicion": hoy().isoformat(),
            "cliente_id": str(cliente.id),
            "lineas": [{"unidades": "1", "descripcion": "Anillo", "precio_unitario": "100"}],
        },
        headers=cabeceras(csrf, uuid.uuid4()),
    )
    assert emitida.status_code == 201, emitida.text
    cuerpo = _cuerpo(await _actual(client), contacto={"telefono": "942 555 555"})
    cuerpo["emisor"]["nombre"] = "Otro Nombre, S.A."
    guardado = await client.put(URL, json=cuerpo, headers={"X-CSRF-Token": csrf})
    assert guardado.status_code == 200, guardado.text

    pdf = await client.get(f"/api/v1/facturas/{emitida.json()['id']}/pdf")

    texto = " ".join(PdfReader(io.BytesIO(pdf.content)).pages[0].extract_text().split())
    assert "942 555 555" in texto
    assert "Joyería Blanco, S.L." in texto  # emisor fiscal copiado al emitir (FR-004)
    assert "Otro Nombre" not in texto

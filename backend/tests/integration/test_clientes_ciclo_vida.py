"""Ciclo de vida del cliente: desactivar, reactivar y borrar (US4; FR-036, FR-037)."""

import uuid
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.tipos import Rol, TipoEvento
from app.services.documentos import get_documentos_checker
from tests.conftest import CrearUsuario, IniciarSesion, eventos

URL = "/api/v1/clientes"
CLIENTE: dict[str, Any] = {
    "tipo": "particular",
    "nombre": "Ana Beltrán Torres",
    "identificacion_pais": "ES",
    "identificacion_tipo": "NIF",
    "identificacion_numero": "12345678Z",
    "pais_residencia": "ES",
}


async def _entrar(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion, rol: Rol
) -> None:
    nombre = f"{rol.value}.prueba"
    await crear_usuario(nombre, rol=rol)
    client.headers["X-CSRF-Token"] = await iniciar_sesion(client, nombre)


async def _crear(client: AsyncClient) -> dict[str, Any]:
    respuesta = await client.post(URL, json=CLIENTE)
    assert respuesta.status_code == 201, respuesta.text
    return dict(respuesta.json())


async def test_desactivar_y_reactivar_son_idempotentes(
    client: AsyncClient,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    db: AsyncSession,
) -> None:
    await _entrar(client, crear_usuario, iniciar_sesion, Rol.EMPLEADO)
    cliente = await _crear(client)

    primera = await client.post(f"{URL}/{cliente['id']}/desactivacion")
    segunda = await client.post(f"{URL}/{cliente['id']}/desactivacion")

    assert primera.status_code == segunda.status_code == 200
    assert primera.json()["activo"] is False
    assert len(await eventos(db, TipoEvento.CLIENTE_DESACTIVADO)) == 1
    assert (await client.get(f"{URL}/indicadores")).json()["activos"] == 0
    assert (await client.get(URL)).json()["total"] == 0
    assert (await client.get(URL, params={"estado": "inactivos"})).json()["total"] == 1

    reactivado = await client.post(f"{URL}/{cliente['id']}/reactivacion")
    await client.post(f"{URL}/{cliente['id']}/reactivacion")

    assert reactivado.json()["activo"] is True
    assert len(await eventos(db, TipoEvento.CLIENTE_REACTIVADO)) == 1
    assert (await client.get(f"{URL}/indicadores")).json()["activos"] == 1


async def test_un_cliente_inactivo_sigue_siendo_editable(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> None:
    await _entrar(client, crear_usuario, iniciar_sesion, Rol.EMPLEADO)
    cliente = await _crear(client)
    desactivado = (await client.post(f"{URL}/{cliente['id']}/desactivacion")).json()

    respuesta = await client.put(
        f"{URL}/{cliente['id']}",
        json={**CLIENTE, "localidad": "Sevilla", "version": desactivado["version"]},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is False


async def test_el_administrador_borra_un_cliente_sin_documentos(
    client: AsyncClient,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    db: AsyncSession,
) -> None:
    await _entrar(client, crear_usuario, iniciar_sesion, Rol.ADMINISTRADOR)
    cliente = await _crear(client)

    respuesta = await client.delete(f"{URL}/{cliente['id']}")

    assert respuesta.status_code == 204
    assert (await client.get(f"{URL}/{cliente['id']}")).status_code == 404
    (evento,) = await eventos(db, TipoEvento.CLIENTE_BORRADO)
    assert evento.cliente_id == uuid.UUID(cliente["id"])  # se conserva sin FK
    assert evento.detalle["instantanea"] == {
        "nombre": "Ana Beltrán Torres",
        "tipo": "particular",
        "identificacion_pais": "ES",
        "identificacion_tipo": "NIF",
        "identificacion_numero": "12345678Z",
    }


async def test_un_empleado_no_puede_borrar(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> None:
    await _entrar(client, crear_usuario, iniciar_sesion, Rol.EMPLEADO)
    cliente = await _crear(client)

    respuesta = await client.delete(f"{URL}/{cliente['id']}")

    assert respuesta.status_code == 403
    assert (await client.get(f"{URL}/{cliente['id']}")).status_code == 200


class _ConDocumentos:
    async def tiene_documentos(self, _db: AsyncSession, _cliente_id: uuid.UUID) -> bool:
        return True


async def test_no_se_borra_un_cliente_con_documentos(
    app: FastAPI,
    client: AsyncClient,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
) -> None:
    app.dependency_overrides[get_documentos_checker] = _ConDocumentos
    await _entrar(client, crear_usuario, iniciar_sesion, Rol.ADMINISTRADOR)
    cliente = await _crear(client)

    respuesta = await client.delete(f"{URL}/{cliente['id']}")

    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == "/problemas/cliente-con-documentos"
    assert (await client.get(f"{URL}/{cliente['id']}")).status_code == 200


@pytest.mark.parametrize("accion", ["desactivacion", "reactivacion"])
async def test_ciclo_de_vida_de_un_cliente_inexistente(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion, accion: str
) -> None:
    await _entrar(client, crear_usuario, iniciar_sesion, Rol.ADMINISTRADOR)
    inexistente = "0192f0c0-0000-7000-8000-000000000999"

    assert (await client.post(f"{URL}/{inexistente}/{accion}")).status_code == 404
    assert (await client.delete(f"{URL}/{inexistente}")).status_code == 404

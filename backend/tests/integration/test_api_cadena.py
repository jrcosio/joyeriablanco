"""US3 de 004 — Navegación por la cadena y «Comprobar integridad» por la API (FR-017, FR-020).

Orden, art. 7.h: desde cualquier registro se salta al anterior y al siguiente, indicando si el
encadenamiento y las fechas son correctos. La comprobación es una escritura (genera eventos): exige
CSRF y, como sus eventos se firman, un certificado utilizable (contrato: 409).
"""

import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.tipos import Rol, TipoEvento
from app.models import Cliente, RegistroEvento, Usuario
from tests.conftest import CrearUsuario, IniciarSesion, eventos
from tests.integration.facturacion_datos import (
    cabeceras,
    configurar_facturacion,
    crear_cliente,
    cuerpo_factura,
)

URL = "/api/v1/registro-fiscal"


@pytest.fixture
async def admin(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> tuple[Usuario, str]:
    usuario = await crear_usuario("admin.cadena", rol=Rol.ADMINISTRADOR)
    return usuario, await iniciar_sesion(client, "admin.cadena")


@pytest.fixture
async def tres(client: AsyncClient, db: AsyncSession, admin: tuple[Usuario, str]) -> list[str]:
    await configurar_facturacion(db)
    cliente: Cliente = await crear_cliente(db, admin[0].id)
    ids = []
    for _ in range(3):
        respuesta = await client.post(
            "/api/v1/facturas", json=cuerpo_factura(cliente.id), headers=cabeceras(admin[1])
        )
        assert respuesta.status_code == 201, respuesta.text
        ids.append(str(respuesta.json()["id"]))
    return ids


async def test_un_registro_con_sus_saltos(client: AsyncClient, tres: list[str]) -> None:
    primero = (await client.get(f"{URL}/registros/1")).json()
    segundo = (await client.get(f"{URL}/registros/2")).json()
    tercero = (await client.get(f"{URL}/registros/3")).json()
    inexistente = await client.get(f"{URL}/registros/9")

    assert segundo == {
        "secuencia": 2,
        "tipo": "alta",
        "num_serie": segundo["num_serie"],
        "factura_id": tres[1],
        "fecha_hora_huso_gen": segundo["fecha_hora_huso_gen"],
        "huella": segundo["huella"],
        "certificado_titular": "JOYERIA BLANCO (PRUEBAS)",
        "huella_correcta": True,
        "firma_correcta": True,
        "anterior": {"secuencia": 1, "encadenamiento_correcto": True, "fechas_en_orden": True},
        "siguiente": {"secuencia": 3, "encadenamiento_correcto": True, "fechas_en_orden": True},
    }
    assert primero["anterior"] is None
    assert tercero["siguiente"] is None
    assert inexistente.status_code == 404


async def test_comprobar_toda_la_cadena_o_un_rango(
    client: AsyncClient, db: AsyncSession, admin: tuple[Usuario, str], tres: list[str]
) -> None:
    csrf = {"X-CSRF-Token": admin[1]}

    entera = await client.post(f"{URL}/comprobaciones", headers=csrf)
    rango = await client.post(
        f"{URL}/comprobaciones",
        json={"desde_secuencia": 2, "hasta_secuencia": 3},
        headers=csrf,
    )

    assert entera.status_code == 201, entera.text
    assert entera.json() == {"integra": True, "registros": 3, "eventos": 0, "anomalias": []}
    assert rango.status_code == 201, rango.text
    assert rango.json()["registros"] == 2
    assert rango.json()["eventos"] == 2  # el 03 y el 05 de la primera
    [auditada, _] = await eventos(db, TipoEvento.INTEGRIDAD_COMPROBADA)
    assert auditada.actor_id == admin[0].id
    assert auditada.detalle == {"registros": 3, "eventos": 0, "anomalias": 0}


async def test_la_comprobacion_exige_csrf_y_un_rango_valido(
    client: AsyncClient, admin: tuple[Usuario, str], tres: list[str]
) -> None:
    sin_csrf = await client.post(f"{URL}/comprobaciones")
    al_reves = await client.post(
        f"{URL}/comprobaciones",
        json={"desde_secuencia": 3, "hasta_secuencia": 1},
        headers={"X-CSRF-Token": admin[1]},
    )
    desconocido = await client.post(
        f"{URL}/comprobaciones", json={"desde": 1}, headers={"X-CSRF-Token": admin[1]}
    )

    assert sin_csrf.status_code == 403
    assert al_reves.status_code == 422
    assert al_reves.json()["errores"][0]["campo"] == "hasta_secuencia"
    assert desconocido.status_code == 422


@pytest.fixture
def sin_certificado(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    monkeypatch.setenv("CERTIFICADO_RUTA", str(tmp_path / f"{uuid.uuid4()}.p12"))
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


async def test_sin_certificado_no_se_comprueba_ni_se_generan_eventos(
    client: AsyncClient,
    db: AsyncSession,
    admin: tuple[Usuario, str],
    tres: list[str],
    sin_certificado: None,
) -> None:
    respuesta = await client.post(f"{URL}/comprobaciones", headers={"X-CSRF-Token": admin[1]})

    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == "/problemas/emision-no-disponible"
    assert respuesta.json()["motivo"] == "no_instalado"
    assert await db.scalar(select(func.count()).select_from(RegistroEvento)) == 0


async def test_un_empleado_no_navega_ni_comprueba(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> None:
    await crear_usuario("empleado.cadena")
    csrf = await iniciar_sesion(client, "empleado.cadena")

    detalle = await client.get(f"{URL}/registros/1")
    comprobacion = await client.post(f"{URL}/comprobaciones", headers={"X-CSRF-Token": csrf})

    assert [detalle.status_code, comprobacion.status_code] == [403, 403]

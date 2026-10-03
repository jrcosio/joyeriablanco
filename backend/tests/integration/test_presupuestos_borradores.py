"""Borradores de presupuesto: guardar, editar, borrar y emitir (005; US1, FR-012 a FR-014)."""

from datetime import date, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tiempo import hoy
from app.domain.tipos import Serie, TipoEvento
from app.models import Cliente, ContadorFactura, Presupuesto, Usuario
from tests.conftest import CrearUsuario, IniciarSesion, eventos
from tests.integration.facturacion_datos import (
    URL_BORRADORES_PRESUPUESTO as URL,
)
from tests.integration.facturacion_datos import (
    cabeceras,
    configurar_facturacion,
    crear_cliente,
    cuerpo_presupuesto,
)


@pytest.fixture
async def empleada(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> tuple[Usuario, str]:
    usuario = await crear_usuario("empleada.presupuestos")
    return usuario, await iniciar_sesion(client, "empleada.presupuestos")


@pytest.fixture
async def maria(db: AsyncSession, empleada: tuple[Usuario, str]) -> Cliente:
    await configurar_facturacion(db)
    return await crear_cliente(db, empleada[0].id)


@pytest.fixture
def csrf(empleada: tuple[Usuario, str]) -> dict[str, str]:
    return {"X-CSRF-Token": empleada[1]}


async def _crear(client: AsyncClient, csrf: dict[str, str], datos: dict[str, Any]) -> Any:
    respuesta = await client.post(URL, json=datos, headers=csrf)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _edicion(datos: dict[str, Any], version: int) -> dict[str, Any]:
    return {**datos, "version": version}


async def _contador_pre(db: AsyncSession) -> int:
    resultado = await db.scalar(
        select(ContadorFactura.ultimo_numero).where(
            ContadorFactura.serie == Serie.PRESUPUESTO.value, ContadorFactura.anio == hoy().year
        )
    )
    return int(resultado or 0)


async def test_se_guarda_incompleto_sin_cliente_ni_lineas(
    client: AsyncClient, csrf: dict[str, str], maria: Cliente
) -> None:
    borrador = await _crear(client, csrf, cuerpo_presupuesto(None, lineas=[]))

    assert borrador["cliente"] is None
    assert borrador["lineas"] == []
    assert borrador["totales_previstos"]["importe_total"] == "0.00"
    assert borrador["valido_hasta"] == (hoy() + timedelta(days=30)).isoformat()


async def test_editar_con_version_y_conflicto(
    client: AsyncClient, csrf: dict[str, str], maria: Cliente, db: AsyncSession
) -> None:
    datos = cuerpo_presupuesto(maria.id)
    borrador = await _crear(client, csrf, datos)

    otra_linea = {"unidades": "3", "descripcion": "Pendientes", "precio_unitario": "80"}
    editado = await client.put(
        f"{URL}/{borrador['id']}",
        json=_edicion({**datos, "lineas": [otra_linea]}, borrador["version"]),
        headers=csrf,
    )
    assert editado.status_code == 200, editado.text
    assert editado.json()["totales_previstos"]["base_total"] == "240.00"
    assert editado.json()["version"] == borrador["version"] + 1

    obsoleto = await client.put(
        f"{URL}/{borrador['id']}", json=_edicion(datos, borrador["version"]), headers=csrf
    )
    assert obsoleto.status_code == 409
    assert obsoleto.json()["type"] == "/problemas/conflicto-version"

    [creado] = await eventos(db, TipoEvento.BORRADOR_PRESUPUESTO_CREADO)
    [evento] = await eventos(db, TipoEvento.BORRADOR_PRESUPUESTO_EDITADO)
    assert creado.detalle["borrador_id"] == borrador["id"]
    assert "lineas" in evento.detalle["cambios"]


async def test_un_cliente_desactivado_ya_elegido_se_conserva(
    client: AsyncClient, csrf: dict[str, str], maria: Cliente, db: AsyncSession
) -> None:
    datos = cuerpo_presupuesto(maria.id)
    borrador = await _crear(client, csrf, datos)
    maria.activo = False
    await db.flush()

    guardado = await client.put(
        f"{URL}/{borrador['id']}",
        json=_edicion({**datos, "lineas": []}, borrador["version"]),
        headers=csrf,
    )

    assert guardado.status_code == 200, guardado.text
    assert guardado.json()["cliente"]["activo"] is False


async def test_borrar_es_definitivo_auditado_y_no_consume_numero(
    client: AsyncClient, csrf: dict[str, str], maria: Cliente, db: AsyncSession
) -> None:
    borrador = await _crear(client, csrf, cuerpo_presupuesto(maria.id))

    borrado = await client.delete(f"{URL}/{borrador['id']}", headers=csrf)

    assert borrado.status_code == 204
    assert (await client.get(f"{URL}/{borrador['id']}")).status_code == 404
    [evento] = await eventos(db, TipoEvento.BORRADOR_PRESUPUESTO_ELIMINADO)
    assert evento.detalle["borrador_id"] == borrador["id"]
    assert await _contador_pre(db) == 0


@pytest.mark.parametrize(
    ("cambios", "campo"),
    [
        ({"valido_hasta": "2026-01-01", "fecha": "2026-02-01"}, "valido_hasta"),
        ({"fecha": (hoy() + timedelta(days=5)).isoformat()}, "fecha"),
        ({"fecha": "2024-10-27", "valido_hasta": "2024-11-30"}, "fecha"),
    ],
)
async def test_fecha_y_validez_se_validan_en_su_campo(
    client: AsyncClient,
    csrf: dict[str, str],
    maria: Cliente,
    cambios: dict[str, str],
    campo: str,
) -> None:
    datos = {**cuerpo_presupuesto(maria.id), **cambios}
    if campo == "fecha" and "valido_hasta" not in cambios:
        datos["valido_hasta"] = (
            date.fromisoformat(datos["fecha"]) + timedelta(days=30)
        ).isoformat()

    respuesta = await client.post(URL, json=datos, headers=csrf)

    assert respuesta.status_code == 422, respuesta.text
    assert campo in [e["campo"] for e in respuesta.json()["errores"]]


async def test_emitir_el_borrador_lo_sustituye_por_el_presupuesto(
    client: AsyncClient, csrf: dict[str, str], maria: Cliente, db: AsyncSession
) -> None:
    datos = cuerpo_presupuesto(maria.id)
    borrador = await _crear(client, csrf, datos)

    emitido = await client.post(
        f"{URL}/{borrador['id']}/emision",
        json=_edicion(datos, borrador["version"]),
        headers=cabeceras(csrf["X-CSRF-Token"]),
    )

    assert emitido.status_code == 201, emitido.text
    assert emitido.json()["num_serie"] == f"PRE-{hoy().year}-0001"
    assert (await client.get(f"{URL}/{borrador['id']}")).status_code == 404
    assert await db.scalar(select(func.count(Presupuesto.id))) == 1


async def test_emitir_un_borrador_sin_cliente_o_sin_lineas(
    client: AsyncClient, csrf: dict[str, str], maria: Cliente
) -> None:
    sin_cliente = cuerpo_presupuesto(None)
    borrador = await _crear(client, csrf, sin_cliente)
    respuesta = await client.post(
        f"{URL}/{borrador['id']}/emision",
        json=_edicion(sin_cliente, borrador["version"]),
        headers=cabeceras(csrf["X-CSRF-Token"]),
    )
    assert respuesta.status_code == 422
    assert "cliente_id" in [e["campo"] for e in respuesta.json()["errores"]]

    sin_lineas = cuerpo_presupuesto(maria.id, lineas=[])
    otro = await _crear(client, csrf, sin_lineas)
    respuesta = await client.post(
        f"{URL}/{otro['id']}/emision",
        json=_edicion(sin_lineas, otro["version"]),
        headers=cabeceras(csrf["X-CSRF-Token"]),
    )
    assert respuesta.status_code == 422
    assert "lineas" in [e["campo"] for e in respuesta.json()["errores"]]

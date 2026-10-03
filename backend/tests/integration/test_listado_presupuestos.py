"""Listado de presupuestos y borradores: búsqueda, filtros, orden, paginación y estados (005; US1,
FR-023 a FR-025).

Los presupuestos se emiten con el servicio real (`emit_presupuesto`). El estado visible añade la
caducidad con la fecha de hoy de la aplicación (research R-3), que aquí se simula.
"""

import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.http import Origen
from app.core.tiempo import hoy
from app.models import Cliente, Usuario
from app.services import contenido, presupuestos
from tests.conftest import CrearUsuario, IniciarSesion
from tests.integration.facturacion_datos import (
    URL_PRESUPUESTOS as URL,
)
from tests.integration.facturacion_datos import (
    configurar_facturacion,
    crear_borrador_presupuesto,
    crear_cliente,
)

ORIGEN = Origen(ip=None, agente="pytest")


@dataclass(frozen=True, slots=True)
class Datos:
    anio: int
    maria: Cliente
    carlos: Cliente
    caducado: uuid.UUID


async def _emitir(
    db: AsyncSession,
    actor: Usuario,
    cliente: Cliente,
    fecha: date,
    precio: str,
    *,
    validez: int = 30,
) -> uuid.UUID:
    presupuesto, _ = await presupuestos.emit_presupuesto(
        db,
        presupuestos.DatosPresupuesto(
            fecha=fecha,
            valido_hasta=fecha + timedelta(days=validez),
            cliente_id=cliente.id,
            lineas=(contenido.DatosLinea(Decimal(1), "Anillo", Decimal(precio)),),
        ),
        actor=actor,
        origen=ORIGEN,
        clave=uuid.uuid4(),
    )
    return presupuesto.id


@pytest.fixture
async def datos(
    client: AsyncClient,
    db: AsyncSession,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
) -> Datos:
    actor = await crear_usuario("empleada.listado.pre")
    csrf = await iniciar_sesion(client, "empleada.listado.pre")
    await configurar_facturacion(db)
    maria = await crear_cliente(db, actor.id)
    carlos = await crear_cliente(db, actor.id, nombre="Carlos Núñez Peña", numero="87654321X")
    anio = hoy().year
    # Fechas dentro del año en curso y no posteriores a hoy.
    enero = date(anio, 1, 15)
    await _emitir(db, actor, maria, enero, "100", validez=365)
    caducado = await _emitir(db, actor, carlos, enero, "900", validez=1)
    await _emitir(db, actor, maria, hoy(), "500")
    await _emitir(db, actor, carlos, date(anio - 1, 6, 1), "50")
    await crear_borrador_presupuesto(client, csrf, maria.id)
    return Datos(anio=anio, maria=maria, carlos=carlos, caducado=caducado)


async def _listar(client: AsyncClient, **params: Any) -> dict[str, Any]:
    respuesta = await client.get(URL, params=params)
    assert respuesta.status_code == 200, respuesta.text
    return dict(respuesta.json())


async def test_por_defecto_el_anio_en_curso_y_los_mas_recientes(
    client: AsyncClient, datos: Datos
) -> None:
    pagina = await _listar(client)

    assert pagina["total"] == 4  # 3 del año + el borrador (con la fecha de hoy)
    fechas = [e["fecha"] for e in pagina["elementos"]]
    assert fechas == sorted(fechas, reverse=True)
    borrador = next(e for e in pagina["elementos"] if e["tipo_documento"] == "borrador")
    assert borrador["num_serie"] is None
    assert borrador["estado"] == "borrador"
    assert borrador["cliente_nombre"] == "María López García"


async def test_la_validez_vencida_se_muestra_caducada(client: AsyncClient, datos: Datos) -> None:
    pagina = await _listar(client)

    estados = {e["id"]: e["estado"] for e in pagina["elementos"]}
    assert estados[str(datos.caducado)] == "caducado"
    assert sorted(estados.values()).count("pendiente") == 2


async def test_busqueda_sin_tildes_por_cliente_numero_e_identificacion(
    client: AsyncClient, datos: Datos
) -> None:
    por_cliente = await _listar(client, q="carlos nunez", anio="todos")
    assert {e["cliente_nombre"] for e in por_cliente["elementos"]} == {"Carlos Núñez Peña"}
    assert por_cliente["total"] == 2

    por_numero = await _listar(client, q=f"PRE-{datos.anio}-0003")
    assert [e["num_serie"] for e in por_numero["elementos"]] == [f"PRE-{datos.anio}-0003"]

    por_nif = await _listar(client, q="87.654.321-x", anio="todos")
    assert por_nif["total"] == 2


async def test_anio_mes_y_todos(client: AsyncClient, datos: Datos) -> None:
    assert (await _listar(client, anio="todos"))["total"] == 5
    assert (await _listar(client, anio=datos.anio - 1))["total"] == 1
    enero = await _listar(client, mes=1)
    assert {e["fecha"] for e in enero["elementos"]} == {f"{datos.anio}-01-15"}


@pytest.mark.parametrize(
    ("orden", "esperado"),
    [
        ("total_desc", ["1089.00", "605.00", "121.00"]),
        ("total_asc", ["121.00", "605.00", "1089.00"]),
    ],
)
async def test_orden_por_total(
    client: AsyncClient, datos: Datos, orden: str, esperado: list[str]
) -> None:
    pagina = await _listar(client, orden=orden)

    emitidos = [e["total"] for e in pagina["elementos"] if e["tipo_documento"] == "presupuesto"]
    assert emitidos == esperado


async def test_paginacion_sin_duplicar_ni_omitir(client: AsyncClient, datos: Datos) -> None:
    vistos: list[str] = []
    for pagina in (1, 2, 3):
        vistos += [
            e["id"]
            for e in (await _listar(client, anio="todos", tamano=2, pagina=pagina))["elementos"]
        ]

    assert len(vistos) == len(set(vistos)) == 5


async def test_tamano_maximo(client: AsyncClient, datos: Datos) -> None:
    assert (await client.get(URL, params={"tamano": 101})).status_code == 422

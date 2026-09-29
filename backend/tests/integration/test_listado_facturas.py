"""Listado de facturas y borradores: búsqueda, filtros, orden y paginación (US3; FR-032 a FR-035).

Las facturas se emiten con el servicio real (`emit_factura`), así que llevan número, copia del
destinatario y registro como cualquier otra. Los borradores se insertan con sus totales previstos
ya guardados: calcularlos es cosa del servicio de borradores (US4), la vista solo los muestra.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.http import Origen
from app.core.tiempo import hoy
from app.models import Cliente, Usuario
from app.models.borrador_factura import BorradorFactura
from app.services import emision
from tests.conftest import CrearUsuario, IniciarSesion
from tests.integration.facturacion_datos import configurar_facturacion, crear_cliente

URL = "/api/v1/facturas"
ORIGEN = Origen(ip=None, agente="pytest")


@dataclass(frozen=True, slots=True)
class Datos:
    anio: int
    maria: Cliente
    carlos: Cliente
    borrador_maria: uuid.UUID
    borrador_sin_cliente: uuid.UUID


async def _emitir(
    db: AsyncSession, actor: Usuario, cliente: Cliente, fecha: date, precio: str
) -> None:
    await emision.emit_factura(
        db,
        emision.DatosFactura(
            fecha_expedicion=fecha,
            cliente_id=cliente.id,
            lineas=(emision.DatosLinea(Decimal(1), "Anillo", Decimal(precio)),),
        ),
        actor=actor,
        origen=ORIGEN,
        clave=uuid.uuid4(),
    )


def _borrador(actor: Usuario, cliente: Cliente | None, base: str) -> BorradorFactura:
    importe = Decimal(base)
    cuota = (importe * Decimal("0.21")).quantize(Decimal("0.01"))
    return BorradorFactura(
        cliente_id=cliente.id if cliente else None,
        fecha_expedicion=hoy(),
        tipo_iva_previsto=Decimal("21.00"),
        base_prevista=importe,
        cuota_prevista=cuota,
        total_previsto=importe + cuota,
        creado_por_id=actor.id,
        actualizado_por_id=actor.id,
    )


@pytest.fixture
async def datos(
    client: AsyncClient,
    db: AsyncSession,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
) -> Datos:
    """Dos facturas del año anterior (noviembre y diciembre), tres de hoy y dos borradores de hoy.

    Totales: año anterior 121,00 y 60,50; hoy 1.560,90 (María), 12,10 (Carlos) y 605,00 (María);
    borradores 242,00 (María) y 0,00 (sin cliente).
    """
    actor = await crear_usuario("listado.facturas")
    await iniciar_sesion(client, "listado.facturas")
    await configurar_facturacion(db)
    maria = await crear_cliente(db, actor.id)
    carlos = await crear_cliente(db, actor.id, nombre="Carlos Martín Ruiz", numero="45678901G")
    anio = hoy().year
    await _emitir(db, actor, maria, date(anio - 1, 11, 10), "100")
    await _emitir(db, actor, carlos, date(anio - 1, 12, 5), "50")
    await _emitir(db, actor, maria, hoy(), "1290")
    await _emitir(db, actor, carlos, hoy(), "10")
    await _emitir(db, actor, maria, hoy(), "500")
    con_cliente = _borrador(actor, maria, "200")
    sin_cliente = _borrador(actor, None, "0")
    db.add_all([con_cliente, sin_cliente])
    await db.commit()
    return Datos(anio, maria, carlos, con_cliente.id, sin_cliente.id)


def _etiquetas(respuesta: Any) -> list[str]:
    """Número de cada fila, o «B:<cliente>» para los borradores."""
    assert respuesta.status_code == 200, respuesta.text
    return [
        f["num_serie"] if f["tipo_documento"] == "factura" else f"B:{f['cliente_nombre']}"
        for f in respuesta.json()["elementos"]
    ]


async def _listar(client: AsyncClient, **params: Any) -> Any:
    return await client.get(URL, params=params)


# ------------------------------------------------------------------------ contenido y filtros


async def test_por_defecto_el_anio_en_curso_con_borradores_primero(
    client: AsyncClient, datos: Datos
) -> None:
    respuesta = await _listar(client)

    a = datos.anio
    etiquetas = _etiquetas(respuesta)
    assert sorted(etiquetas[:2], key=str) == ["B:María López García", "B:None"]
    assert etiquetas[2:] == [f"FAC-{a}-0003", f"FAC-{a}-0002", f"FAC-{a}-0001"]
    cuerpo = respuesta.json()
    assert (cuerpo["total"], cuerpo["pagina"], cuerpo["tamano"]) == (5, 1, 25)


async def test_las_filas_llevan_los_campos_del_contrato_con_importes_en_texto(
    client: AsyncClient, datos: Datos
) -> None:
    filas = {f["id"]: f for f in (await _listar(client)).json()["elementos"]}

    borrador = filas[str(datos.borrador_maria)]
    assert borrador == {
        "tipo_documento": "borrador",
        "id": str(datos.borrador_maria),
        "num_serie": None,
        "fecha": hoy().isoformat(),
        "cliente_nombre": "María López García",
        "identificacion": "12345678Z",
        "base": "200.00",
        "cuota": "42.00",
        "total": "242.00",
        "estado": "borrador",
    }
    assert filas[str(datos.borrador_sin_cliente)]["cliente_nombre"] is None
    factura = next(f for f in filas.values() if f["num_serie"] == f"FAC-{datos.anio}-0001")
    assert (factura["base"], factura["cuota"], factura["total"]) == ("1290.00", "270.90", "1560.90")
    assert factura["estado"] == "vigente"
    assert factura["identificacion"] == "12345678Z"


@pytest.mark.parametrize(
    ("desfase", "mes", "esperadas"),
    [
        (-1, None, ["FAC-{p}-0002", "FAC-{p}-0001"]),
        (-1, 12, ["FAC-{p}-0002"]),
        (-1, 11, ["FAC-{p}-0001"]),
        (-1, 3, []),
    ],
)
async def test_filtra_por_anio_y_mes(
    client: AsyncClient, datos: Datos, desfase: int, mes: int | None, esperadas: list[str]
) -> None:
    params: dict[str, Any] = {"anio": datos.anio + desfase}
    if mes is not None:
        params["mes"] = mes

    etiquetas = _etiquetas(await _listar(client, **params))

    assert etiquetas == [e.format(p=datos.anio - 1) for e in esperadas]


async def test_todos_los_anios_y_mes_sin_anio(client: AsyncClient, datos: Datos) -> None:
    todos = await _listar(client, anio="todos")
    assert todos.json()["total"] == 7

    diciembre = _etiquetas(await _listar(client, anio="todos", mes=12))
    esperadas = {f"FAC-{datos.anio - 1}-0002"}
    if hoy().month == 12:  # las de hoy también son de diciembre
        esperadas |= {f"FAC-{datos.anio}-000{n}" for n in (1, 2, 3)}
        esperadas |= {"B:María López García", "B:None"}
    assert set(diciembre) == esperadas


# ------------------------------------------------------------------------------- búsqueda


async def test_busca_por_parte_del_numero(client: AsyncClient, datos: Datos) -> None:
    etiquetas = _etiquetas(await _listar(client, q=f"{datos.anio}-0002"))

    assert etiquetas == [f"FAC-{datos.anio}-0002"]


@pytest.mark.parametrize("q", ["maria lopez", "MARÍA LÓPEZ", "12.345.678-z", "345678"])
async def test_busca_por_cliente_sin_tildes_y_por_identificacion(
    client: AsyncClient, datos: Datos, q: str
) -> None:
    etiquetas = _etiquetas(await _listar(client, q=q))

    a = datos.anio
    assert etiquetas == ["B:María López García", f"FAC-{a}-0003", f"FAC-{a}-0001"]


async def test_los_comodines_de_la_busqueda_se_toman_literalmente(
    client: AsyncClient, datos: Datos
) -> None:
    for q in ("%", "_", "FAC\\"):
        assert _etiquetas(await _listar(client, q=q, anio="todos")) == [], q


# --------------------------------------------------------------------------------- órdenes


async def test_ordenes_por_fecha_y_por_total(client: AsyncClient, datos: Datos) -> None:
    a = datos.anio

    antiguas = _etiquetas(await _listar(client, orden="antiguas"))
    assert antiguas[:3] == [f"FAC-{a}-0001", f"FAC-{a}-0002", f"FAC-{a}-0003"]
    assert sorted(antiguas[3:], key=str) == ["B:María López García", "B:None"]

    mayor = _etiquetas(await _listar(client, orden="total_desc"))
    assert mayor == [
        f"FAC-{a}-0001",  # 1.560,90
        f"FAC-{a}-0003",  # 605,00
        "B:María López García",  # 242,00
        f"FAC-{a}-0002",  # 12,10
        "B:None",  # 0,00
    ]
    menor = _etiquetas(await _listar(client, orden="total_asc"))
    assert menor == list(reversed(mayor))


@pytest.mark.parametrize("orden", ["recientes", "antiguas", "total_desc", "total_asc"])
async def test_recorrer_las_paginas_no_duplica_ni_omite(
    client: AsyncClient, datos: Datos, orden: str
) -> None:
    todas = await _listar(client, anio="todos", orden=orden)
    completo = [f["id"] for f in todas.json()["elementos"]]
    paginado: list[str] = []
    for pagina in range(1, 5):
        respuesta = await _listar(client, anio="todos", orden=orden, tamano=2, pagina=pagina)
        assert respuesta.json()["total"] == 7
        paginado += [f["id"] for f in respuesta.json()["elementos"]]

    assert paginado == completo
    assert len(set(paginado)) == 7


# ---------------------------------------------------------------------------- casos límite


async def test_una_pagina_posterior_a_la_ultima_viene_vacia_con_el_total_real(
    client: AsyncClient, datos: Datos
) -> None:
    respuesta = await _listar(client, pagina=10)

    assert respuesta.status_code == 200
    assert respuesta.json()["elementos"] == []
    assert respuesta.json()["total"] == 5


@pytest.mark.parametrize(
    "params",
    [
        {"anio": 2023},
        {"anio": "ninguno"},
        {"mes": 0},
        {"mes": 13},
        {"orden": "numero"},
        {"tamano": 101},
        {"pagina": 0},
        {"q": "x" * 101},
    ],
)
async def test_parametros_no_validos(
    client: AsyncClient, datos: Datos, params: dict[str, Any]
) -> None:
    respuesta = await _listar(client, **params)

    assert respuesta.status_code == 422, params


async def test_sin_sesion_no_hay_listado(client: AsyncClient) -> None:
    respuesta = await client.get(URL)

    assert respuesta.status_code == 401

"""Listado, búsqueda, filtros, orden, paginación e indicadores (US3; FR-031 a FR-034)."""

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tiempo import ahora
from app.models import Cliente, Usuario
from tests.conftest import CrearUsuario, IniciarSesion

URL = "/api/v1/clientes"
MADRID = ZoneInfo("Europe/Madrid")

CrearCliente = Callable[..., Awaitable[Cliente]]


@pytest.fixture
async def autor(crear_usuario: CrearUsuario) -> Usuario:
    return await crear_usuario("ana.garcia")


@pytest.fixture
async def sesion(client: AsyncClient, autor: Usuario, iniciar_sesion: IniciarSesion) -> None:
    await iniciar_sesion(client, "ana.garcia")


@pytest.fixture
def crear_cliente(db: AsyncSession, autor: Usuario) -> CrearCliente:
    contador = {"n": 0}

    async def _crear(nombre: str, **campos: Any) -> Cliente:
        contador["n"] += 1
        datos: dict[str, Any] = {
            "tipo": "particular",
            "nombre": nombre,
            "identificacion_pais": "ES",
            "identificacion_tipo": "03",
            "identificacion_numero": f"PAS{contador['n']:06d}",
            "pais_residencia": "ES",
            "creado_por_id": autor.id,
            "actualizado_por_id": autor.id,
        }
        datos.update(campos)
        cliente = Cliente(**datos)
        db.add(cliente)
        await db.commit()
        return cliente

    return _crear


def nombres(respuesta: Any) -> list[str]:
    return [c["nombre"] for c in respuesta.json()["elementos"]]


@pytest.mark.usefixtures("sesion")
async def test_por_defecto_solo_activos_ordenados_por_nombre(
    client: AsyncClient, crear_cliente: CrearCliente
) -> None:
    await crear_cliente("Carlos Martín Ruiz")
    await crear_cliente("Ana Beltrán Torres")
    await crear_cliente("Baja Antigua", activo=False)

    respuesta = await client.get(URL)

    assert respuesta.status_code == 200
    assert nombres(respuesta) == ["Ana Beltrán Torres", "Carlos Martín Ruiz"]
    cuerpo = respuesta.json()
    assert (cuerpo["total"], cuerpo["pagina"], cuerpo["tamano"]) == (2, 1, 25)


@pytest.mark.usefixtures("sesion")
@pytest.mark.parametrize(
    ("q", "esperados"),
    [
        ("maria lopez", ["María López García"]),
        ("MÁLAGA", ["Joyería Serrano"]),
        ("serr", ["Joyería Serrano"]),
        ("12.345.678-z", ["María López García"]),
        ("5678", ["María López García"]),
        ("100%", []),  # los comodines se buscan literalmente
        ("_", []),
    ],
)
async def test_busqueda_sin_tildes_ni_mayusculas(
    client: AsyncClient, crear_cliente: CrearCliente, q: str, esperados: list[str]
) -> None:
    await crear_cliente(
        "María López García",
        identificacion_tipo="NIF",
        identificacion_numero="12345678Z",
        localidad="Granada",
    )
    await crear_cliente("Joyería Serrano", tipo="empresa", localidad="Málaga")

    respuesta = await client.get(URL, params={"q": q})

    assert nombres(respuesta) == esperados


@pytest.mark.usefixtures("sesion")
async def test_filtros_combinados(client: AsyncClient, crear_cliente: CrearCliente) -> None:
    await crear_cliente("Empresa Málaga", tipo="empresa", provincia_codigo="29")
    await crear_cliente("Particular Málaga", provincia_codigo="29")
    await crear_cliente("Empresa Granada", tipo="empresa", provincia_codigo="18")
    await crear_cliente(
        "Empresa Málaga Inactiva", tipo="empresa", provincia_codigo="29", activo=False
    )

    solo_activas = await client.get(URL, params={"provincia": "29", "tipo": "empresa"})
    todas = await client.get(URL, params={"provincia": "29", "tipo": "empresa", "estado": "todos"})
    inactivas = await client.get(URL, params={"estado": "inactivos"})
    busqueda = await client.get(URL, params={"q": "empresa", "provincia": "18"})

    assert nombres(solo_activas) == ["Empresa Málaga"]
    assert nombres(todas) == ["Empresa Málaga", "Empresa Málaga Inactiva"]
    assert nombres(inactivas) == ["Empresa Málaga Inactiva"]
    assert nombres(busqueda) == ["Empresa Granada"]
    assert solo_activas.json()["elementos"][0]["provincia_nombre"] == "Málaga"


@pytest.mark.usefixtures("sesion")
async def test_ordenaciones(client: AsyncClient, crear_cliente: CrearCliente) -> None:
    base = ahora()
    await crear_cliente("Beatriz", creado_en=base - timedelta(days=2))
    await crear_cliente("Álvaro", creado_en=base - timedelta(days=1))
    await crear_cliente("Carmen", creado_en=base - timedelta(days=3))

    assert nombres(await client.get(URL, params={"orden": "nombre_asc"})) == [
        "Álvaro",
        "Beatriz",
        "Carmen",
    ]
    assert nombres(await client.get(URL, params={"orden": "nombre_desc"})) == [
        "Carmen",
        "Beatriz",
        "Álvaro",
    ]
    assert nombres(await client.get(URL, params={"orden": "recientes"})) == [
        "Álvaro",
        "Beatriz",
        "Carmen",
    ]
    assert nombres(await client.get(URL, params={"orden": "antiguos"})) == [
        "Carmen",
        "Beatriz",
        "Álvaro",
    ]


@pytest.mark.usefixtures("sesion")
async def test_paginacion_estable_sin_duplicados_ni_omisiones(
    client: AsyncClient, crear_cliente: CrearCliente
) -> None:
    for i in range(7):
        await crear_cliente("Mismo Nombre", identificacion_numero=f"EMP{i:06d}")

    vistos: list[str] = []
    for pagina in (1, 2, 3):
        respuesta = await client.get(URL, params={"pagina": pagina, "tamano": 3})
        vistos += [c["id"] for c in respuesta.json()["elementos"]]
        assert respuesta.json()["total"] == 7

    assert len(vistos) == 7
    assert len(set(vistos)) == 7
    vacia = await client.get(URL, params={"pagina": 9, "tamano": 3})
    assert vacia.json()["elementos"] == []
    assert vacia.json()["total"] == 7


@pytest.mark.usefixtures("sesion")
@pytest.mark.parametrize(
    "params",
    [{"q": "x" * 101}, {"tamano": 101}, {"pagina": 0}, {"orden": "otro"}, {"provincia": "5"}],
)
async def test_parametros_no_validos(client: AsyncClient, params: dict[str, Any]) -> None:
    assert (await client.get(URL, params=params)).status_code == 422


@pytest.mark.usefixtures("sesion")
async def test_indicadores_globales_con_el_ano_natural_en_hora_peninsular(
    client: AsyncClient, crear_cliente: CrearCliente
) -> None:
    inicio_ano = datetime(ahora().astimezone(MADRID).year, 1, 1, tzinfo=MADRID)
    await crear_cliente("Nuevo activo", creado_en=inicio_ano + timedelta(minutes=1))
    await crear_cliente("Nuevo inactivo", creado_en=inicio_ano + timedelta(days=3), activo=False)
    await crear_cliente("Del año pasado", creado_en=inicio_ano - timedelta(minutes=1))

    respuesta = await client.get(f"{URL}/indicadores", params={"q": "nada que ver"})

    assert respuesta.status_code == 200
    assert respuesta.json() == {"activos": 2, "nuevos_este_anio": 2}

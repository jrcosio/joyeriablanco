"""Consulta de la auditoría por el administrador (US5; FR-051)."""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.http import Origen
from app.domain.tipos import Rol, TipoEvento
from app.models import Usuario
from app.services.auditoria import record_event
from tests.conftest import CrearUsuario, IniciarSesion

URL = "/api/v1/auditoria"


async def test_filtros_orden_y_paginacion(
    client: AsyncClient,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    db: AsyncSession,
) -> None:
    jefa = await crear_usuario("jefa", rol=Rol.ADMINISTRADOR, nombre="Jefa Blanco")
    lucia: Usuario = await crear_usuario("lucia", nombre="Lucía Moreno")
    await iniciar_sesion(client, "jefa")  # genera acceso_correcto de jefa
    cliente_id = uuid.uuid4()
    origen = Origen(ip="10.1.1.1", agente="pytest")
    await record_event(
        db, TipoEvento.CLIENTE_CREADO, origen=origen, actor=lucia, cliente_id=cliente_id
    )
    await record_event(
        db,
        TipoEvento.CLIENTE_EDITADO,
        origen=origen,
        actor=lucia,
        cliente_id=cliente_id,
        detalle={"cambios": {"localidad": ["Málaga", "Ronda"]}},
    )
    await record_event(
        db, TipoEvento.USUARIO_DESACTIVADO, origen=origen, actor=jefa, usuario_afectado_id=lucia.id
    )
    await db.commit()

    todos = (await client.get(URL)).json()
    por_tipo = (await client.get(URL, params={"tipo": "cliente_editado"})).json()
    por_cliente = (await client.get(URL, params={"cliente_id": str(cliente_id)})).json()
    por_usuario = (await client.get(URL, params={"usuario_id": str(lucia.id)})).json()
    combinado = (
        await client.get(URL, params={"usuario_id": str(lucia.id), "tipo": "cliente_creado"})
    ).json()
    pagina = (await client.get(URL, params={"tamano": 2, "pagina": 2})).json()

    assert todos["total"] == 4
    assert por_tipo["total"] == 1
    editado = por_tipo["elementos"][0]
    assert editado["actor"]["nombre"] == "Lucía Moreno"
    assert editado["origen_ip"] == "10.1.1.1"
    assert editado["detalle"] == {"cambios": {"localidad": ["Málaga", "Ronda"]}}
    assert por_cliente["total"] == 2
    assert por_usuario["total"] == 3  # como actor (2) o como usuario afectado (1)
    assert combinado["total"] == 1
    assert len(pagina["elementos"]) == 2
    fechas = [e["ocurrido_en"] for e in todos["elementos"]]
    assert fechas == sorted(fechas, reverse=True)


async def test_filtro_por_fechas(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> None:
    await crear_usuario("jefa", rol=Rol.ADMINISTRADOR)
    await iniciar_sesion(client, "jefa")

    futuro = await client.get(URL, params={"desde": "2999-01-01T00:00:00Z"})
    pasado = await client.get(URL, params={"hasta": "2000-01-01T00:00:00Z"})

    assert futuro.json()["total"] == 0
    assert pasado.json()["total"] == 0


async def test_un_empleado_no_consulta_la_auditoria(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> None:
    await crear_usuario("lucia")
    await iniciar_sesion(client, "lucia")

    assert (await client.get(URL)).status_code == 403

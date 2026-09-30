"""Borradores de factura: guardar, editar, borrar y emitir (US4; FR-011, FR-019, FR-020; R-9).

Ajuste de cierre: borradores de oro de inversión sin IVA (FR-052, R-21).
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tiempo import hoy
from app.domain.tipos import Rol, TipoEvento
from app.models import Cliente, RegistroFacturacion, Usuario
from app.repositories import configuracion_facturacion
from tests.conftest import CrearUsuario, IniciarSesion, eventos
from tests.integration.facturacion_datos import (
    LINEAS_CAPTURA,
    LINGOTE,
    cabeceras,
    configurar_facturacion,
    crear_cliente,
)

URL = "/api/v1/borradores-factura"


@pytest.fixture
async def empleada(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> tuple[Usuario, str]:
    usuario = await crear_usuario("empleada.borradores")
    return usuario, await iniciar_sesion(client, "empleada.borradores")


@pytest.fixture
async def maria(db: AsyncSession, empleada: tuple[Usuario, str]) -> Cliente:
    await configurar_facturacion(db)
    return await crear_cliente(db, empleada[0].id)


@pytest.fixture
def csrf(empleada: tuple[Usuario, str]) -> dict[str, str]:
    return {"X-CSRF-Token": empleada[1]}


def cuerpo(
    cliente: Cliente | None = None,
    *,
    lineas: list[dict[str, str]] | None = None,
    fecha: date | None = None,
    version: int | None = None,
    oro_inversion: bool | None = None,
) -> dict[str, Any]:
    """Al crear, `oro_inversion` es opcional; al editar o emitir (con `version`), obligatoria."""
    datos: dict[str, Any] = {
        "fecha_expedicion": (fecha or hoy()).isoformat(),
        "cliente_id": str(cliente.id) if cliente else None,
        "lineas": LINEAS_CAPTURA if lineas is None else lineas,
    }
    if version is not None:
        datos["version"] = version
        datos["oro_inversion"] = bool(oro_inversion)
    elif oro_inversion is not None:
        datos["oro_inversion"] = oro_inversion
    return datos


async def _crear(client: AsyncClient, csrf: dict[str, str], datos: dict[str, Any]) -> Any:
    respuesta = await client.post(URL, json=datos, headers=csrf)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


async def _emitir(
    client: AsyncClient,
    csrf: str,
    borrador: dict[str, Any],
    datos: dict[str, Any],
    clave: uuid.UUID | None = None,
) -> Any:
    return await client.post(
        f"{URL}/{borrador['id']}/emision", json=datos, headers=cabeceras(csrf, clave)
    )


async def _registros(db: AsyncSession) -> int:
    return int(await db.scalar(select(func.count()).select_from(RegistroFacturacion)) or 0)


# ---------------------------------------------------------------------------------- CRUD


@pytest.mark.usefixtures("maria")
async def test_un_borrador_incompleto_se_guarda_sin_numero_ni_registro(
    client: AsyncClient, csrf: dict[str, str], db: AsyncSession
) -> None:
    borrador = await _crear(client, csrf, cuerpo(lineas=[]))

    assert borrador["version"] == 1
    assert borrador["cliente"] is None
    assert borrador["lineas"] == []
    assert borrador["tipo_iva_previsto"] == "21.00"
    assert borrador["totales_previstos"] == {
        "desglose": [{"tipo_iva": "21.00", "base": "0.00", "cuota": "0.00"}],
        "base_total": "0.00",
        "cuota_total": "0.00",
        "importe_total": "0.00",
    }
    assert "num_serie" not in borrador
    assert await _registros(db) == 0
    [evento] = await eventos(db, TipoEvento.BORRADOR_FACTURA_CREADO)
    assert evento.detalle == {"borrador_id": borrador["id"], "lineas": 0}


async def test_guarda_los_totales_previstos_con_el_iva_vigente(
    client: AsyncClient, csrf: dict[str, str], maria: Cliente, db: AsyncSession
) -> None:
    creado = await _crear(client, csrf, cuerpo(maria))

    leido = (await client.get(f"{URL}/{creado['id']}")).json()
    assert leido == creado
    assert [linea["importe"] for linea in leido["lineas"]] == ["1200.00", "90.00"]
    assert [linea["unidades"] for linea in leido["lineas"]] == ["1.00", "2.00"]
    assert leido["totales_previstos"]["base_total"] == "1290.00"
    assert leido["totales_previstos"]["cuota_total"] == "270.90"
    assert leido["totales_previstos"]["importe_total"] == "1560.90"
    assert leido["cliente"]["nombre"] == "María López García"
    assert leido["cliente"]["activo"] is True
    assert leido["creado_por"]["nombre"] == "Ana García"

    # Cambia el IVA: el guardado conserva el suyo hasta volver a guardar (aviso en la web).
    config = await configuracion_facturacion.get(db, for_update=True)
    config.iva_por_defecto = Decimal("10.00")
    await db.commit()
    assert (await client.get(f"{URL}/{creado['id']}")).json()["tipo_iva_previsto"] == "21.00"

    respuesta = await client.put(
        f"{URL}/{creado['id']}", json=cuerpo(maria, version=1), headers=csrf
    )
    assert respuesta.status_code == 200, respuesta.text
    guardado = respuesta.json()
    assert guardado["version"] == 2
    assert guardado["tipo_iva_previsto"] == "10.00"
    assert guardado["totales_previstos"]["cuota_total"] == "129.00"


async def test_editar_sustituye_las_lineas_y_detecta_versiones_desfasadas(
    client: AsyncClient, csrf: dict[str, str], maria: Cliente, db: AsyncSession
) -> None:
    creado = await _crear(client, csrf, cuerpo(maria))
    nuevas = [{"unidades": "3", "descripcion": "Cadena de plata", "precio_unitario": "25.50"}]

    respuesta = await client.put(
        f"{URL}/{creado['id']}", json=cuerpo(maria, lineas=nuevas, version=1), headers=csrf
    )

    assert respuesta.status_code == 200, respuesta.text
    editado = respuesta.json()
    assert editado["version"] == 2  # solo cambian las líneas y aun así sube la versión
    assert [linea["descripcion"] for linea in editado["lineas"]] == ["Cadena de plata"]
    assert editado["totales_previstos"]["base_total"] == "76.50"
    [evento] = await eventos(db, TipoEvento.BORRADOR_FACTURA_EDITADO)
    assert evento.detalle["borrador_id"] == creado["id"]
    assert set(evento.detalle["cambios"]) == {"lineas"}

    desfasado = await client.put(
        f"{URL}/{creado['id']}", json=cuerpo(maria, lineas=[], version=1), headers=csrf
    )
    assert desfasado.status_code == 409
    assert desfasado.json()["type"] == "/problemas/conflicto-version"
    assert desfasado.json()["detail"] == "El borrador ha cambiado desde que lo abriste."


async def test_guardar_sin_cambios_no_sube_la_version_ni_audita(
    client: AsyncClient, csrf: dict[str, str], maria: Cliente, db: AsyncSession
) -> None:
    creado = await _crear(client, csrf, cuerpo(maria))

    respuesta = await client.put(
        f"{URL}/{creado['id']}", json=cuerpo(maria, version=1), headers=csrf
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["version"] == 1
    assert await eventos(db, TipoEvento.BORRADOR_FACTURA_EDITADO) == []


async def test_borrar_no_consume_numero_ni_genera_registro(
    client: AsyncClient, csrf: dict[str, str], maria: Cliente, db: AsyncSession
) -> None:
    creado = await _crear(client, csrf, cuerpo(maria))
    antes = (await client.get("/api/v1/facturas/parametros")).json()["proximo_numero"]

    respuesta = await client.delete(f"{URL}/{creado['id']}", headers=csrf)

    assert respuesta.status_code == 204
    assert (await client.get(f"{URL}/{creado['id']}")).status_code == 404
    assert (await client.get("/api/v1/facturas/parametros")).json()["proximo_numero"] == antes
    assert await _registros(db) == 0
    [evento] = await eventos(db, TipoEvento.BORRADOR_FACTURA_ELIMINADO)
    assert evento.detalle["borrador_id"] == creado["id"]
    assert evento.cliente_id == maria.id
    assert len(evento.detalle["lineas"]) == 2


async def test_un_cliente_desactivado_no_se_elige_pero_se_conserva_si_ya_estaba(
    client: AsyncClient, csrf: dict[str, str], maria: Cliente, db: AsyncSession
) -> None:
    creado = await _crear(client, csrf, cuerpo(maria))
    maria.activo = False
    await db.commit()

    # Se puede seguir guardando con el cliente que ya tenía…
    otras = [{"unidades": "1", "descripcion": "Pulsera", "precio_unitario": "80"}]
    conservado = await client.put(
        f"{URL}/{creado['id']}", json=cuerpo(maria, lineas=otras, version=1), headers=csrf
    )
    assert conservado.status_code == 200, conservado.text
    assert conservado.json()["cliente"]["activo"] is False
    # …pero no elegirlo para uno nuevo.
    nuevo = await client.post(URL, json=cuerpo(maria), headers=csrf)
    assert nuevo.status_code == 422
    assert nuevo.json()["errores"][0]["campo"] == "cliente_id"


@pytest.mark.usefixtures("maria")
async def test_la_entrada_no_admite_totales_ni_cifras_json(
    client: AsyncClient, csrf: dict[str, str]
) -> None:
    con_totales = {**cuerpo(), "totales_previstos": {"importe_total": "1.00"}}
    assert (await client.post(URL, json=con_totales, headers=csrf)).status_code == 422
    con_float = {
        **cuerpo(),
        "lineas": [{"unidades": 1, "descripcion": "Anillo", "precio_unitario": 10.5}],
    }
    assert (await client.post(URL, json=con_float, headers=csrf)).status_code == 422
    inexistente = {**cuerpo(), "cliente_id": str(uuid.uuid4())}
    assert (await client.post(URL, json=inexistente, headers=csrf)).status_code == 422


async def test_sin_sesion_no_hay_borradores(client: AsyncClient) -> None:
    assert (await client.get(f"{URL}/{uuid.uuid4()}")).status_code == 401


# ------------------------------------------------ oro de inversión exento (FR-052, R-21)


async def test_un_borrador_de_oro_de_inversion_va_sin_cuota(
    client: AsyncClient, csrf: dict[str, str], maria: Cliente
) -> None:
    creado = await _crear(client, csrf, cuerpo(maria, lineas=LINGOTE, oro_inversion=True))

    assert creado["oro_inversion"] is True
    assert creado["mencion_exencion"] == (
        "Operación exenta de IVA (art. 140 bis.Uno.1.º de la Ley 37/1992)"
    )
    assert creado["totales_previstos"] == {
        "desglose": [{"tipo_iva": None, "base": "7450.00", "cuota": "0.00"}],
        "base_total": "7450.00",
        "cuota_total": "0.00",
        "importe_total": "7450.00",
    }
    sin_casilla = await _crear(client, csrf, cuerpo(maria))
    assert sin_casilla["oro_inversion"] is False
    assert sin_casilla["mencion_exencion"] is None


async def test_editar_la_casilla_se_audita_y_es_obligatoria(
    client: AsyncClient, csrf: dict[str, str], maria: Cliente, db: AsyncSession
) -> None:
    creado = await _crear(client, csrf, cuerpo(maria, lineas=LINGOTE))

    editado = await client.put(
        f"{URL}/{creado['id']}",
        json=cuerpo(maria, lineas=LINGOTE, version=1, oro_inversion=True),
        headers=csrf,
    )
    sin_casilla = await client.put(
        f"{URL}/{creado['id']}",
        json={k: v for k, v in cuerpo(maria, version=2).items() if k != "oro_inversion"},
        headers=csrf,
    )

    assert editado.status_code == 200, editado.text
    assert editado.json()["oro_inversion"] is True
    assert editado.json()["totales_previstos"]["cuota_total"] == "0.00"
    [evento] = await eventos(db, TipoEvento.BORRADOR_FACTURA_EDITADO)
    assert evento.detalle["cambios"]["oro_inversion"] == [False, True]
    assert sin_casilla.status_code == 422
    assert "oro_inversion" in {e["campo"] for e in sin_casilla.json()["errores"]}


async def test_emitir_un_borrador_de_oro_de_inversion(
    client: AsyncClient, empleada: tuple[Usuario, str], csrf: dict[str, str], maria: Cliente
) -> None:
    creado = await _crear(client, csrf, cuerpo(maria, lineas=LINGOTE, oro_inversion=True))

    respuesta = await _emitir(
        client,
        empleada[1],
        creado,
        cuerpo(maria, lineas=LINGOTE, version=1, oro_inversion=True),
    )

    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["oro_inversion"] is True
    assert respuesta.json()["totales"]["importe_total"] == "7450.00"


# ------------------------------------------------------------------------------- emisión


async def test_emitir_sustituye_el_borrador_por_la_factura(
    client: AsyncClient,
    empleada: tuple[Usuario, str],
    csrf: dict[str, str],
    maria: Cliente,
    db: AsyncSession,
) -> None:
    creado = await _crear(client, csrf, cuerpo(maria, lineas=[]))
    clave = uuid.uuid4()

    # Se emite con el contenido actual del modal, aunque no se haya guardado.
    respuesta = await _emitir(client, empleada[1], creado, cuerpo(maria, version=1), clave)

    assert respuesta.status_code == 201, respuesta.text
    factura = respuesta.json()
    assert factura["num_serie"] == f"FAC-{hoy().year}-0001"
    assert factura["totales"]["importe_total"] == "1560.90"
    assert len(factura["registros"]) == 1
    assert (await client.get(f"{URL}/{creado['id']}")).status_code == 404
    [evento] = await eventos(db, TipoEvento.FACTURA_EMITIDA)
    assert evento.detalle["borrador_id"] == creado["id"]

    repeticion = await _emitir(client, empleada[1], creado, cuerpo(maria, version=1), clave)
    assert repeticion.status_code == 200
    assert repeticion.json()["id"] == factura["id"]

    otra_clave = await _emitir(client, empleada[1], creado, cuerpo(maria, version=1))
    assert otra_clave.status_code == 404
    assert "ya no existe" in otra_clave.json()["detail"]
    assert await _registros(db) == 1


async def test_la_clave_de_otra_operacion_es_un_conflicto(
    client: AsyncClient, empleada: tuple[Usuario, str], csrf: dict[str, str], maria: Cliente
) -> None:
    clave = uuid.uuid4()
    emitida = await client.post(
        "/api/v1/facturas",
        json=cuerpo(maria),
        headers=cabeceras(empleada[1], clave),
    )
    assert emitida.status_code == 201
    creado = await _crear(client, csrf, cuerpo(maria))

    respuesta = await _emitir(client, empleada[1], creado, cuerpo(maria, version=1), clave)

    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == "/problemas/idempotencia-conflicto"


async def test_emitir_valida_como_cualquier_emision(
    client: AsyncClient,
    empleada: tuple[Usuario, str],
    csrf: dict[str, str],
    maria: Cliente,
    db: AsyncSession,
) -> None:
    creado = await _crear(client, csrf, cuerpo(maria))
    csrf_emp = empleada[1]

    sin_cliente = await _emitir(client, csrf_emp, creado, cuerpo(version=1))
    assert sin_cliente.status_code == 422
    assert sin_cliente.json()["errores"][0]["campo"] == "cliente_id"

    # FR-018: la AEAT no admite fechas anteriores al 28/10/2024 (error 1152).
    antigua = await _emitir(
        client, csrf_emp, creado, cuerpo(maria, fecha=date(2024, 10, 27), version=1)
    )
    assert antigua.status_code == 422
    assert antigua.json()["type"] == "/problemas/fecha-expedicion"
    futura = await _emitir(
        client, csrf_emp, creado, cuerpo(maria, fecha=hoy() + timedelta(days=1), version=1)
    )
    assert futura.status_code == 422
    assert futura.json()["type"] == "/problemas/fecha-expedicion"

    desfasada = await _emitir(client, csrf_emp, creado, cuerpo(maria, version=7))
    assert desfasada.status_code == 409
    assert desfasada.json()["type"] == "/problemas/conflicto-version"

    maria.activo = False
    await db.commit()
    desactivado = await _emitir(client, csrf_emp, creado, cuerpo(maria, version=1))
    assert desactivado.status_code == 422
    assert desactivado.json()["type"] == "/problemas/cliente-no-facturable"

    # Nada se ha emitido y el borrador sigue ahí.
    assert (await client.get(f"{URL}/{creado['id']}")).status_code == 200
    assert await _registros(db) == 0


async def test_un_cliente_con_borrador_no_se_puede_borrar(
    client: AsyncClient,
    csrf: dict[str, str],
    maria: Cliente,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    otro_cliente: Any,
) -> None:
    await _crear(client, csrf, cuerpo(maria))
    await crear_usuario("admin.borradores", rol=Rol.ADMINISTRADOR)
    async with otro_cliente() as admin:
        token = await iniciar_sesion(admin, "admin.borradores")
        respuesta = await admin.delete(
            f"/api/v1/clientes/{maria.id}", headers={"X-CSRF-Token": token}
        )

    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == "/problemas/cliente-con-documentos"

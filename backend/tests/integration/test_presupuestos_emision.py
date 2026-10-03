"""⚖️ Emisión de presupuestos: número, importes, copias y ninguna pieza fiscal (005; US1).

Tests obligatorios (constitución VII) de importes y redondeos del presupuesto (SC-004). Además:
FR-002 a FR-011, FR-014 y FR-028. Un presupuesto no genera registros ni consume números de
factura (FR-005).
"""

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tiempo import hoy
from app.domain.importes import LineaCalculo, compute_totals
from app.domain.tipos import Serie, TipoEvento
from app.models import Cliente, ContadorFactura, RegistroFacturacion, Usuario
from app.repositories import configuracion_facturacion
from tests.conftest import CrearUsuario, IniciarSesion, eventos
from tests.integration.facturacion_datos import (
    IBAN_DEMO,
    LINGOTE,
    URL_PRESUPUESTOS,
    cabeceras,
    configurar_facturacion,
    crear_cliente,
    cuerpo_presupuesto,
)


@pytest.fixture
async def empleada(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> tuple[Usuario, str]:
    usuario = await crear_usuario("empleada.emision.pre")
    return usuario, await iniciar_sesion(client, "empleada.emision.pre")


@pytest.fixture
async def maria(db: AsyncSession, empleada: tuple[Usuario, str]) -> Cliente:
    await configurar_facturacion(db, iban=IBAN_DEMO)
    return await crear_cliente(db, empleada[0].id)


@pytest.fixture
def csrf(empleada: tuple[Usuario, str]) -> str:
    return empleada[1]


async def _contador(db: AsyncSession, serie: Serie) -> int:
    valor = await db.scalar(
        select(ContadorFactura.ultimo_numero).where(
            ContadorFactura.serie == serie.value, ContadorFactura.anio == hoy().year
        )
    )
    return int(valor or 0)


async def test_emite_con_numero_pre_e_importes_del_servidor(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    respuesta = await client.post(
        URL_PRESUPUESTOS, json=cuerpo_presupuesto(maria.id), headers=cabeceras(csrf)
    )

    assert respuesta.status_code == 201, respuesta.text
    datos = respuesta.json()
    assert datos["num_serie"] == f"PRE-{hoy().year}-0001"
    assert datos["estado"] == "pendiente"
    # 1 × 1.200,00 + 2 × 45,00 = 1.290,00 + 21 % = 1.560,90 (como la factura, FR-007)
    assert datos["totales"]["base_total"] == "1290.00"
    assert datos["totales"]["cuota_total"] == "270.90"
    assert datos["totales"]["importe_total"] == "1560.90"
    assert [linea["tipo_iva"] for linea in datos["lineas"]] == ["21.00", "21.00"]
    segundo = await client.post(
        URL_PRESUPUESTOS, json=cuerpo_presupuesto(maria.id), headers=cabeceras(csrf)
    )
    assert segundo.json()["num_serie"] == f"PRE-{hoy().year}-0002"
    [evento, _] = await eventos(db, TipoEvento.PRESUPUESTO_EMITIDO)
    assert evento.detalle["num_serie"] == datos["num_serie"]


@pytest.mark.parametrize(
    ("lineas", "iva"),
    [
        ([{"unidades": "1", "descripcion": "Medio céntimo", "precio_unitario": "0.05"}], "10"),
        ([{"unidades": "1.50", "descripcion": "Gramos", "precio_unitario": "33.33"}], "21"),
        ([{"unidades": "999", "descripcion": "Grande", "precio_unitario": "99999.99"}], "21"),
    ],
)
async def test_importes_y_redondeo_iguales_que_compute_totals(
    client: AsyncClient,
    csrf: str,
    maria: Cliente,
    db: AsyncSession,
    lineas: list[dict[str, str]],
    iva: str,
) -> None:
    config = await configuracion_facturacion.get(db, for_update=True)
    config.iva_por_defecto = Decimal(iva)
    await db.flush()
    esperado = compute_totals(
        [
            LineaCalculo(Decimal(x["unidades"]), Decimal(x["precio_unitario"]), Decimal(iva))
            for x in lineas
        ],
        tipo_iva_por_defecto=Decimal(iva),
    )

    respuesta = await client.post(
        URL_PRESUPUESTOS, json=cuerpo_presupuesto(maria.id, lineas=lineas), headers=cabeceras(csrf)
    )

    assert respuesta.status_code == 201, respuesta.text
    totales = respuesta.json()["totales"]
    assert Decimal(totales["base_total"]) == esperado.base_total
    assert Decimal(totales["cuota_total"]) == esperado.cuota_total
    assert Decimal(totales["importe_total"]) == esperado.importe_total


async def test_oro_de_inversion_sin_iva_y_con_mencion(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    respuesta = await client.post(
        URL_PRESUPUESTOS,
        json=cuerpo_presupuesto(maria.id, lineas=LINGOTE, oro_inversion=True),
        headers=cabeceras(csrf),
    )

    assert respuesta.status_code == 201, respuesta.text
    datos = respuesta.json()
    assert datos["totales"]["cuota_total"] == "0.00"
    assert datos["totales"]["importe_total"] == "7450.00"
    assert datos["totales"]["desglose"] == [{"tipo_iva": None, "base": "7450.00", "cuota": "0.00"}]
    assert datos["lineas"][0]["tipo_iva"] is None
    assert "140 bis" in datos["mencion_exencion"]


async def test_un_total_enviado_por_la_web_se_rechaza(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    datos = {**cuerpo_presupuesto(maria.id), "importe_total": "1.00"}

    respuesta = await client.post(URL_PRESUPUESTOS, json=datos, headers=cabeceras(csrf))

    assert respuesta.status_code == 422


async def test_copia_el_emisor_y_el_destinatario(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    emitido = (
        await client.post(
            URL_PRESUPUESTOS, json=cuerpo_presupuesto(maria.id), headers=cabeceras(csrf)
        )
    ).json()
    maria.nombre = "Otro Nombre"
    config = await configuracion_facturacion.get(db, for_update=True)
    config.emisor_nombre = "Otra Joyería"
    await db.flush()

    consulta = (await client.get(f"{URL_PRESUPUESTOS}/{emitido['id']}")).json()

    assert consulta["cliente"]["nombre"] == "María López García"
    assert consulta["emisor"]["nombre"] == "Joyería Blanco, S.L."
    assert consulta["emisor"]["iban"] == IBAN_DEMO


async def test_sin_efectos_fiscales(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    await client.post(URL_PRESUPUESTOS, json=cuerpo_presupuesto(maria.id), headers=cabeceras(csrf))

    assert await db.scalar(select(func.count(RegistroFacturacion.id))) == 0
    assert await _contador(db, Serie.ORDINARIA) == 0
    assert await _contador(db, Serie.PRESUPUESTO) == 1


async def test_sin_datos_del_emisor_no_se_emite_pero_sin_modalidad_si(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    config = await configuracion_facturacion.get(db, for_update=True)
    config.modalidad = None
    await db.flush()
    sin_modalidad = await client.post(
        URL_PRESUPUESTOS, json=cuerpo_presupuesto(maria.id), headers=cabeceras(csrf)
    )
    assert sin_modalidad.status_code == 201, sin_modalidad.text

    config.emisor_nif = None
    await db.flush()
    sin_emisor = await client.post(
        URL_PRESUPUESTOS, json=cuerpo_presupuesto(maria.id), headers=cabeceras(csrf)
    )
    assert sin_emisor.status_code == 409
    assert sin_emisor.json()["type"] == "/problemas/emision-no-disponible"
    assert sin_emisor.json()["faltan"] == ["emisor.nif"]


async def test_cliente_inactivo_no_y_sin_domicilio_si(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession, empleada: tuple[Usuario, str]
) -> None:
    sin_domicilio = await crear_cliente(
        db, empleada[0].id, nombre="Sin Casa", numero="00000002W", con_domicilio=False
    )
    respuesta = await client.post(
        URL_PRESUPUESTOS, json=cuerpo_presupuesto(sin_domicilio.id), headers=cabeceras(csrf)
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["cliente"]["direccion"] is None

    maria.activo = False
    await db.flush()
    inactivo = await client.post(
        URL_PRESUPUESTOS, json=cuerpo_presupuesto(maria.id), headers=cabeceras(csrf)
    )
    assert inactivo.status_code == 422
    assert inactivo.json()["type"] == "/problemas/cliente-no-facturable"
    assert inactivo.json()["faltan"] == ["activo"]


@pytest.mark.parametrize(
    ("cambios", "campo"),
    [
        ({"fecha": "2024-10-27", "valido_hasta": "2024-12-01"}, "fecha"),
        ({"valido_hasta": "2024-10-28"}, "valido_hasta"),
    ],
)
async def test_fecha_y_validez_en_su_campo(
    client: AsyncClient, csrf: str, maria: Cliente, cambios: dict[str, str], campo: str
) -> None:
    respuesta = await client.post(
        URL_PRESUPUESTOS,
        json={**cuerpo_presupuesto(maria.id), **cambios},
        headers=cabeceras(csrf),
    )

    assert respuesta.status_code == 422, respuesta.text
    assert campo in [e["campo"] for e in respuesta.json()["errores"]]


async def test_idempotencia(client: AsyncClient, csrf: str, maria: Cliente) -> None:
    clave = uuid.uuid4()
    primera = await client.post(
        URL_PRESUPUESTOS, json=cuerpo_presupuesto(maria.id), headers=cabeceras(csrf, clave)
    )
    repetida = await client.post(
        URL_PRESUPUESTOS, json=cuerpo_presupuesto(maria.id), headers=cabeceras(csrf, clave)
    )

    assert primera.status_code == 201
    assert repetida.status_code == 200
    assert repetida.json()["id"] == primera.json()["id"]

    # La misma clave para emitir un borrador (otra operación y otro origen) es un conflicto.
    borrador = await client.post(
        "/api/v1/borradores-presupuesto",
        json=cuerpo_presupuesto(maria.id),
        headers={"X-CSRF-Token": csrf},
    )
    otra = await client.post(
        f"/api/v1/borradores-presupuesto/{borrador.json()['id']}/emision",
        json={**cuerpo_presupuesto(maria.id), "version": borrador.json()["version"]},
        headers=cabeceras(csrf, clave),
    )
    assert otra.status_code == 409
    assert otra.json()["type"] == "/problemas/idempotencia-conflicto"


async def test_sin_ajuste_de_la_serie_pre(
    client: AsyncClient,
    db: AsyncSession,
    maria: Cliente,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
) -> None:
    """FR-003: el ajuste al alza del contador solo mueve la serie FAC."""
    from app.domain.tipos import Rol

    await crear_usuario("admin.ajuste.pre", rol=Rol.ADMINISTRADOR)
    csrf_admin = await iniciar_sesion(client, "admin.ajuste.pre")
    await client.post(
        URL_PRESUPUESTOS, json=cuerpo_presupuesto(maria.id), headers=cabeceras(csrf_admin)
    )

    ajuste = await client.post(
        "/api/v1/configuracion/facturacion/contador",
        json={"proximo_numero": 50, "motivo": "Prueba", "simular": False},
        headers={"X-CSRF-Token": csrf_admin},
    )

    assert ajuste.status_code == 200, ajuste.text
    assert ajuste.json()["serie"] == "FAC"
    assert await _contador(db, Serie.PRESUPUESTO) == 1


async def test_consulta_de_un_presupuesto_inexistente(client: AsyncClient, csrf: str) -> None:
    respuesta = await client.get(f"{URL_PRESUPUESTOS}/{uuid.uuid4()}")

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "El presupuesto no existe."


async def test_parametros_del_modal(client: AsyncClient, csrf: str, maria: Cliente) -> None:
    datos = (await client.get(f"{URL_PRESUPUESTOS}/parametros")).json()

    assert datos["validez_dias"] == 30
    assert datos["emision_posible"] is True
    assert datos["proximo_numero"] == f"PRE-{hoy().year}-0001"
    assert datos["fecha_minima"] == "2024-10-28"

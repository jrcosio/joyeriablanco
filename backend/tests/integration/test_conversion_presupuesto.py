"""⚖️ Test obligatorio (constitución VII): conversión presupuesto → factura (005, US3).

FR-018 a FR-022, SC-003 a SC-005, research R-5 y R-6. La conversión crea un borrador de factura
vinculado. Al emitirlo con la operación de 002, en la misma transacción, la factura recibe su
número FAC y su registro encadenado, y el presupuesto queda «convertido» con un cierre inalterable.

Los flujos van por la API real, dentro de la transacción del test. Las pruebas de concurrencia
usan sesiones reales que confirman, como `test_numeracion_presupuestos.py`. Las carreras frente a
anular y modificar se prueban con esos servicios, en `test_presupuestos_cierres.py` (US4).
"""

import asyncio
import io
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient, Response
from pypdf import PdfReader
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.errors import PresupuestoNoModificable, restriccion
from app.core.http import Origen
from app.core.security import hash_password
from app.core.tiempo import hoy
from app.domain.exenciones import MENCION_EXENCION_ORO_INVERSION
from app.domain.tipos import Rol, Serie, TipoEvento
from app.models import (
    BorradorFactura,
    Cliente,
    ContadorFactura,
    Factura,
    Presupuesto,
    RegistroFacturacion,
    Usuario,
)
from app.models.cierre_presupuesto import CierrePresupuesto
from app.repositories import cierres_presupuesto as cierres
from app.services import borradores, contenido, conversion, integridad, presupuestos
from tests.conftest import CrearUsuario, IniciarSesion, eventos
from tests.integration.facturacion_datos import (
    LINGOTE,
    URL_PRESUPUESTOS,
    cabeceras,
    configurar_facturacion,
    crear_cliente,
    cuerpo_factura,
    emitir_presupuesto,
    limpiar_facturacion_confirmada,
)

ANIO = hoy().year
URL_BORRADORES = "/api/v1/borradores-factura"
URL_FACTURAS = "/api/v1/facturas"
ORIGEN = Origen(ip=None, agente=None)


@pytest.fixture
async def admin(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> tuple[Usuario, str]:
    usuario = await crear_usuario("admin.conversion", rol=Rol.ADMINISTRADOR)
    return usuario, await iniciar_sesion(client, "admin.conversion")


@pytest.fixture
def csrf(admin: tuple[Usuario, str]) -> str:
    return admin[1]


@pytest.fixture
async def maria(db: AsyncSession, admin: tuple[Usuario, str]) -> Cliente:
    await configurar_facturacion(db)
    return await crear_cliente(db, admin[0].id)


async def _convertir(client: AsyncClient, csrf: str, presupuesto: dict[str, Any]) -> Response:
    return await client.post(
        f"{URL_PRESUPUESTOS}/{presupuesto['id']}/conversion", headers={"X-CSRF-Token": csrf}
    )


async def _borrador(client: AsyncClient, csrf: str, presupuesto: dict[str, Any]) -> dict[str, Any]:
    respuesta = await _convertir(client, csrf, presupuesto)
    assert respuesta.status_code == 201, respuesta.text
    return dict(respuesta.json())


async def _emitir_borrador(
    client: AsyncClient,
    csrf: str,
    borrador: dict[str, Any],
    *,
    fecha: str | None = None,
    clave: uuid.UUID | None = None,
) -> Response:
    """Emite el borrador tal como lo devolvió la API, como hace el modal de 002."""
    cuerpo = {
        "fecha_expedicion": fecha or borrador["fecha_expedicion"],
        "cliente_id": borrador["cliente"]["id"] if borrador["cliente"] else None,
        "lineas": [
            {
                "unidades": linea["unidades"],
                "descripcion": linea["descripcion"],
                "precio_unitario": linea["precio_unitario"],
            }
            for linea in borrador["lineas"]
        ],
        "oro_inversion": borrador["oro_inversion"],
        "version": borrador["version"],
    }
    return await client.post(
        f"{URL_BORRADORES}/{borrador['id']}/emision", json=cuerpo, headers=cabeceras(csrf, clave)
    )


async def _factura_de(client: AsyncClient, csrf: str, borrador: dict[str, Any]) -> dict[str, Any]:
    respuesta = await _emitir_borrador(client, csrf, borrador)
    assert respuesta.status_code == 201, respuesta.text
    return dict(respuesta.json())


async def _consultar(client: AsyncClient, presupuesto: dict[str, Any]) -> dict[str, Any]:
    respuesta = await client.get(f"{URL_PRESUPUESTOS}/{presupuesto['id']}")
    assert respuesta.status_code == 200, respuesta.text
    return dict(respuesta.json())


async def _cuenta(db: AsyncSession, modelo: type[Any]) -> int:
    return int(await db.scalar(select(func.count()).select_from(modelo)) or 0)


async def _contador_fac(db: AsyncSession) -> int:
    resultado = await db.scalar(
        select(ContadorFactura.ultimo_numero).where(
            ContadorFactura.serie == Serie.ORDINARIA.value, ContadorFactura.anio == ANIO
        )
    )
    return int(resultado or 0)


def _anulacion(presupuesto: dict[str, Any], actor: Usuario) -> CierrePresupuesto:
    """El cierre que insertará «Anular» (US4), escrito aquí directamente."""
    return CierrePresupuesto(
        presupuesto_id=uuid.UUID(presupuesto["id"]),
        tipo="anulacion",
        motivo_texto="Rechazado por el cliente",
        creado_por_id=actor.id,
        clave_idempotencia=uuid.uuid4(),
        operacion_idempotencia="anular",
    )


async def _insertar(db: AsyncSession, fila: object) -> None:
    """Inserta en un punto de guardado, para que la sesión siga viva si la BD lo rechaza."""
    async with db.begin_nested():
        db.add(fila)
        await db.flush()


def _texto_pdf(pdf: bytes) -> str:
    return " ".join(" ".join(p.extract_text().split()) for p in PdfReader(io.BytesIO(pdf)).pages)


# --------------------------------------------------------------- crear el borrador vinculado


async def test_convertir_crea_un_borrador_precargado_sin_consumir_numeros(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)

    borrador = await _borrador(client, csrf, presupuesto)

    assert borrador["cliente"]["id"] == str(maria.id)
    assert borrador["fecha_expedicion"] == hoy().isoformat()
    assert borrador["oro_inversion"] is False
    assert borrador["tipo_iva_previsto"] == "21.00"
    assert [
        (Decimal(linea["unidades"]), linea["descripcion"], Decimal(linea["precio_unitario"]))
        for linea in borrador["lineas"]
    ] == [
        (Decimal(linea["unidades"]), linea["descripcion"], Decimal(linea["precio_unitario"]))
        for linea in presupuesto["lineas"]
    ]
    assert borrador["totales_previstos"]["importe_total"] == "1560.90"
    assert borrador["presupuesto_origen"] == {
        "id": presupuesto["id"],
        "num_serie": presupuesto["num_serie"],
        "fecha": presupuesto["fecha"],
    }
    # Sin números ni registros (R-5)
    assert await _cuenta(db, Factura) == 0
    assert await _cuenta(db, RegistroFacturacion) == 0
    assert await _contador_fac(db) == 0
    [evento] = await eventos(db, TipoEvento.BORRADOR_FACTURA_CREADO)
    assert evento.detalle is not None
    assert evento.detalle["presupuesto_id"] == presupuesto["id"]
    consultado = await _consultar(client, presupuesto)
    assert consultado["estado"] == "en_facturacion"
    assert consultado["borrador_factura"] == {"id": borrador["id"]}
    # El GET del borrador también lleva el origen
    leido = (await client.get(f"{URL_BORRADORES}/{borrador['id']}")).json()
    assert leido["presupuesto_origen"]["num_serie"] == presupuesto["num_serie"]


async def test_repetir_la_conversion_devuelve_el_mismo_borrador(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)
    primero = await _borrador(client, csrf, presupuesto)

    repeticion = await _convertir(client, csrf, presupuesto)

    assert repeticion.status_code == 200
    assert repeticion.json()["id"] == primero["id"]
    assert await _cuenta(db, BorradorFactura) == 1


async def test_un_caducado_se_convierte(client: AsyncClient, csrf: str, maria: Cliente) -> None:
    presupuesto = await emitir_presupuesto(
        client, csrf, maria.id, fecha=hoy() - timedelta(days=40), valido_hasta=hoy() - timedelta(1)
    )
    assert presupuesto["estado"] == "caducado"

    assert (await _convertir(client, csrf, presupuesto)).status_code == 201
    assert (await _consultar(client, presupuesto))["estado"] == "en_facturacion"


async def test_con_el_cliente_desactivado_se_crea_pero_no_se_emite(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)
    maria.activo = False
    await db.flush()

    borrador = await _borrador(client, csrf, presupuesto)
    emision = await _emitir_borrador(client, csrf, borrador)

    assert borrador["cliente"]["id"] == str(maria.id)
    assert borrador["cliente"]["activo"] is False
    assert emision.status_code == 422
    assert emision.json()["type"] == "/problemas/cliente-no-facturable"
    assert await _cuenta(db, Factura) == 0
    assert (await _consultar(client, presupuesto))["estado"] == "en_facturacion"


async def test_convertir_uno_cerrado_responde_409(
    client: AsyncClient, csrf: str, admin: tuple[Usuario, str], maria: Cliente, db: AsyncSession
) -> None:
    convertido = await emitir_presupuesto(client, csrf, maria.id)
    await _factura_de(client, csrf, await _borrador(client, csrf, convertido))
    anulado = await emitir_presupuesto(client, csrf, maria.id)
    sustituido = await emitir_presupuesto(client, csrf, maria.id)
    nuevo = await emitir_presupuesto(client, csrf, maria.id)
    # Los cierres de anular y sustituir llegan con US4: aquí se insertan como lo harán sus servicios
    db.add_all(
        [
            _anulacion(anulado, admin[0]),
            CierrePresupuesto(
                presupuesto_id=uuid.UUID(sustituido["id"]),
                tipo="sustitucion",
                motivo_texto="Cambio de talla",
                presupuesto_nuevo_id=uuid.UUID(nuevo["id"]),
                creado_por_id=admin[0].id,
            ),
        ]
    )
    await db.flush()

    for presupuesto, estado in (
        (convertido, "convertido"),
        (anulado, "anulado"),
        (sustituido, "sustituido"),
    ):
        respuesta = await _convertir(client, csrf, presupuesto)
        assert respuesta.status_code == 409, estado
        cuerpo = respuesta.json()
        assert cuerpo["type"] == "/problemas/presupuesto-no-modificable"
        assert cuerpo["estado"] == estado
        assert "borrador_factura_id" not in cuerpo
    assert await _cuenta(db, BorradorFactura) == 0


async def test_un_inexistente_responde_404(client: AsyncClient, csrf: str) -> None:
    respuesta = await _convertir(client, csrf, {"id": str(uuid.uuid4())})

    assert respuesta.status_code == 404


async def test_un_empleado_tambien_convierte(
    client: AsyncClient,
    csrf: str,
    maria: Cliente,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
) -> None:
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)
    await crear_usuario("empleado.conversion")
    csrf_empleado = await iniciar_sesion(client, "empleado.conversion")

    assert (await _convertir(client, csrf_empleado, presupuesto)).status_code == 201


# ------------------------------------------------------------------ emitir el borrador


async def test_emitir_el_borrador_convierte_el_presupuesto_en_la_misma_operacion(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)
    borrador = await _borrador(client, csrf, presupuesto)

    factura = await _factura_de(client, csrf, borrador)

    assert factura["num_serie"] == f"FAC-{ANIO}-0001"
    assert [r["tipo"] for r in factura["registros"]] == ["alta"]
    assert factura["presupuesto_origen"] == {
        "id": presupuesto["id"],
        "num_serie": presupuesto["num_serie"],
        "fecha": presupuesto["fecha"],
    }
    consultado = await _consultar(client, presupuesto)
    assert consultado["estado"] == "convertido"
    assert consultado["borrador_factura"] is None
    assert consultado["cierre"]["tipo"] == "conversion"
    assert consultado["cierre"]["factura"] == {
        "id": factura["id"],
        "num_serie": factura["num_serie"],
    }
    assert consultado["cierre"]["factura_vigente"] is None
    # El borrador desaparece; la factura lleva el origen también al consultarla
    assert (await client.get(f"{URL_BORRADORES}/{borrador['id']}")).status_code == 404
    leida = (await client.get(f"{URL_FACTURAS}/{factura['id']}")).json()
    assert leida["presupuesto_origen"]["id"] == presupuesto["id"]
    assert len(await eventos(db, TipoEvento.FACTURA_EMITIDA)) == 1
    [evento] = await eventos(db, TipoEvento.PRESUPUESTO_CONVERTIDO)
    assert evento.detalle == {
        "presupuesto_id": presupuesto["id"],
        "num_serie": presupuesto["num_serie"],
        "factura_id": factura["id"],
        "factura_num_serie": factura["num_serie"],
    }
    [cierre] = (await db.execute(select(CierrePresupuesto))).scalars().all()
    assert str(cierre.factura_id) == factura["id"]


async def test_repetir_la_emision_devuelve_la_misma_factura(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)
    borrador = await _borrador(client, csrf, presupuesto)
    clave = uuid.uuid4()
    primera = await _emitir_borrador(client, csrf, borrador, clave=clave)

    repeticion = await _emitir_borrador(client, csrf, borrador, clave=clave)

    assert primera.status_code == 201
    assert repeticion.status_code == 200
    assert repeticion.json()["id"] == primera.json()["id"]
    assert await _cuenta(db, Factura) == 1
    assert await _cuenta(db, CierrePresupuesto) == 1


async def test_el_pdf_del_convertido_lleva_la_factura_del_cierre(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)
    factura = await _factura_de(client, csrf, await _borrador(client, csrf, presupuesto))
    pdf = await client.get(f"{URL_PRESUPUESTOS}/{presupuesto['id']}/pdf")
    assert f"CONVERTIDO en {factura['num_serie']}" in _texto_pdf(pdf.content)

    # La factura se anula y se reemite: el PDF sigue mostrando aquella en la que se convirtió
    reemision = await client.post(
        f"{URL_FACTURAS}/{factura['id']}/modificacion",
        json={
            "motivo": "no_debio_emitirse",
            "causa": None,
            "motivo_texto": "Corrección de prueba",
            "cliente_id": str(maria.id),
            "lineas": [{"unidades": "1", "descripcion": "Otra pieza", "precio_unitario": "1100"}],
            "oro_inversion": False,
        },
        headers=cabeceras(csrf),
    )
    assert reemision.status_code == 201, reemision.text
    nueva = reemision.json()

    pdf = await client.get(f"{URL_PRESUPUESTOS}/{presupuesto['id']}/pdf")
    assert f"CONVERTIDO en {factura['num_serie']}" in _texto_pdf(pdf.content)
    cierre = (await _consultar(client, presupuesto))["cierre"]
    assert cierre["factura"]["num_serie"] == factura["num_serie"]
    assert cierre["factura_vigente"] == {"id": nueva["id"], "num_serie": nueva["num_serie"]}


async def test_fecha_anterior_a_la_del_presupuesto_responde_422_sin_numero(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    fecha = hoy() - timedelta(days=5)
    presupuesto = await emitir_presupuesto(client, csrf, maria.id, fecha=fecha)
    borrador = await _borrador(client, csrf, presupuesto)

    respuesta = await _emitir_borrador(
        client, csrf, borrador, fecha=(fecha - timedelta(days=1)).isoformat()
    )

    assert respuesta.status_code == 422
    cuerpo = respuesta.json()
    assert cuerpo["type"] == "/problemas/fecha-expedicion"
    assert presupuesto["num_serie"] in cuerpo["detail"]
    assert await _contador_fac(db) == 0
    assert (await _consultar(client, presupuesto))["estado"] == "en_facturacion"
    # La misma fecha del presupuesto sí vale
    mismo_dia = await _emitir_borrador(client, csrf, borrador, fecha=fecha.isoformat())
    assert mismo_dia.status_code == 201, mismo_dia.text


async def test_cliente_sin_domicilio_o_sin_modalidad_no_emite_ni_consume_numero(
    client: AsyncClient, csrf: str, admin: tuple[Usuario, str], db: AsyncSession
) -> None:
    await configurar_facturacion(db)
    sin_domicilio = await crear_cliente(db, admin[0].id, con_domicilio=False)
    presupuesto = await emitir_presupuesto(client, csrf, sin_domicilio.id)  # FR-011: se admite
    borrador = await _borrador(client, csrf, presupuesto)

    respuesta = await _emitir_borrador(client, csrf, borrador)

    assert respuesta.status_code == 422
    assert respuesta.json()["type"] == "/problemas/cliente-no-facturable"

    otro = await emitir_presupuesto(
        client, csrf, (await crear_cliente(db, admin[0].id, numero="00000001R")).id
    )
    borrador_otro = await _borrador(client, csrf, otro)
    await configurar_facturacion(db, modalidad=None)

    respuesta = await _emitir_borrador(client, csrf, borrador_otro)

    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == "/problemas/emision-no-disponible"
    assert await _cuenta(db, Factura) == 0
    assert await _contador_fac(db) == 0
    for p in (presupuesto, otro):
        assert (await _consultar(client, p))["estado"] == "en_facturacion"


async def test_eliminar_el_borrador_devuelve_el_presupuesto_a_pendiente(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)
    borrador = await _borrador(client, csrf, presupuesto)

    borrado = await client.delete(
        f"{URL_BORRADORES}/{borrador['id']}", headers={"X-CSRF-Token": csrf}
    )

    assert borrado.status_code == 204
    assert (await _consultar(client, presupuesto))["estado"] == "pendiente"
    [evento] = await eventos(db, TipoEvento.BORRADOR_FACTURA_ELIMINADO)
    assert evento.detalle is not None
    assert evento.detalle["presupuesto_id"] == presupuesto["id"]
    otra_vez = await _convertir(client, csrf, presupuesto)
    assert otra_vez.status_code == 201
    assert otra_vez.json()["id"] != borrador["id"]


# ------------------------------------------------------------------------ importes ⚖️


async def test_con_el_mismo_iva_la_factura_coincide_al_centimo(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)

    factura = await _factura_de(client, csrf, await _borrador(client, csrf, presupuesto))

    assert factura["totales"] == presupuesto["totales"]
    assert [(linea["tipo_iva"], linea["importe"]) for linea in factura["lineas"]] == [
        (linea["tipo_iva"], linea["importe"]) for linea in presupuesto["lineas"]
    ]


async def test_con_el_iva_cambiado_la_misma_base_y_la_cuota_recalculada(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)
    await configurar_facturacion(db, iva="10")

    borrador = await _borrador(client, csrf, presupuesto)
    factura = await _factura_de(client, csrf, borrador)

    assert borrador["tipo_iva_previsto"] == "10.00"
    assert factura["totales"]["base_total"] == presupuesto["totales"]["base_total"] == "1290.00"
    assert factura["totales"]["cuota_total"] == "129.00"
    assert factura["totales"]["importe_total"] == "1419.00"


async def test_oro_de_inversion_da_una_factura_exenta(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    presupuesto = await emitir_presupuesto(
        client, csrf, maria.id, lineas=LINGOTE, oro_inversion=True
    )

    borrador = await _borrador(client, csrf, presupuesto)
    factura = await _factura_de(client, csrf, borrador)

    assert borrador["oro_inversion"] is True
    assert factura["oro_inversion"] is True
    assert factura["mencion_exencion"] == MENCION_EXENCION_ORO_INVERSION
    assert factura["totales"]["cuota_total"] == "0.00"
    assert factura["totales"]["importe_total"] == presupuesto["totales"]["importe_total"]


# ------------------------------------------------------------------- encadenamiento ⚖️


async def test_las_conversiones_no_alteran_la_cadena_de_huellas(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    directa = (
        await client.post(URL_FACTURAS, json=cuerpo_factura(maria.id), headers=cabeceras(csrf))
    ).json()
    convertida = await _factura_de(
        client,
        csrf,
        await _borrador(client, csrf, await emitir_presupuesto(client, csrf, maria.id)),
    )
    anulacion = await client.post(
        f"{URL_FACTURAS}/{directa['id']}/anulacion",
        json={"declaracion_no_debio_emitirse": True, "motivo_texto": "Duplicada"},
        headers=cabeceras(csrf),
    )
    assert anulacion.status_code == 200, anulacion.text
    rectificativa = await client.post(
        f"{URL_FACTURAS}/{convertida['id']}/modificacion",
        json={
            "motivo": "factura_entregada",
            "causa": "error_datos",
            "motivo_texto": "Talla equivocada",
            "cliente_id": str(maria.id),
            "lineas": [{"unidades": "1", "descripcion": "Otra talla", "precio_unitario": "1000"}],
            "oro_inversion": False,
        },
        headers=cabeceras(csrf),
    )
    assert rectificativa.status_code == 201, rectificativa.text
    await _factura_de(
        client,
        csrf,
        await _borrador(client, csrf, await emitir_presupuesto(client, csrf, maria.id)),
    )

    resultado = await integridad.verify_chain(db)

    assert resultado.integra
    assert resultado.registros == await _cuenta(db, RegistroFacturacion) == 5
    assert await _cuenta(db, CierrePresupuesto) == 2


# ----------------------------------------------------------------- barreras de la BD (R-6)


async def test_el_trigger_impide_cerrar_un_presupuesto_en_facturacion(
    client: AsyncClient, csrf: str, admin: tuple[Usuario, str], maria: Cliente, db: AsyncSession
) -> None:
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)
    borrador = await _borrador(client, csrf, presupuesto)

    with pytest.raises(IntegrityError) as error:
        await _insertar(db, _anulacion(presupuesto, admin[0]))

    assert restriccion(error.value) == "tg_cierres_presupuesto_en_facturacion"
    # Traducido al 409, con el estado y el borrador, y la sesión sigue utilizable
    with pytest.raises(PresupuestoNoModificable) as no_modificable:
        await presupuestos.guard_presupuesto(
            db,
            uuid.UUID(presupuesto["id"]),
            lambda: cierres.insert(db, _anulacion(presupuesto, admin[0])),
        )
    cuerpo = no_modificable.value.body()
    assert cuerpo["type"] == "/problemas/presupuesto-no-modificable"
    assert cuerpo["estado"] == "en_facturacion"
    assert cuerpo["borrador_factura_id"] == borrador["id"]
    assert "tg_" not in str(cuerpo)
    assert (await _consultar(client, presupuesto))["estado"] == "en_facturacion"


async def test_el_trigger_impide_vincular_un_borrador_a_un_cerrado_y_solo_hay_uno(
    client: AsyncClient, csrf: str, admin: tuple[Usuario, str], maria: Cliente, db: AsyncSession
) -> None:
    cerrado = await emitir_presupuesto(client, csrf, maria.id)
    await _insertar(db, _anulacion(cerrado, admin[0]))
    vinculado = await emitir_presupuesto(client, csrf, maria.id)
    await _borrador(client, csrf, vinculado)

    def nuevo(presupuesto: dict[str, Any]) -> BorradorFactura:
        return borradores.build_borrador(
            borradores.DatosBorrador(
                fecha_expedicion=hoy(),
                cliente_id=maria.id,
                lineas=(contenido.DatosLinea(Decimal(1), "Anillo", Decimal(100)),),
            ),
            actor=admin[0],
            tipo_iva=Decimal(21),
            presupuesto_id=uuid.UUID(presupuesto["id"]),
        )

    for presupuesto, nombre in (
        (cerrado, "tg_borradores_factura_presupuesto_cerrado"),
        (vinculado, "uq_borradores_factura_presupuesto_id"),
    ):
        with pytest.raises(IntegrityError) as error:
            await _insertar(db, nuevo(presupuesto))
        assert restriccion(error.value) == nombre


async def test_emitir_el_borrador_de_un_presupuesto_ya_cerrado_responde_409_sin_numero(
    client: AsyncClient, csrf: str, admin: tuple[Usuario, str], maria: Cliente, db: AsyncSession
) -> None:
    otra = (
        await client.post(URL_FACTURAS, json=cuerpo_factura(maria.id), headers=cabeceras(csrf))
    ).json()
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)
    borrador = await _borrador(client, csrf, presupuesto)
    # Cierre «por fuera» (el trigger admite una conversión con el borrador vivo)
    db.add(
        CierrePresupuesto(
            presupuesto_id=uuid.UUID(presupuesto["id"]),
            tipo="conversion",
            factura_id=uuid.UUID(otra["id"]),
            creado_por_id=admin[0].id,
        )
    )
    await db.flush()

    respuesta = await _emitir_borrador(client, csrf, borrador)

    assert respuesta.status_code == 409
    cuerpo = respuesta.json()
    assert cuerpo["type"] == "/problemas/presupuesto-no-modificable"
    assert cuerpo["estado"] == "convertido"
    assert await _cuenta(db, Factura) == 1  # solo la otra: la emisión se deshizo entera
    assert await _contador_fac(db) == 1
    assert await _cuenta(db, RegistroFacturacion) == 1


# ------------------------------------------------------- concurrencia (sesiones que confirman)


@dataclass(frozen=True, slots=True)
class Escenario:
    usuario_id: uuid.UUID
    cliente_id: uuid.UUID
    presupuesto_id: uuid.UUID


@pytest.fixture
async def escenario(engine_app: AsyncEngine, engine_owner: AsyncEngine) -> AsyncIterator[Escenario]:
    async with AsyncSession(engine_app, expire_on_commit=False) as sesion:
        assert (await sesion.execute(select(func.count(Presupuesto.id)))).scalar() == 0
        usuario = Usuario(
            nombre_usuario=f"conc.conv.{uuid.uuid4().hex[:6]}",
            nombre="Concurrencia",
            rol=Rol.ADMINISTRADOR.value,
            hash_contrasena=hash_password("x" * 12),
            contrasena_temporal=False,
        )
        sesion.add(usuario)
        await sesion.flush()
        await configurar_facturacion(sesion)
        cliente = await crear_cliente(sesion, usuario.id, numero="00000001R")
        presupuesto, _ = await presupuestos.emit_presupuesto(
            sesion,
            presupuestos.DatosPresupuesto(
                fecha=hoy(),
                valido_hasta=hoy() + timedelta(days=30),
                cliente_id=cliente.id,
                lineas=(contenido.DatosLinea(Decimal(1), "Anillo", Decimal("100.00")),),
            ),
            actor=usuario,
            origen=ORIGEN,
            clave=uuid.uuid4(),
        )
        await sesion.commit()
    try:
        yield Escenario(usuario.id, cliente.id, presupuesto.id)
    finally:
        await limpiar_facturacion_confirmada(
            engine_owner, clientes=[cliente.id], usuarios=[usuario.id]
        )


async def _convertir_en_sesion(
    engine_app: AsyncEngine, escenario: Escenario
) -> tuple[uuid.UUID, bool]:
    async with AsyncSession(engine_app, expire_on_commit=False) as sesion:
        actor = await sesion.get(Usuario, escenario.usuario_id)
        assert actor is not None
        borrador, creado = await conversion.create_borrador_conversion(
            sesion, escenario.presupuesto_id, actor=actor, origen=ORIGEN
        )
        await sesion.commit()
        return borrador.id, creado


async def _emitir_en_sesion(
    engine_app: AsyncEngine, escenario: Escenario, borrador_id: uuid.UUID, clave: uuid.UUID
) -> tuple[uuid.UUID, bool]:
    async with AsyncSession(engine_app, expire_on_commit=False) as sesion:
        actor = await sesion.get(Usuario, escenario.usuario_id)
        assert actor is not None
        factura, creada = await borradores.emit_borrador(
            sesion,
            borrador_id,
            borradores.DatosBorrador(
                fecha_expedicion=hoy(),
                cliente_id=escenario.cliente_id,
                lineas=(contenido.DatosLinea(Decimal(1), "Anillo", Decimal("100.00")),),
            ),
            version=1,
            actor=actor,
            origen=ORIGEN,
            clave=clave,
        )
        await sesion.commit()
        return factura.id, creada


async def _recuentos(engine_app: AsyncEngine) -> tuple[int, int, int, int, int]:
    async with AsyncSession(engine_app) as sesion:
        return (
            await _cuenta(sesion, BorradorFactura),
            await _cuenta(sesion, Factura),
            await _cuenta(sesion, RegistroFacturacion),
            await _cuenta(sesion, CierrePresupuesto),
            await _contador_fac(sesion),
        )


async def test_20_conversiones_simultaneas_dan_un_solo_borrador(
    engine_app: AsyncEngine, escenario: Escenario
) -> None:
    resultados = await asyncio.gather(
        *(_convertir_en_sesion(engine_app, escenario) for _ in range(20))
    )

    assert len({borrador_id for borrador_id, _ in resultados}) == 1
    assert sum(creado for _, creado in resultados) == 1
    assert await _recuentos(engine_app) == (1, 0, 0, 0, 0)


@pytest.mark.parametrize("misma_clave", [True, False])
async def test_20_emisiones_simultaneas_del_borrador_dan_una_sola_factura(
    engine_app: AsyncEngine, escenario: Escenario, misma_clave: bool
) -> None:
    borrador_id, _ = await _convertir_en_sesion(engine_app, escenario)
    clave = uuid.uuid4()

    resultados = await asyncio.gather(
        *(
            _emitir_en_sesion(
                engine_app, escenario, borrador_id, clave if misma_clave else uuid.uuid4()
            )
            for _ in range(20)
        ),
        return_exceptions=True,
    )

    facturas = [r for r in resultados if not isinstance(r, BaseException)]
    assert sum(creada for _, creada in facturas) == 1
    assert len({factura_id for factura_id, _ in facturas}) == 1
    if misma_clave:
        assert len(facturas) == 20  # las repeticiones devuelven la misma factura
    else:
        # Las demás llegan con el borrador ya emitido: «ya no existe» (404), sin consumir número
        assert all(
            getattr(r, "status", None) == 404 for r in resultados if isinstance(r, BaseException)
        )
    # Un borrador menos; una factura, un registro y un cierre más; el contador FAC +1
    assert await _recuentos(engine_app) == (0, 1, 1, 1, 1)

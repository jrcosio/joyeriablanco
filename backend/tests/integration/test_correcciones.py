"""Correcciones trazables de facturas emitidas (US5; FR-023 a FR-027, FR-048; R-4, R-8, R-9, R-18).

Anular, anular y reemitir, rectificar por sustitución (R1/R4, con devoluciones) y anular una
rectificativa, que devuelve la original a vigente. Nunca se toca el original: todo son registros
y correcciones nuevas, encadenados y con historial.
"""

import asyncio
import itertools
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.errors import FacturaNoModificable
from app.core.http import Origen
from app.core.security import hash_password
from app.core.tiempo import hoy
from app.domain.tipos import (
    CausaRectificacion,
    MotivoModificacion,
    OperacionIdempotente,
    Rol,
    TipoEvento,
)
from app.models import Cliente, Factura, RegistroFacturacion, Usuario
from app.repositories import configuracion_facturacion, registros
from app.services import cadena, emision
from tests.conftest import CrearUsuario, IniciarSesion, eventos
from tests.integration.facturacion_datos import (
    LINEAS_CAPTURA,
    LINGOTE,
    cabeceras,
    configurar_facturacion,
    crear_cliente,
    cuerpo_factura,
    limpiar_facturacion_confirmada,
)
from tests.integration.facturacion_sql import PRIVILEGIO_INSUFICIENTE

URL = "/api/v1/facturas"
ANIO = hoy().year
OTRAS_LINEAS = [
    {"unidades": "1", "descripcion": "Anillo de oro blanco (talla 15)", "precio_unitario": "1100"}
]


@pytest.fixture
async def admin(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> tuple[Usuario, str]:
    usuario = await crear_usuario("admin.correcciones", rol=Rol.ADMINISTRADOR)
    return usuario, await iniciar_sesion(client, "admin.correcciones")


@pytest.fixture
def csrf(admin: tuple[Usuario, str]) -> str:
    return admin[1]


@pytest.fixture
async def maria(db: AsyncSession, admin: tuple[Usuario, str]) -> Cliente:
    await configurar_facturacion(db)
    return await crear_cliente(db, admin[0].id)


async def _emitir(
    client: AsyncClient,
    csrf: str,
    cliente: Cliente,
    *,
    fecha: date | None = None,
    lineas: list[dict[str, str]] | None = None,
    oro_inversion: bool | None = None,
) -> dict[str, Any]:
    respuesta = await client.post(
        URL,
        json=cuerpo_factura(cliente.id, fecha=fecha, lineas=lineas, oro_inversion=oro_inversion),
        headers=cabeceras(csrf),
    )
    assert respuesta.status_code == 201, respuesta.text
    return dict(respuesta.json())


async def _anular(
    client: AsyncClient,
    csrf: str,
    factura: dict[str, Any],
    *,
    clave: uuid.UUID | None = None,
    declaracion: object = True,
    motivo: str = "Factura duplicada por error",
) -> Any:
    return await client.post(
        f"{URL}/{factura['id']}/anulacion",
        json={"declaracion_no_debio_emitirse": declaracion, "motivo_texto": motivo},
        headers=cabeceras(csrf, clave),
    )


async def _modificar(
    client: AsyncClient,
    csrf: str,
    factura: dict[str, Any],
    cliente: Cliente,
    *,
    motivo: str,
    causa: str | None = None,
    lineas: list[dict[str, str]] | None = None,
    clave: uuid.UUID | None = None,
    fecha: date | None = None,
    oro_inversion: bool = False,
) -> Any:
    cuerpo: dict[str, Any] = {
        "motivo": motivo,
        "causa": causa,
        "motivo_texto": "El cliente pidió otra talla",
        "cliente_id": str(cliente.id),
        "lineas": LINEAS_CAPTURA if lineas is None else lineas,
        "oro_inversion": oro_inversion,  # obligatoria al modificar (R-21)
    }
    if fecha is not None:
        cuerpo["fecha_expedicion"] = fecha.isoformat()
    return await client.post(
        f"{URL}/{factura['id']}/modificacion", json=cuerpo, headers=cabeceras(csrf, clave)
    )


async def _detalle(client: AsyncClient, factura: dict[str, Any]) -> dict[str, Any]:
    return dict((await client.get(f"{URL}/{factura['id']}")).json())


def _fecha_anterior() -> date:
    """Un día anterior a hoy del mismo año (o hoy, el 1 de enero)."""
    ayer = hoy() - timedelta(days=1)
    return ayer if ayer.year == ANIO else hoy()


async def _cadena(db: AsyncSession) -> list[RegistroFacturacion]:
    cola = await registros.list_in_order(db)
    for anterior, actual in itertools.pairwise(cola):
        assert actual.huella_anterior == anterior.huella
        assert cadena.recompute_huella(actual) == actual.huella
    return cola


# ---------------------------------------------------------------------------------- anular


async def test_anular_genera_el_registro_encadenado_y_el_numero_no_se_reutiliza(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    factura = await _emitir(client, csrf, maria)

    respuesta = await _anular(client, csrf, factura)

    assert respuesta.status_code == 200, respuesta.text
    anulada = respuesta.json()
    assert anulada["estado"] == "anulada"
    [correccion] = anulada["correcciones"]
    assert correccion["tipo"] == "anulacion"
    assert correccion["motivo"] == "no_debio_emitirse"
    assert correccion["motivo_texto"] == "Factura duplicada por error"
    assert correccion["factura_nueva"] is None
    assert correccion["en_vigor"] is True
    assert [r["tipo"] for r in anulada["registros"]] == ["alta", "anulacion"]
    cola = await _cadena(db)
    assert [r.tipo for r in cola] == ["alta", "anulacion"]
    assert cola[1].contenido["IDFactura"]["NumSerieFacturaAnulada"] == factura["num_serie"]
    [evento] = await eventos(db, TipoEvento.FACTURA_ANULADA)
    assert evento.detalle["num_serie"] == factura["num_serie"]
    assert "reactivada" not in evento.detalle

    siguiente = await _emitir(client, csrf, maria)
    assert siguiente["num_serie"] == f"FAC-{ANIO}-0002"


@pytest.mark.usefixtures("maria")
@pytest.mark.parametrize(
    "cuerpo",
    [
        {"declaracion_no_debio_emitirse": False, "motivo_texto": "Duplicada"},
        {"motivo_texto": "Duplicada"},
        {"declaracion_no_debio_emitirse": True, "motivo_texto": "  "},
        {"declaracion_no_debio_emitirse": True},
    ],
)
async def test_anular_exige_la_declaracion_y_el_motivo(
    client: AsyncClient, csrf: str, maria: Cliente, cuerpo: dict[str, Any]
) -> None:
    factura = await _emitir(client, csrf, maria)

    respuesta = await client.post(
        f"{URL}/{factura['id']}/anulacion", json=cuerpo, headers=cabeceras(csrf)
    )

    assert respuesta.status_code == 422
    assert (await _detalle(client, factura))["estado"] == "vigente"


async def test_anular_es_idempotente_por_clave(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    factura = await _emitir(client, csrf, maria)
    clave = uuid.uuid4()

    primera = await _anular(client, csrf, factura, clave=clave)
    repeticion = await _anular(client, csrf, factura, clave=clave)
    otra_clave = await _anular(client, csrf, factura)

    assert primera.status_code == repeticion.status_code == 200
    assert repeticion.json()["correcciones"] == primera.json()["correcciones"]
    assert otra_clave.status_code == 409
    assert otra_clave.json()["type"] == "/problemas/factura-no-modificable"
    assert [r.tipo for r in await _cadena(db)] == ["alta", "anulacion"]


async def test_un_empleado_no_puede_anular_ni_modificar(
    client: AsyncClient,
    csrf: str,
    maria: Cliente,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    otro_cliente: Any,
) -> None:
    factura = await _emitir(client, csrf, maria)
    await crear_usuario("empleado.correcciones")
    async with otro_cliente() as empleado:
        token = await iniciar_sesion(empleado, "empleado.correcciones")
        anular = await _anular(empleado, token, factura)
        modificar = await _modificar(empleado, token, factura, maria, motivo="no_debio_emitirse")

    assert anular.status_code == modificar.status_code == 403
    assert (await _detalle(client, factura))["estado"] == "vigente"


# ------------------------------------------------------------------ modificar: reemisión


async def test_no_debio_emitirse_anula_y_reemite_con_el_siguiente_numero(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    original = await _emitir(client, csrf, maria, fecha=_fecha_anterior())

    # Sin cambios se admite: es como se corrige un número erróneo (FR-010).
    respuesta = await _modificar(client, csrf, original, maria, motivo="no_debio_emitirse")

    assert respuesta.status_code == 201, respuesta.text
    nueva = respuesta.json()
    assert nueva["num_serie"] == f"FAC-{ANIO}-0002"
    assert nueva["tipo_factura"] == "F1"
    assert nueva["fecha_expedicion"] == hoy().isoformat()
    assert nueva["fecha_operacion"] == original["fecha_expedicion"]
    assert nueva["sustituye_a"] == {"id": original["id"], "num_serie": original["num_serie"]}
    antigua = await _detalle(client, original)
    assert antigua["estado"] == "anulada"
    assert antigua["vigente_actual"]["num_serie"] == nueva["num_serie"]
    [correccion] = antigua["correcciones"]
    assert correccion["tipo"] == "anulacion_y_reemision"
    assert correccion["factura_nueva"]["num_serie"] == nueva["num_serie"]

    cola = await _cadena(db)
    assert [r.tipo for r in cola] == ["alta", "anulacion", "alta"]
    assert cola[2].contenido["FechaOperacion"] == "-".join(
        reversed(original["fecha_expedicion"].split("-"))
    )
    [anulacion] = await eventos(db, TipoEvento.FACTURA_ANULADA)
    assert anulacion.detalle["sustituida_por"] == nueva["num_serie"]
    emitidas = await eventos(db, TipoEvento.FACTURA_EMITIDA)
    assert emitidas[-1].detalle["sustituye_a"] == original["num_serie"]


async def test_la_correccion_admite_una_fecha_anterior_pero_no_a_la_de_la_operacion(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    """FR-018: la fecha de la corrección es editable; F-3 §3.1.3.1 (error 1146) impide que sea
    anterior a la fecha de la operación, que se hereda de la original."""
    dia = hoy() - timedelta(days=10)
    original = await _emitir(client, csrf, maria, fecha=dia)

    antes_de_la_operacion = await _modificar(
        client,
        csrf,
        original,
        maria,
        motivo="no_debio_emitirse",
        fecha=dia - timedelta(days=1),
    )
    assert antes_de_la_operacion.status_code == 422
    assert antes_de_la_operacion.json()["type"] == "/problemas/fecha-expedicion"
    futura = await _modificar(
        client, csrf, original, maria, motivo="no_debio_emitirse", fecha=hoy() + timedelta(days=1)
    )
    assert futura.status_code == 422

    elegida = dia + timedelta(days=3)
    respuesta = await _modificar(
        client,
        csrf,
        original,
        maria,
        motivo="factura_entregada",
        causa="error_datos",
        lineas=OTRAS_LINEAS,
        fecha=elegida,
    )

    assert respuesta.status_code == 201, respuesta.text
    rec = respuesta.json()
    assert rec["fecha_expedicion"] == elegida.isoformat()
    assert rec["fecha_operacion"] == dia.isoformat()
    assert rec["num_serie"] == f"REC-{elegida.year}-0001"
    assert (await _cadena(db))[-1].contenido["IDFactura"]["FechaExpedicionFactura"] == (
        elegida.strftime("%d-%m-%Y")
    )


async def test_la_reemision_necesita_lineas(client: AsyncClient, csrf: str, maria: Cliente) -> None:
    original = await _emitir(client, csrf, maria)

    respuesta = await _modificar(
        client, csrf, original, maria, motivo="no_debio_emitirse", lineas=[]
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["errores"][0]["campo"] == "lineas"


# ---------------------------------------------------------------- modificar: rectificativa


async def test_factura_entregada_con_error_de_datos_emite_una_rec_r4(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    original = await _emitir(client, csrf, maria, fecha=_fecha_anterior())

    respuesta = await _modificar(
        client,
        csrf,
        original,
        maria,
        motivo="factura_entregada",
        causa="error_datos",
        lineas=OTRAS_LINEAS,
    )

    assert respuesta.status_code == 201, respuesta.text
    rec = respuesta.json()
    assert rec["num_serie"] == f"REC-{ANIO}-0001"
    assert (rec["tipo_factura"], rec["tipo_rectificativa"]) == ("R4", "S")
    assert rec["rectifica_a"] == {
        "factura": {"id": original["id"], "num_serie": original["num_serie"]},
        "base_rectificada": "1290.00",
        "cuota_rectificada": "270.90",
        "causa": "error_datos",
    }
    assert rec["totales"]["importe_total"] == "1331.00"
    assert rec["fecha_expedicion"] == hoy().isoformat()
    assert rec["fecha_operacion"] == original["fecha_expedicion"]
    antigua = await _detalle(client, original)
    assert antigua["estado"] == "rectificada"
    assert antigua["vigente_actual"]["num_serie"] == rec["num_serie"]
    assert antigua["correcciones"][0]["tipo"] == "rectificacion_sustitucion"
    assert antigua["correcciones"][0]["en_vigor"] is True

    alta = (await _cadena(db))[-1]
    assert alta.contenido["TipoFactura"] == "R4"
    assert alta.contenido["TipoRectificativa"] == "S"
    assert alta.contenido["ImporteRectificacion"] == {
        "BaseRectificada": "1290.00",
        "CuotaRectificada": "270.90",
    }
    [rectificada] = alta.contenido["FacturasRectificadas"]["IDFacturaRectificada"]
    assert rectificada["NumSerieFactura"] == original["num_serie"]
    assert "FechaOperacion" in alta.contenido
    [evento] = await eventos(db, TipoEvento.FACTURA_RECTIFICADA)
    assert evento.detalle["causa"] == "error_datos"
    assert evento.detalle["rectificativa"] == rec["num_serie"]
    assert (await eventos(db, TipoEvento.FACTURA_EMITIDA))[-1].detalle["rectifica_a"] == original[
        "num_serie"
    ]


async def test_una_devolucion_total_es_una_r1_sin_lineas_y_total_cero(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    original = await _emitir(client, csrf, maria)

    respuesta = await _modificar(
        client,
        csrf,
        original,
        maria,
        motivo="factura_entregada",
        causa="devolucion_o_precio",
        lineas=[],
    )

    assert respuesta.status_code == 201, respuesta.text
    rec = respuesta.json()
    assert rec["tipo_factura"] == "R1"
    assert rec["lineas"] == []
    assert rec["totales"] == {
        "desglose": [{"tipo_iva": "21.00", "base": "0.00", "cuota": "0.00"}],
        "base_total": "0.00",
        "cuota_total": "0.00",
        "importe_total": "0.00",
    }
    assert rec["rectifica_a"]["base_rectificada"] == "1290.00"


async def test_una_rectificativa_identica_se_rechaza_salvo_con_el_iva_corregido(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    original = await _emitir(client, csrf, maria)

    identica = await _modificar(
        client, csrf, original, maria, motivo="factura_entregada", causa="error_datos"
    )
    assert identica.status_code == 422
    assert identica.json()["type"] == "/problemas/sin-cambios"

    # R1 «IVA mal aplicado»: mismas líneas, pero la configuración ya tiene el tipo correcto.
    config = await configuracion_facturacion.get(db, for_update=True)
    config.iva_por_defecto = Decimal("10.00")
    await db.commit()
    corregida = await _modificar(
        client, csrf, original, maria, motivo="factura_entregada", causa="devolucion_o_precio"
    )
    assert corregida.status_code == 201, corregida.text
    assert corregida.json()["totales"]["cuota_total"] == "129.00"


async def test_si_cambian_los_datos_del_cliente_no_es_una_rectificativa_identica(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    original = await _emitir(client, csrf, maria)
    maria.direccion = "Calle Serrano, 47, 2.º A"
    await db.commit()

    respuesta = await _modificar(
        client, csrf, original, maria, motivo="factura_entregada", causa="error_datos"
    )

    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["cliente"]["direccion"] == "Calle Serrano, 47, 2.º A"


@pytest.mark.parametrize(
    ("causa", "lineas", "campo"),
    [(None, OTRAS_LINEAS, "causa"), ("error_datos", [], "lineas")],
)
async def test_la_rectificativa_valida_causa_y_lineas(
    client: AsyncClient,
    csrf: str,
    maria: Cliente,
    causa: str | None,
    lineas: list[dict[str, str]],
    campo: str,
) -> None:
    original = await _emitir(client, csrf, maria)

    respuesta = await _modificar(
        client, csrf, original, maria, motivo="factura_entregada", causa=causa, lineas=lineas
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["errores"][0]["campo"] == campo


async def test_el_iva_ya_no_se_revalida_con_la_fecha_de_operacion(
    admin: tuple[Usuario, str], maria: Cliente, db: AsyncSession
) -> None:
    """R-20: la lista de F-3 §15.1 es informativa. Un 7,5 % confirmado en la configuración se
    aplica aunque la fecha de la operación no esté en su ventana (01/10/2024–31/12/2024)."""
    config = await configuracion_facturacion.get(db, for_update=True)
    config.iva_por_defecto = Decimal("7.50")
    await db.flush()
    await db.refresh(maria, ["provincia"])  # en la API lo carga `billable_cliente`
    await registros.lock_chain(db)

    factura = await emision.create_factura(
        db,
        config=config,
        cliente=maria,
        fecha_expedicion=hoy(),
        fecha_operacion=None,
        lineas=(emision.DatosLinea(Decimal(1), "Anillo", Decimal(100)),),
        actor=admin[0],
        clave=uuid.uuid4(),
        operacion=OperacionIdempotente.MODIFICAR,
        origen_id=None,
    )

    assert factura.cuota_total == Decimal("7.50")


# --------------------------------------------- oro de inversión exento (FR-052, R-4, R-21)


async def test_rectificar_a_exenta_un_lingote_facturado_con_iva(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    # US5-9: el lingote se facturó con IVA por error; R1 «IVA mal aplicado», ahora exenta.
    original = await _emitir(client, csrf, maria, lineas=LINGOTE)
    assert original["totales"]["importe_total"] == "9014.50"

    respuesta = await _modificar(
        client,
        csrf,
        original,
        maria,
        motivo="factura_entregada",
        causa="devolucion_o_precio",
        lineas=LINGOTE,
        oro_inversion=True,
    )

    assert respuesta.status_code == 201, respuesta.text
    rec = respuesta.json()
    assert rec["num_serie"] == f"REC-{ANIO}-0001"
    assert rec["tipo_factura"] == "R1"
    assert rec["oro_inversion"] is True
    assert rec["totales"]["desglose"] == [{"tipo_iva": None, "base": "7450.00", "cuota": "0.00"}]
    assert rec["totales"]["importe_total"] == "7450.00"
    assert rec["rectifica_a"]["base_rectificada"] == "7450.00"
    assert rec["rectifica_a"]["cuota_rectificada"] == "1564.50"
    assert (await _detalle(client, original))["estado"] == "rectificada"
    alta = (await _cadena(db))[-1]
    assert alta.contenido["Desglose"]["DetalleDesglose"] == [
        {"ClaveRegimen": "04", "OperacionExenta": "E6", "BaseImponibleOimporteNoSujeto": "7450.00"}
    ]


async def test_rectificar_a_sujeta_una_factura_exenta(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    original = await _emitir(client, csrf, maria, lineas=LINGOTE, oro_inversion=True)

    respuesta = await _modificar(
        client,
        csrf,
        original,
        maria,
        motivo="factura_entregada",
        causa="error_datos",
        lineas=LINGOTE,
        oro_inversion=False,
    )

    assert respuesta.status_code == 201, respuesta.text
    rec = respuesta.json()
    assert rec["oro_inversion"] is False
    assert rec["totales"]["desglose"] == [
        {"tipo_iva": "21.00", "base": "7450.00", "cuota": "1564.50"}
    ]
    assert rec["rectifica_a"]["cuota_rectificada"] == "0.00"


async def test_reemitir_como_exenta(client: AsyncClient, csrf: str, maria: Cliente) -> None:
    original = await _emitir(client, csrf, maria, lineas=LINGOTE)

    respuesta = await _modificar(
        client,
        csrf,
        original,
        maria,
        motivo="no_debio_emitirse",
        lineas=LINGOTE,
        oro_inversion=True,
    )

    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["num_serie"].startswith(f"FAC-{ANIO}-")
    assert respuesta.json()["oro_inversion"] is True
    assert (await _detalle(client, original))["estado"] == "anulada"


async def test_la_casilla_cuenta_como_cambio_pero_la_misma_exenta_no(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    exenta = await _emitir(client, csrf, maria, lineas=LINGOTE, oro_inversion=True)

    identica = await _modificar(
        client,
        csrf,
        exenta,
        maria,
        motivo="factura_entregada",
        causa="error_datos",
        lineas=LINGOTE,
        oro_inversion=True,
    )
    solo_la_casilla = await _modificar(
        client,
        csrf,
        exenta,
        maria,
        motivo="factura_entregada",
        causa="devolucion_o_precio",
        lineas=LINGOTE,
        oro_inversion=False,
    )

    assert identica.status_code == 422
    assert identica.json()["type"] == "/problemas/sin-cambios"
    assert solo_la_casilla.status_code == 201, solo_la_casilla.text


async def test_devolucion_total_de_una_factura_exenta(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    exenta = await _emitir(client, csrf, maria, lineas=LINGOTE, oro_inversion=True)

    respuesta = await _modificar(
        client,
        csrf,
        exenta,
        maria,
        motivo="factura_entregada",
        causa="devolucion_o_precio",
        lineas=[],
        oro_inversion=True,
    )

    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["totales"] == {
        "desglose": [{"tipo_iva": None, "base": "0.00", "cuota": "0.00"}],
        "base_total": "0.00",
        "cuota_total": "0.00",
        "importe_total": "0.00",
    }


async def test_modificar_exige_la_casilla(client: AsyncClient, csrf: str, maria: Cliente) -> None:
    original = await _emitir(client, csrf, maria)

    respuesta = await client.post(
        f"{URL}/{original['id']}/modificacion",
        json={
            "motivo": "factura_entregada",
            "causa": "error_datos",
            "motivo_texto": "Sin la casilla",
            "cliente_id": str(maria.id),
            "lineas": OTRAS_LINEAS,
        },
        headers=cabeceras(csrf),
    )

    assert respuesta.status_code == 422
    assert "oro_inversion" in {e["campo"] for e in respuesta.json()["errores"]}


# -------------------------------------------------------------------- sobre rectificativas


async def test_una_rectificativa_se_puede_rectificar_de_nuevo(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    original = await _emitir(client, csrf, maria)
    primera = (
        await _modificar(
            client,
            csrf,
            original,
            maria,
            motivo="factura_entregada",
            causa="error_datos",
            lineas=OTRAS_LINEAS,
        )
    ).json()

    respuesta = await _modificar(
        client,
        csrf,
        primera,
        maria,
        motivo="factura_entregada",
        causa="devolucion_o_precio",
        lineas=[],
    )

    assert respuesta.status_code == 201, respuesta.text
    segunda = respuesta.json()
    assert segunda["num_serie"] == f"REC-{ANIO}-0002"
    assert segunda["rectifica_a"]["factura"]["num_serie"] == primera["num_serie"]
    assert segunda["rectifica_a"]["base_rectificada"] == "1100.00"
    assert (await _detalle(client, original))["vigente_actual"]["num_serie"] == segunda["num_serie"]


async def test_anular_una_rectificativa_devuelve_la_original_a_vigente(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    original = await _emitir(client, csrf, maria)
    rec = (
        await _modificar(
            client,
            csrf,
            original,
            maria,
            motivo="factura_entregada",
            causa="error_datos",
            lineas=OTRAS_LINEAS,
        )
    ).json()

    respuesta = await _anular(client, csrf, rec, motivo="La rectificación era un error")

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "anulada"
    revivida = await _detalle(client, original)
    assert revivida["estado"] == "vigente"
    assert revivida["vigente_actual"] is None
    [rectificacion] = revivida["correcciones"]
    assert rectificacion["en_vigor"] is False
    assert [r["tipo"] for r in revivida["registros"]] == ["alta"]  # sin registro nuevo (FR-048)
    [evento] = await eventos(db, TipoEvento.FACTURA_ANULADA)
    assert evento.detalle["reactivada"] == original["num_serie"]

    # Se puede corregir de nuevo.
    otra = await _modificar(
        client,
        csrf,
        original,
        maria,
        motivo="factura_entregada",
        causa="devolucion_o_precio",
        lineas=[],
    )
    assert otra.status_code == 201, otra.text
    assert otra.json()["num_serie"] == f"REC-{ANIO}-0002"


async def test_una_rectificativa_no_se_reemite(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    original = await _emitir(client, csrf, maria)
    rec = (
        await _modificar(
            client,
            csrf,
            original,
            maria,
            motivo="factura_entregada",
            causa="error_datos",
            lineas=OTRAS_LINEAS,
        )
    ).json()

    respuesta = await _modificar(client, csrf, rec, maria, motivo="no_debio_emitirse")

    assert respuesta.status_code == 422
    assert respuesta.json()["errores"][0]["campo"] == "motivo"


# ------------------------------------------------------------------------------- rechazos


async def test_solo_se_corrige_la_factura_vigente(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    original = await _emitir(client, csrf, maria)
    await _modificar(client, csrf, original, maria, motivo="no_debio_emitirse")

    modificar = await _modificar(
        client, csrf, original, maria, motivo="factura_entregada", causa="error_datos"
    )
    anular = await _anular(client, csrf, original)

    for respuesta in (modificar, anular):
        assert respuesta.status_code == 409
        assert respuesta.json()["type"] == "/problemas/factura-no-modificable"


async def test_modificar_es_idempotente_por_clave(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    original = await _emitir(client, csrf, maria)
    clave = uuid.uuid4()

    primera = await _modificar(
        client, csrf, original, maria, motivo="no_debio_emitirse", clave=clave
    )
    repeticion = await _modificar(
        client, csrf, original, maria, motivo="no_debio_emitirse", clave=clave
    )
    en_otra = await _anular(client, csrf, primera.json(), clave=clave)

    assert primera.status_code == 201
    assert repeticion.status_code == 200
    assert repeticion.json()["id"] == primera.json()["id"]
    assert en_otra.status_code == 409
    assert en_otra.json()["type"] == "/problemas/idempotencia-conflicto"
    assert len(await _cadena(db)) == 3


async def test_el_trigger_rechaza_corregir_una_factura_no_vigente(
    client: AsyncClient, csrf: str, admin: tuple[Usuario, str], maria: Cliente, db: AsyncSession
) -> None:
    anulada = (await _anular(client, csrf, await _emitir(client, csrf, maria))).json()
    [registro] = [r for r in await registros.list_in_order(db) if r.tipo == "anulacion"]
    conn = await db.connection()

    with pytest.raises(DBAPIError) as error:
        async with conn.begin_nested():
            await conn.execute(
                text(
                    "INSERT INTO correcciones_factura (factura_id, tipo, motivo, motivo_texto, "
                    "registro_anulacion_id, creada_por_id) VALUES (:f, 'anulacion', "
                    "'no_debio_emitirse', 'Otra vez', :r, :u)"
                ),
                {"f": anulada["id"], "r": registro.id, "u": admin[0].id},
            )

    assert getattr(error.value.orig, "sqlstate", None) == PRIVILEGIO_INSUFICIENTE


# ---------------------------------------------------------------- concurrencia (confirma)


@dataclass(frozen=True, slots=True)
class Emitida:
    usuario_id: uuid.UUID
    cliente_id: uuid.UUID
    factura_id: uuid.UUID


@pytest.fixture
async def emitida(engine_app: AsyncEngine, engine_owner: AsyncEngine) -> AsyncIterator[Emitida]:
    async with AsyncSession(engine_app, expire_on_commit=False) as sesion:
        assert (await sesion.execute(select(RegistroFacturacion.id).limit(1))).first() is None
        usuario = Usuario(
            nombre_usuario=f"conc.corr.{uuid.uuid4().hex[:6]}",
            nombre="Concurrencia",
            rol=Rol.ADMINISTRADOR.value,
            hash_contrasena=hash_password("x" * 12),
            contrasena_temporal=False,
        )
        sesion.add(usuario)
        await sesion.flush()
        await configurar_facturacion(sesion)
        cliente = await crear_cliente(sesion, usuario.id, numero="00000002W")
        factura, _ = await emision.emit_factura(
            sesion,
            emision.DatosFactura(
                fecha_expedicion=hoy(),
                cliente_id=cliente.id,
                lineas=(emision.DatosLinea(Decimal(1), "Anillo", Decimal(100)),),
            ),
            actor=usuario,
            origen=Origen(ip=None, agente=None),
            clave=uuid.uuid4(),
        )
        await sesion.commit()
    try:
        yield Emitida(usuario.id, cliente.id, factura.id)
    finally:
        await limpiar_facturacion_confirmada(
            engine_owner, clientes=[cliente.id], usuarios=[usuario.id]
        )


async def test_dos_modificaciones_simultaneas_solo_una_prospera(
    engine_app: AsyncEngine, emitida: Emitida
) -> None:
    async def modificar() -> Factura | Exception:
        async with AsyncSession(engine_app, expire_on_commit=False) as sesion:
            actor = await sesion.get(Usuario, emitida.usuario_id)
            assert actor is not None
            try:
                nueva, _ = await emision.modify_factura(
                    sesion,
                    emitida.factura_id,
                    emision.DatosModificacion(
                        motivo=MotivoModificacion.FACTURA_ENTREGADA,
                        causa=CausaRectificacion.DEVOLUCION_O_PRECIO,
                        motivo_texto="Devolución",
                        cliente_id=emitida.cliente_id,
                        lineas=(),
                    ),
                    actor=actor,
                    origen=Origen(ip=None, agente=None),
                    clave=uuid.uuid4(),
                )
            except FacturaNoModificable as exc:
                return exc
            await sesion.commit()
            return nueva

    resultados = await asyncio.gather(modificar(), modificar())

    assert sum(isinstance(r, Factura) for r in resultados) == 1
    assert sum(isinstance(r, FacturaNoModificable) for r in resultados) == 1
    async with AsyncSession(engine_app) as sesion:
        cola = await registros.list_in_order(sesion)
    assert [r.tipo for r in cola] == ["alta", "alta"]

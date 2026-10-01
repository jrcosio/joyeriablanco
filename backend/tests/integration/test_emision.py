"""US2 — Emitir una factura sin borrador (FR-004 a FR-018, FR-021, FR-028 a FR-030, FR-042, FR-047).

Research R-3 (contenido del registro), R-6 (cadena), R-7 (numeración), R-9 (flujo) y R-18
(idempotencia).
"""

import uuid
from datetime import date, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app.core.tiempo import hoy
from app.domain.tipos import Rol, TipoEvento
from app.models import Cliente, RegistroFacturacion, Usuario
from app.services import cadena
from tests.conftest import CrearUsuario, IniciarSesion, eventos
from tests.integration.facturacion_datos import (
    IBAN_DEMO,
    LINEAS_CAPTURA,
    LINGOTE,
    cabeceras,
    configurar_facturacion,
    crear_cliente,
    cuerpo_factura,
)

URL = "/api/v1/facturas"


@pytest.fixture
async def empleada(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> tuple[Usuario, str]:
    usuario = await crear_usuario("empleada.emision")
    return usuario, await iniciar_sesion(client, "empleada.emision")


@pytest.fixture
async def maria(db: AsyncSession, empleada: tuple[Usuario, str]) -> Cliente:
    await configurar_facturacion(db)
    return await crear_cliente(db, empleada[0].id)


async def _emitir(
    client: AsyncClient, csrf: str, cuerpo: dict[str, Any], clave: uuid.UUID | None = None
) -> Any:
    return await client.post(URL, json=cuerpo, headers=cabeceras(csrf, clave))


async def test_emitir_asigna_numero_calcula_importes_y_genera_el_registro(
    client: AsyncClient, empleada: tuple[Usuario, str], maria: Cliente, db: AsyncSession
) -> None:
    respuesta = await _emitir(client, empleada[1], cuerpo_factura(maria.id))

    assert respuesta.status_code == 201, respuesta.text
    factura = respuesta.json()
    assert factura["num_serie"] == f"FAC-{hoy().year}-0001"
    assert factura["tipo_factura"] == "F1"
    assert factura["estado"] == "vigente"
    assert [linea["importe"] for linea in factura["lineas"]] == ["1200.00", "90.00"]
    assert [linea["tipo_iva"] for linea in factura["lineas"]] == ["21.00", "21.00"]
    assert factura["totales"] == {
        "desglose": [{"tipo_iva": "21.00", "base": "1290.00", "cuota": "270.90"}],
        "base_total": "1290.00",
        "cuota_total": "270.90",
        "importe_total": "1560.90",
    }
    assert factura["emisor"]["nif"] == "B12345674"
    assert factura["emisor"]["provincia"] == "Cantabria"
    assert factura["emisor"]["iban"] is None  # sin IBAN en la configuración (FR-053)
    assert factura["oro_inversion"] is False
    assert factura["mencion_exencion"] is None
    assert factura["cliente"]["nombre"] == "María López García"
    assert factura["cliente"]["direccion"] == "Calle Serrano, 45, 2.º A"
    assert factura["descripcion_operacion"] == "; ".join(
        linea["descripcion"] for linea in LINEAS_CAPTURA
    )
    assert factura["emitida_por"]["nombre"] == "Ana García"
    (registro,) = factura["registros"]
    assert registro["tipo"] == "alta"
    assert registro["secuencia"] == 1
    assert registro["estado_remision"] == "pendiente"

    guardado = (await db.execute(select(RegistroFacturacion))).scalar_one()
    assert guardado.primer_registro
    assert guardado.modalidad == "verifactu"
    assert cadena.recompute_huella(guardado) == guardado.huella == registro["huella"]
    contenido = guardado.contenido
    assert contenido["IDFactura"]["NumSerieFactura"] == factura["num_serie"]
    assert contenido["Destinatarios"] == {
        "IDDestinatario": [{"NombreRazon": "María López García", "NIF": "12345678Z"}]
    }
    assert contenido["ImporteTotal"] == "1560.90"
    assert contenido["Desglose"]["DetalleDesglose"] == [
        {
            "ClaveRegimen": "01",
            "CalificacionOperacion": "S1",
            "TipoImpositivo": "21.00",
            "BaseImponibleOimporteNoSujeto": "1290.00",
            "CuotaRepercutida": "270.90",
        }
    ]
    (evento,) = await eventos(db, TipoEvento.FACTURA_EMITIDA)
    assert evento.detalle["num_serie"] == factura["num_serie"]
    assert evento.detalle["importe_total"] == "1560.90"


async def test_la_numeracion_es_correlativa(
    client: AsyncClient, empleada: tuple[Usuario, str], maria: Cliente
) -> None:
    numeros = [
        (await _emitir(client, empleada[1], cuerpo_factura(maria.id))).json()["num_serie"]
        for _ in range(3)
    ]

    anio = hoy().year
    assert numeros == [f"FAC-{anio}-0001", f"FAC-{anio}-0002", f"FAC-{anio}-0003"]


async def test_detalle_de_una_factura(
    client: AsyncClient, empleada: tuple[Usuario, str], maria: Cliente
) -> None:
    emitida = (await _emitir(client, empleada[1], cuerpo_factura(maria.id))).json()

    detalle = await client.get(f"{URL}/{emitida['id']}")

    assert detalle.status_code == 200
    assert detalle.json() == emitida
    assert (await client.get(f"{URL}/{uuid.uuid4()}")).status_code == 404


async def test_el_anio_del_numero_es_el_de_la_fecha(
    client: AsyncClient, empleada: tuple[Usuario, str], maria: Cliente
) -> None:
    anterior = date(hoy().year - 1, 12, 31)

    respuesta = await _emitir(client, empleada[1], cuerpo_factura(maria.id, fecha=anterior))

    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["num_serie"] == f"FAC-{anterior.year}-0001"


async def test_editar_el_cliente_despues_no_altera_la_factura(
    client: AsyncClient, empleada: tuple[Usuario, str], maria: Cliente, db: AsyncSession
) -> None:
    emitida = (await _emitir(client, empleada[1], cuerpo_factura(maria.id))).json()
    maria.nombre = "María López Cambiada"
    await db.flush()

    detalle = (await client.get(f"{URL}/{emitida['id']}")).json()

    assert detalle["cliente"]["nombre"] == "María López García"


# --------------------------------------------------------------------------- rechazos


async def test_sin_configuracion_completa_no_se_emite(
    client: AsyncClient, empleada: tuple[Usuario, str], db: AsyncSession
) -> None:
    cliente = await crear_cliente(db, empleada[0].id)

    respuesta = await _emitir(client, empleada[1], cuerpo_factura(cliente.id))

    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == "/problemas/emision-no-disponible"
    assert "modalidad" in respuesta.json()["faltan"]


@pytest.mark.parametrize(
    ("activo", "con_domicilio", "falta"),
    [(False, True, "activo"), (True, False, "direccion")],
)
async def test_cliente_no_facturable(
    client: AsyncClient,
    empleada: tuple[Usuario, str],
    db: AsyncSession,
    activo: bool,
    con_domicilio: bool,
    falta: str,
) -> None:
    await configurar_facturacion(db)
    cliente = await crear_cliente(db, empleada[0].id, activo=activo, con_domicilio=con_domicilio)

    respuesta = await _emitir(client, empleada[1], cuerpo_factura(cliente.id))

    assert respuesta.status_code == 422
    assert respuesta.json()["type"] == "/problemas/cliente-no-facturable"
    assert falta in respuesta.json()["faltan"]


@pytest.mark.parametrize(
    "fecha",
    [
        lambda: hoy() + timedelta(days=1),  # futura (F-3 §3.1.3.1, error 1112)
        lambda: date(2024, 10, 27),  # antes de la Orden (F-3 §3.1.3.1, error 1152)
    ],
    ids=["futura", "anterior-a-la-orden"],
)
async def test_fecha_de_expedicion_no_valida(
    client: AsyncClient, empleada: tuple[Usuario, str], maria: Cliente, fecha: Any
) -> None:
    respuesta = await _emitir(client, empleada[1], cuerpo_factura(maria.id, fecha=fecha()))

    assert respuesta.status_code == 422
    assert respuesta.json()["type"] == "/problemas/fecha-expedicion"


async def test_la_fecha_puede_ser_anterior_a_la_ultima_de_la_serie(
    client: AsyncClient, empleada: tuple[Usuario, str], maria: Cliente
) -> None:
    """FR-018 (cambio tras la implementación): sin orden entre fecha y número en la serie."""
    if hoy().month == 1 and hoy().day == 1:
        pytest.skip("El 1 de enero no hay un día anterior en la misma serie")
    primera = (await _emitir(client, empleada[1], cuerpo_factura(maria.id))).json()
    inicio_de_anio = date(hoy().year, 1, 1)

    respuesta = await _emitir(client, empleada[1], cuerpo_factura(maria.id, fecha=inicio_de_anio))

    assert respuesta.status_code == 201, respuesta.text
    segunda = respuesta.json()
    assert segunda["num_serie"] == f"FAC-{hoy().year}-0002"
    assert segunda["fecha_expedicion"] == inicio_de_anio.isoformat()
    assert segunda["fecha_expedicion"] < primera["fecha_expedicion"]


async def test_la_fecha_puede_ser_de_cualquier_anio_desde_la_orden(
    client: AsyncClient, empleada: tuple[Usuario, str], maria: Cliente
) -> None:
    fecha = max(date(hoy().year - 2, 12, 15), date(2024, 10, 28))

    respuesta = await _emitir(client, empleada[1], cuerpo_factura(maria.id, fecha=fecha))

    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["num_serie"] == f"FAC-{fecha.year}-0001"


@pytest.mark.parametrize(("tipo", "cuota"), [("5", "64.50"), ("22", "283.80")])
async def test_un_tipo_fuera_de_la_lista_oficial_ya_no_impide_emitir(
    client: AsyncClient,
    empleada: tuple[Usuario, str],
    maria: Cliente,
    conexion: AsyncConnection,
    tipo: str,
    cuota: str,
) -> None:
    # R-20: la lista de F-3 §15.1 es informativa; el administrador ya confirmó el tipo al
    # configurarlo y emitir nunca se bloquea por él (FR-001, FR-013).
    await conexion.execute(
        text("UPDATE configuracion_facturacion SET iva_por_defecto = :t"), {"t": tipo}
    )

    respuesta = await _emitir(client, empleada[1], cuerpo_factura(maria.id))

    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["totales"]["cuota_total"] == cuota


# ------------------------------------------------ oro de inversión exento (FR-052, R-21)


async def test_emitir_una_factura_de_oro_de_inversion_sin_iva(
    client: AsyncClient,
    empleada: tuple[Usuario, str],
    maria: Cliente,
    db: AsyncSession,
    conexion: AsyncConnection,
) -> None:
    respuesta = await _emitir(
        client, empleada[1], cuerpo_factura(maria.id, lineas=LINGOTE, oro_inversion=True)
    )

    assert respuesta.status_code == 201, respuesta.text
    factura = respuesta.json()
    assert factura["oro_inversion"] is True
    assert factura["mencion_exencion"] == (
        "Operación exenta de IVA (art. 140 bis.Uno.1.º de la Ley 37/1992)"
    )
    assert [linea["tipo_iva"] for linea in factura["lineas"]] == [None]
    assert factura["totales"] == {
        "desglose": [{"tipo_iva": None, "base": "7450.00", "cuota": "0.00"}],
        "base_total": "7450.00",
        "cuota_total": "0.00",
        "importe_total": "7450.00",
    }
    fila = (
        await conexion.execute(
            text(
                "SELECT f.clave_regimen, d.clave_regimen, d.calificacion_operacion, "
                "d.operacion_exenta, d.tipo_iva, d.orden FROM facturas f "
                "JOIN desgloses_factura d ON d.factura_id = f.id WHERE f.id = :id"
            ),
            {"id": factura["id"]},
        )
    ).one()
    assert tuple(fila) == ("04", "04", None, "E6", None, 1)
    guardado = (await db.execute(select(RegistroFacturacion))).scalar_one()
    assert guardado.contenido["Desglose"]["DetalleDesglose"] == [
        {"ClaveRegimen": "04", "OperacionExenta": "E6", "BaseImponibleOimporteNoSujeto": "7450.00"}
    ]
    assert guardado.contenido["CuotaTotal"] == "0.00"
    assert guardado.contenido["ImporteTotal"] == "7450.00"
    assert cadena.recompute_huella(guardado) == guardado.huella


async def test_sin_la_casilla_la_factura_va_con_iva_como_antes(
    client: AsyncClient, empleada: tuple[Usuario, str], maria: Cliente
) -> None:
    respuesta = await _emitir(
        client, empleada[1], cuerpo_factura(maria.id, lineas=LINGOTE, oro_inversion=False)
    )

    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["oro_inversion"] is False
    assert respuesta.json()["totales"]["cuota_total"] == "1564.50"


# ---------------------------------------------------------------- IBAN (FR-016, FR-053)


async def test_el_iban_se_copia_al_emitir_y_no_cambia_despues(
    client: AsyncClient, empleada: tuple[Usuario, str], maria: Cliente, db: AsyncSession
) -> None:
    await configurar_facturacion(db, iban=IBAN_DEMO)
    emitida = (await _emitir(client, empleada[1], cuerpo_factura(maria.id))).json()
    await configurar_facturacion(db, iban="DE89370400440532013000")

    detalle = (await client.get(f"{URL}/{emitida['id']}")).json()

    assert emitida["emisor"]["iban"] == IBAN_DEMO
    assert detalle["emisor"]["iban"] == IBAN_DEMO


async def test_los_parametros_llevan_la_mencion_de_la_exencion(
    client: AsyncClient, empleada: tuple[Usuario, str]
) -> None:
    respuesta = await client.get(f"{URL}/parametros")

    assert respuesta.json()["mencion_exencion_oro_inversion"] == (
        "Operación exenta de IVA (art. 140 bis.Uno.1.º de la Ley 37/1992)"
    )


@pytest.mark.parametrize(
    "lineas",
    [
        [],  # sin líneas
        [{"unidades": 1, "descripcion": "Anillo", "precio_unitario": "10"}],  # número JSON
        [{"unidades": "0", "descripcion": "Anillo", "precio_unitario": "10"}],
        [{"unidades": "1", "descripcion": "   ", "precio_unitario": "10"}],
        [{"unidades": "1", "descripcion": "Anillo", "precio_unitario": "0"}],  # total cero
    ],
)
async def test_lineas_no_validas(
    client: AsyncClient, empleada: tuple[Usuario, str], maria: Cliente, lineas: list[Any]
) -> None:
    respuesta = await _emitir(client, empleada[1], cuerpo_factura(maria.id, lineas=lineas))

    assert respuesta.status_code == 422
    assert respuesta.json()["type"] == "/problemas/validacion"


async def test_los_totales_del_cliente_se_rechazan(
    client: AsyncClient, empleada: tuple[Usuario, str], maria: Cliente
) -> None:
    cuerpo = {**cuerpo_factura(maria.id), "importe_total": "1.00"}

    respuesta = await _emitir(client, empleada[1], cuerpo)

    assert respuesta.status_code == 422


async def test_sin_clave_de_idempotencia_no_se_emite(
    client: AsyncClient, empleada: tuple[Usuario, str], maria: Cliente
) -> None:
    respuesta = await client.post(
        URL, json=cuerpo_factura(maria.id), headers={"X-CSRF-Token": empleada[1]}
    )

    assert respuesta.status_code == 422


# ------------------------------------------------------------------------ idempotencia


async def test_repetir_la_clave_devuelve_la_misma_factura_sin_emitir_otra(
    client: AsyncClient, empleada: tuple[Usuario, str], maria: Cliente, db: AsyncSession
) -> None:
    clave = uuid.uuid4()

    primera = await _emitir(client, empleada[1], cuerpo_factura(maria.id), clave)
    segunda = await _emitir(client, empleada[1], cuerpo_factura(maria.id), clave)

    assert (primera.status_code, segunda.status_code) == (201, 200)
    assert segunda.json()["id"] == primera.json()["id"]
    registros = (await db.execute(select(RegistroFacturacion))).scalars().all()
    assert len(registros) == 1
    siguiente = await _emitir(client, empleada[1], cuerpo_factura(maria.id))
    assert siguiente.json()["num_serie"].endswith("-0002")  # no se consumió ningún número


# ------------------------------------------------------------------- cadena y cliente


async def test_una_cadena_inconsistente_impide_emitir(
    client: AsyncClient,
    empleada: tuple[Usuario, str],
    maria: Cliente,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _emitir(client, empleada[1], cuerpo_factura(maria.id))
    monkeypatch.setattr(cadena, "tail_problem", lambda *_: "prueba")

    respuesta = await _emitir(client, empleada[1], cuerpo_factura(maria.id))

    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == "/problemas/cadena-inconsistente"


async def test_un_cliente_con_facturas_no_se_puede_borrar(
    client: AsyncClient,
    empleada: tuple[Usuario, str],
    maria: Cliente,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    otro_cliente: Any,
) -> None:
    await _emitir(client, empleada[1], cuerpo_factura(maria.id))
    await crear_usuario("admin.borrado", rol=Rol.ADMINISTRADOR)
    async with otro_cliente() as admin:
        csrf = await iniciar_sesion(admin, "admin.borrado")

        respuesta = await admin.delete(
            f"/api/v1/clientes/{maria.id}", headers={"X-CSRF-Token": csrf}
        )

    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == "/problemas/cliente-con-documentos"

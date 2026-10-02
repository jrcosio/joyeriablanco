"""Modificar y anular un presupuesto emitido (005, US4; FR-005, FR-015 a FR-017, FR-021, FR-028).

«Modificar» emite un presupuesto nuevo que sustituye al original, y «Anular» lo cierra con un
motivo. Los dos son cierres inalterables, solo de administradores, sobre un pendiente o un caducado
sin borrador de factura vinculado. Ninguno toca la cadena de registros ni el contador FAC.

Las pruebas de concurrencia (doble envío y carreras frente a la conversión, que pasan aquí desde
T045) usan sesiones reales que confirman, como `test_conversion_presupuesto.py`.
"""

import asyncio
import io
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient, Response
from pypdf import PdfReader
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.errors import PresupuestoNoModificable
from app.core.http import Origen
from app.core.security import hash_password
from app.core.tiempo import hoy
from app.domain.tipos import Rol, Serie, TipoEvento
from app.models import (
    BorradorFactura,
    Cliente,
    ContadorFactura,
    Presupuesto,
    RegistroFacturacion,
    Usuario,
)
from app.models.cierre_presupuesto import CierrePresupuesto
from app.services import contenido, conversion, presupuestos
from tests.conftest import CrearUsuario, IniciarSesion, eventos
from tests.integration.facturacion_datos import (
    URL_PRESUPUESTOS,
    cabeceras,
    configurar_facturacion,
    crear_cliente,
    cuerpo_factura,
    emitir_presupuesto,
    limpiar_facturacion_confirmada,
)

ANIO = hoy().year
ORIGEN = Origen(ip=None, agente=None)
MOTIVO = "Cambio de talla"


@pytest.fixture
async def admin(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> tuple[Usuario, str]:
    usuario = await crear_usuario("admin.cierres", rol=Rol.ADMINISTRADOR)
    return usuario, await iniciar_sesion(client, "admin.cierres")


@pytest.fixture
def csrf(admin: tuple[Usuario, str]) -> str:
    return admin[1]


@pytest.fixture
async def maria(db: AsyncSession, admin: tuple[Usuario, str]) -> Cliente:
    await configurar_facturacion(db)
    return await crear_cliente(db, admin[0].id)


def _cuerpo_modificacion(presupuesto: dict[str, Any], **cambios: Any) -> dict[str, Any]:
    """El modal precargado con el original, la fecha de hoy y el motivo (FR-015)."""
    cuerpo: dict[str, Any] = {
        "motivo_texto": MOTIVO,
        "fecha": hoy().isoformat(),
        "valido_hasta": presupuesto["valido_hasta"],
        "cliente_id": presupuesto["cliente"]["id"],
        "lineas": [
            {
                "unidades": linea["unidades"],
                "descripcion": linea["descripcion"],
                "precio_unitario": linea["precio_unitario"],
            }
            for linea in presupuesto["lineas"]
        ],
        "oro_inversion": presupuesto["oro_inversion"],
    }
    cuerpo.update(cambios)
    return cuerpo


async def _modificar(
    client: AsyncClient,
    csrf: str,
    presupuesto: dict[str, Any],
    clave: uuid.UUID | None = None,
    **cambios: Any,
) -> Response:
    return await client.post(
        f"{URL_PRESUPUESTOS}/{presupuesto['id']}/modificacion",
        json=_cuerpo_modificacion(presupuesto, **cambios),
        headers=cabeceras(csrf, clave),
    )


async def _anular(
    client: AsyncClient,
    csrf: str,
    presupuesto: dict[str, Any],
    clave: uuid.UUID | None = None,
    motivo: str = "Rechazado por el cliente",
) -> Response:
    return await client.post(
        f"{URL_PRESUPUESTOS}/{presupuesto['id']}/anulacion",
        json={"motivo_texto": motivo},
        headers=cabeceras(csrf, clave),
    )


async def _consultar(client: AsyncClient, presupuesto: dict[str, Any]) -> dict[str, Any]:
    respuesta = await client.get(f"{URL_PRESUPUESTOS}/{presupuesto['id']}")
    assert respuesta.status_code == 200, respuesta.text
    return dict(respuesta.json())


async def _contador(db: AsyncSession, serie: Serie) -> int:
    resultado = await db.scalar(
        select(ContadorFactura.ultimo_numero).where(
            ContadorFactura.serie == serie.value, ContadorFactura.anio == ANIO
        )
    )
    return int(resultado or 0)


async def _cuenta(db: AsyncSession, modelo: type[Any]) -> int:
    return int(await db.scalar(select(func.count()).select_from(modelo)) or 0)


def _referencia(presupuesto: dict[str, Any]) -> dict[str, str]:
    return {k: presupuesto[k] for k in ("id", "num_serie", "fecha")}


def _texto_pdf(pdf: bytes) -> str:
    return " ".join(" ".join(p.extract_text().split()) for p in PdfReader(io.BytesIO(pdf)).pages)


# ------------------------------------------------------------------------------ modificar


async def test_modificar_emite_el_siguiente_y_sustituye_al_original(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    original = await emitir_presupuesto(client, csrf, maria.id)

    respuesta = await _modificar(
        client,
        csrf,
        original,
        lineas=[{"unidades": "1", "descripcion": "Anillo talla 15", "precio_unitario": "1100"}],
    )

    assert respuesta.status_code == 201, respuesta.text
    nuevo = respuesta.json()
    assert nuevo["num_serie"] == f"PRE-{ANIO}-0002"
    assert nuevo["estado"] == "pendiente"
    assert nuevo["sustituye_a"] == _referencia(original)
    assert nuevo["totales"]["importe_total"] == "1331.00"
    sustituido = await _consultar(client, original)
    assert sustituido["estado"] == "sustituido"
    assert sustituido["vigente_actual"] == _referencia(nuevo)
    assert sustituido["cierre"]["tipo"] == "sustitucion"
    assert sustituido["cierre"]["motivo_texto"] == MOTIVO
    assert sustituido["cierre"]["presupuesto_nuevo"] == _referencia(nuevo)
    # El original sigue intacto (FR-005)
    assert sustituido["lineas"] == original["lineas"]
    assert sustituido["totales"] == original["totales"]
    [evento] = await eventos(db, TipoEvento.PRESUPUESTO_MODIFICADO)
    assert evento.detalle == {
        "presupuesto_id": original["id"],
        "num_serie": original["num_serie"],
        "presupuesto_nuevo_id": nuevo["id"],
        "num_serie_nuevo": nuevo["num_serie"],
        "motivo_texto": MOTIVO,
    }


async def test_en_una_cadena_de_sustituciones_apunta_al_ultimo(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    original = await emitir_presupuesto(client, csrf, maria.id)
    segundo = (
        await _modificar(client, csrf, original, valido_hasta=(hoy() + timedelta(60)).isoformat())
    ).json()
    tercero = (
        await _modificar(client, csrf, segundo, valido_hasta=(hoy() + timedelta(90)).isoformat())
    ).json()

    assert (await _consultar(client, original))["vigente_actual"] == _referencia(tercero)
    assert (await _consultar(client, segundo))["vigente_actual"] == _referencia(tercero)
    assert (await _consultar(client, tercero))["sustituye_a"] == _referencia(segundo)
    pdf = await client.get(f"{URL_PRESUPUESTOS}/{original['id']}/pdf")
    assert f"SUSTITUIDO por {tercero['num_serie']}" in _texto_pdf(pdf.content)


async def test_solo_la_fecha_cambiada_no_es_un_cambio(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    original = await emitir_presupuesto(
        client,
        csrf,
        maria.id,
        fecha=hoy() - timedelta(days=3),
        valido_hasta=hoy() + timedelta(days=27),
    )

    respuesta = await _modificar(client, csrf, original)  # la fecha de hoy, el resto igual

    assert respuesta.status_code == 422
    cuerpo = respuesta.json()
    assert cuerpo["type"] == "/problemas/sin-cambios"
    assert "además de la fecha" in cuerpo["detail"]
    assert await _contador(db, Serie.PRESUPUESTO) == 1
    assert (await _consultar(client, original))["estado"] == "pendiente"


async def test_cualquier_otro_cambio_si_emite(
    client: AsyncClient,
    csrf: str,
    admin: tuple[Usuario, str],
    maria: Cliente,
    db: AsyncSession,
) -> None:
    otro = await crear_cliente(db, admin[0].id, nombre="Jean Dupont", numero="00000001R")

    async def cambia(cambio: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]) -> None:
        original = await emitir_presupuesto(client, csrf, maria.id)
        respuesta = await _modificar(client, csrf, original, **await cambio(original))
        assert respuesta.status_code == 201, respuesta.text

    async def de_cliente(_: dict[str, Any]) -> dict[str, Any]:
        return {"cliente_id": str(otro.id)}

    async def de_lineas(_: dict[str, Any]) -> dict[str, Any]:
        return {"lineas": [{"unidades": "3", "descripcion": "Otra", "precio_unitario": "10"}]}

    async def de_oro(_: dict[str, Any]) -> dict[str, Any]:
        return {"oro_inversion": True}

    async def de_validez(p: dict[str, Any]) -> dict[str, Any]:
        return {"valido_hasta": (hoy() + timedelta(days=45)).isoformat()}

    async def de_copia_del_cliente(_: dict[str, Any]) -> dict[str, Any]:
        maria.direccion = "Calle Nueva, 7"  # la copia que se haría ya no es la del original
        await db.flush()
        return {}

    for cambio in (de_cliente, de_lineas, de_oro, de_validez, de_copia_del_cliente):
        await cambia(cambio)

    # El IVA que se aplicaría también cuenta
    original = await emitir_presupuesto(client, csrf, maria.id)
    await configurar_facturacion(db, iva="10")
    assert (await _modificar(client, csrf, original)).status_code == 201


async def test_un_caducado_se_modifica_ampliando_la_validez(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    caducado = await emitir_presupuesto(
        client, csrf, maria.id, fecha=hoy() - timedelta(40), valido_hasta=hoy() - timedelta(10)
    )
    assert caducado["estado"] == "caducado"

    respuesta = await _modificar(
        client, csrf, caducado, valido_hasta=(hoy() + timedelta(days=30)).isoformat()
    )

    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["estado"] == "pendiente"
    assert (await _consultar(client, caducado))["estado"] == "sustituido"


async def test_fechas_no_validas_responden_422_en_su_campo(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    original = await emitir_presupuesto(client, csrf, maria.id)

    futura = await _modificar(client, csrf, original, fecha=(hoy() + timedelta(1)).isoformat())
    validez = await _modificar(
        client, csrf, original, valido_hasta=(hoy() - timedelta(1)).isoformat()
    )

    for respuesta, campo in ((futura, "fecha"), (validez, "valido_hasta")):
        assert respuesta.status_code == 422
        assert respuesta.json()["type"] == "/problemas/validacion"
        assert [e["campo"] for e in respuesta.json()["errores"]] == [campo]
    assert await _contador(db, Serie.PRESUPUESTO) == 1


# -------------------------------------------------------------------------------- anular


async def test_anular_con_motivo(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)

    respuesta = await _anular(client, csrf, presupuesto)

    assert respuesta.status_code == 200, respuesta.text
    anulado = respuesta.json()
    assert anulado["estado"] == "anulado"
    assert anulado["cierre"]["tipo"] == "anulacion"
    assert anulado["cierre"]["motivo_texto"] == "Rechazado por el cliente"
    assert anulado["cierre"]["presupuesto_nuevo"] is None
    assert anulado["cierre"]["factura"] is None
    pdf = await client.get(f"{URL_PRESUPUESTOS}/{presupuesto['id']}/pdf")
    assert "ANULADO" in _texto_pdf(pdf.content)
    [evento] = await eventos(db, TipoEvento.PRESUPUESTO_ANULADO)
    assert evento.detalle == {
        "presupuesto_id": presupuesto["id"],
        "num_serie": presupuesto["num_serie"],
        "motivo_texto": "Rechazado por el cliente",
    }


@pytest.mark.parametrize("motivo", ["", "   "])
async def test_anular_sin_motivo_responde_422(
    client: AsyncClient, csrf: str, maria: Cliente, motivo: str
) -> None:
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)

    respuesta = await _anular(client, csrf, presupuesto, motivo=motivo)

    assert respuesta.status_code == 422
    assert (await _consultar(client, presupuesto))["estado"] == "pendiente"


async def test_modificar_sin_motivo_responde_422(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)

    respuesta = await _modificar(
        client, csrf, presupuesto, motivo_texto="", valido_hasta=(hoy() + timedelta(9)).isoformat()
    )

    assert respuesta.status_code == 422


# ------------------------------------------------------------------------ sin efectos fiscales


async def test_modificar_y_anular_no_tocan_la_cadena_ni_el_contador_fac(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    factura = await client.post(
        "/api/v1/facturas", json=cuerpo_factura(maria.id), headers=cabeceras(csrf)
    )
    assert factura.status_code == 201
    registros, fac = await _cuenta(db, RegistroFacturacion), await _contador(db, Serie.ORDINARIA)
    original = await emitir_presupuesto(client, csrf, maria.id)

    nuevo = (
        await _modificar(client, csrf, original, valido_hasta=(hoy() + timedelta(60)).isoformat())
    ).json()
    await _anular(client, csrf, nuevo)

    assert await _cuenta(db, RegistroFacturacion) == registros
    assert await _contador(db, Serie.ORDINARIA) == fac


# -------------------------------------------------------------------------- permisos y estados


async def test_un_empleado_no_modifica_ni_anula(
    client: AsyncClient,
    csrf: str,
    maria: Cliente,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
) -> None:
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)
    await crear_usuario("empleado.cierres")
    csrf_empleado = await iniciar_sesion(client, "empleado.cierres")

    modificar = await _modificar(
        client, csrf_empleado, presupuesto, valido_hasta=(hoy() + timedelta(9)).isoformat()
    )
    anular = await _anular(client, csrf_empleado, presupuesto)

    for respuesta in (modificar, anular):
        assert respuesta.status_code == 403
        assert respuesta.json()["type"] == "/problemas/sin-permiso"
    assert (await _consultar(client, presupuesto))["estado"] == "pendiente"


async def test_sobre_uno_cerrado_o_en_facturacion_responde_409(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    anulado = await emitir_presupuesto(client, csrf, maria.id)
    await _anular(client, csrf, anulado)
    en_facturacion = await emitir_presupuesto(client, csrf, maria.id)
    borrador = (
        await client.post(
            f"{URL_PRESUPUESTOS}/{en_facturacion['id']}/conversion",
            headers={"X-CSRF-Token": csrf},
        )
    ).json()
    contador = await _contador(db, Serie.PRESUPUESTO)

    for presupuesto, estado, borrador_id in (
        (anulado, "anulado", None),
        (en_facturacion, "en_facturacion", borrador["id"]),
    ):
        for respuesta in (
            await _modificar(
                client, csrf, presupuesto, valido_hasta=(hoy() + timedelta(9)).isoformat()
            ),
            await _anular(client, csrf, presupuesto),
        ):
            assert respuesta.status_code == 409, estado
            cuerpo = respuesta.json()
            assert cuerpo["type"] == "/problemas/presupuesto-no-modificable"
            assert cuerpo["estado"] == estado
            assert cuerpo.get("borrador_factura_id") == borrador_id
    assert await _contador(db, Serie.PRESUPUESTO) == contador
    assert await _cuenta(db, CierrePresupuesto) == 1


async def test_un_inexistente_responde_404(client: AsyncClient, csrf: str, maria: Cliente) -> None:
    falso = {"id": str(uuid.uuid4())}
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)

    modificar = await client.post(
        f"{URL_PRESUPUESTOS}/{falso['id']}/modificacion",
        json=_cuerpo_modificacion(presupuesto),
        headers=cabeceras(csrf),
    )

    assert modificar.status_code == 404
    assert (await _anular(client, csrf, falso)).status_code == 404


# ------------------------------------------------------------------------------ idempotencia


async def test_repetir_con_la_misma_clave_devuelve_lo_mismo(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    original = await emitir_presupuesto(client, csrf, maria.id)
    clave = uuid.uuid4()
    validez = (hoy() + timedelta(60)).isoformat()
    primera = await _modificar(client, csrf, original, clave, valido_hasta=validez)

    repeticion = await _modificar(client, csrf, original, clave, valido_hasta=validez)

    assert primera.status_code == 201
    assert repeticion.status_code == 200
    assert repeticion.json()["id"] == primera.json()["id"]
    assert await _contador(db, Serie.PRESUPUESTO) == 2

    otro = await emitir_presupuesto(client, csrf, maria.id)
    clave_anular = uuid.uuid4()
    assert (await _anular(client, csrf, otro, clave_anular)).status_code == 200
    repetida = await _anular(client, csrf, otro, clave_anular)
    assert repetida.status_code == 200
    assert repetida.json()["estado"] == "anulado"
    assert await _cuenta(db, CierrePresupuesto) == 2


async def test_la_clave_de_anular_reutilizada_en_modificar_es_un_conflicto(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    anulado = await emitir_presupuesto(client, csrf, maria.id)
    otro = await emitir_presupuesto(client, csrf, maria.id)
    clave = uuid.uuid4()
    await _anular(client, csrf, anulado, clave)

    for presupuesto in (anulado, otro):
        respuesta = await _modificar(
            client, csrf, presupuesto, clave, valido_hasta=(hoy() + timedelta(9)).isoformat()
        )
        assert respuesta.status_code == 409
        assert respuesta.json()["type"] == "/problemas/idempotencia-conflicto"
    # Y la de modificar, en anular
    clave_modificar = uuid.uuid4()
    validez = (hoy() + timedelta(9)).isoformat()
    await _modificar(client, csrf, otro, clave_modificar, valido_hasta=validez)
    otro_mas = await emitir_presupuesto(client, csrf, maria.id)
    conflicto = await _anular(client, csrf, otro_mas, clave_modificar)
    assert conflicto.status_code == 409
    assert conflicto.json()["type"] == "/problemas/idempotencia-conflicto"


# ------------------------------------------------------- concurrencia (sesiones que confirman)


@dataclass(frozen=True, slots=True)
class Escenario:
    usuario_id: uuid.UUID
    cliente_id: uuid.UUID


LINEA = (contenido.DatosLinea(Decimal(1), "Anillo", Decimal("100.00")),)


def _datos(escenario: Escenario, dias: int = 30) -> presupuestos.DatosPresupuesto:
    return presupuestos.DatosPresupuesto(
        fecha=hoy(),
        valido_hasta=hoy() + timedelta(days=dias),
        cliente_id=escenario.cliente_id,
        lineas=LINEA,
    )


@pytest.fixture
async def escenario(engine_app: AsyncEngine, engine_owner: AsyncEngine) -> AsyncIterator[Escenario]:
    async with AsyncSession(engine_app, expire_on_commit=False) as sesion:
        assert (await sesion.execute(select(func.count(Presupuesto.id)))).scalar() == 0
        usuario = Usuario(
            nombre_usuario=f"conc.cier.{uuid.uuid4().hex[:6]}",
            nombre="Concurrencia",
            rol=Rol.ADMINISTRADOR.value,
            hash_contrasena=hash_password("x" * 12),
            contrasena_temporal=False,
        )
        sesion.add(usuario)
        await sesion.flush()
        await configurar_facturacion(sesion)
        cliente = await crear_cliente(sesion, usuario.id, numero="00000001R")
        await sesion.commit()
    try:
        yield Escenario(usuario.id, cliente.id)
    finally:
        await limpiar_facturacion_confirmada(
            engine_owner, clientes=[cliente.id], usuarios=[usuario.id]
        )


async def _en_sesion[T](
    engine_app: AsyncEngine,
    escenario: Escenario,
    operacion: Callable[[AsyncSession, Usuario], Awaitable[T]],
) -> T:
    async with AsyncSession(engine_app, expire_on_commit=False) as sesion:
        actor = await sesion.get(Usuario, escenario.usuario_id)
        assert actor is not None
        resultado = await operacion(sesion, actor)
        await sesion.commit()
        return resultado


async def _emitir(engine_app: AsyncEngine, escenario: Escenario) -> uuid.UUID:
    async def emitir(sesion: AsyncSession, actor: Usuario) -> uuid.UUID:
        presupuesto, _ = await presupuestos.emit_presupuesto(
            sesion, _datos(escenario), actor=actor, origen=ORIGEN, clave=uuid.uuid4()
        )
        return presupuesto.id

    return await _en_sesion(engine_app, escenario, emitir)


def _convertir(presupuesto_id: uuid.UUID) -> Callable[[AsyncSession, Usuario], Awaitable[Any]]:
    return lambda sesion, actor: conversion.create_borrador_conversion(
        sesion, presupuesto_id, actor=actor, origen=ORIGEN
    )


def _anular_servicio(
    presupuesto_id: uuid.UUID, clave: uuid.UUID | None = None
) -> Callable[[AsyncSession, Usuario], Awaitable[Any]]:
    return lambda sesion, actor: presupuestos.annul_presupuesto(
        sesion,
        presupuesto_id,
        motivo_texto="Rechazado",
        actor=actor,
        origen=ORIGEN,
        clave=clave or uuid.uuid4(),
    )


def _modificar_servicio(
    escenario: Escenario, presupuesto_id: uuid.UUID, clave: uuid.UUID | None = None
) -> Callable[[AsyncSession, Usuario], Awaitable[Any]]:
    return lambda sesion, actor: presupuestos.modify_presupuesto(
        sesion,
        presupuesto_id,
        _datos(escenario, dias=60),
        motivo_texto=MOTIVO,
        actor=actor,
        origen=ORIGEN,
        clave=clave or uuid.uuid4(),
    )


async def _estado(engine_app: AsyncEngine) -> tuple[int, int, int]:
    """Borradores de factura, cierres y último número PRE."""
    async with AsyncSession(engine_app) as sesion:
        return (
            await _cuenta(sesion, BorradorFactura),
            await _cuenta(sesion, CierrePresupuesto),
            await _contador(sesion, Serie.PRESUPUESTO),
        )


async def test_doble_envio_simultaneo_con_la_misma_clave(
    engine_app: AsyncEngine, escenario: Escenario
) -> None:
    original = await _emitir(engine_app, escenario)
    otro = await _emitir(engine_app, escenario)
    clave_modificar, clave_anular = uuid.uuid4(), uuid.uuid4()

    modificaciones = await asyncio.gather(
        *(
            _en_sesion(
                engine_app, escenario, _modificar_servicio(escenario, original, clave_modificar)
            )
            for _ in range(5)
        )
    )
    anulaciones = await asyncio.gather(
        *(_en_sesion(engine_app, escenario, _anular_servicio(otro, clave_anular)) for _ in range(5))
    )

    assert len({nuevo.id for nuevo, _ in modificaciones}) == 1
    assert sum(creado for _, creado in modificaciones) == 1
    assert sum(creado for _, creado in anulaciones) == 1
    assert await _estado(engine_app) == (0, 2, 3)  # 2 cierres; PRE: 2 emitidos + 1 nuevo


@pytest.mark.parametrize("cierre", ["anulacion", "modificacion"])
async def test_carrera_entre_convertir_y_cerrar_solo_una_tiene_efecto(
    engine_app: AsyncEngine, escenario: Escenario, cierre: str
) -> None:
    rondas = 6
    ganadas: dict[str, int] = {"conversion": 0, "cierre": 0}
    for _ in range(rondas):
        presupuesto_id = await _emitir(engine_app, escenario)
        cerrar = (
            _anular_servicio(presupuesto_id)
            if cierre == "anulacion"
            else _modificar_servicio(escenario, presupuesto_id)
        )
        resultados: list[object] = list(
            await asyncio.gather(
                _en_sesion(engine_app, escenario, _convertir(presupuesto_id)),
                _en_sesion(engine_app, escenario, cerrar),
                return_exceptions=True,
            )
        )
        convertir, cerrado = resultados
        perdedoras = [r for r in (convertir, cerrado) if isinstance(r, BaseException)]
        assert len(perdedoras) == 1, (convertir, cerrado)
        assert isinstance(perdedoras[0], PresupuestoNoModificable)
        ganadas["cierre" if isinstance(convertir, BaseException) else "conversion"] += 1

    borradores, cierres, ultimo_pre = await _estado(engine_app)
    assert borradores == ganadas["conversion"]
    assert cierres == ganadas["cierre"]
    # Una modificación perdedora no consume número: solo los emitidos y los nuevos que ganaron
    nuevos = ganadas["cierre"] if cierre == "modificacion" else 0
    assert ultimo_pre == rondas + nuevos

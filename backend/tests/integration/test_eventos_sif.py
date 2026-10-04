"""⚖️ US2 de 004 — Registro de eventos (FR-012 a FR-015; Orden, art. 9; research R-7).

Constitución VII (2.4.0): cada evento se encadena con el anterior, lleva la huella de F-2 §3.c, se
firma, cumple `EventosSIF.xsd` y se genera en su propia transacción, sin huecos aunque lleguen a
la vez.
"""

import asyncio
import logging
import uuid
from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest
from lxml import etree
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession

from app.core.config import get_settings
from app.core.http import Origen
from app.core.security import hash_password
from app.core.tiempo import hoy
from app.domain.huella import CamposHuellaEvento, compute_huella
from app.domain.tipos import Rol, TipoEventoSif
from app.domain.xml_registro import NS_EVENTOS
from app.models import RegistroEvento, Usuario
from app.services import emision, eventos_sif, firma
from app.services.eventos_sif import NuevoEvento
from tests.integration.facturacion_datos import (
    configurar_facturacion,
    crear_cliente,
    limpiar_facturacion_confirmada,
)

ORIGEN = Origen(ip=None, agente="pytest")


async def _eventos(db: AsyncSession) -> list[RegistroEvento]:
    return list(
        (await db.execute(select(RegistroEvento).order_by(RegistroEvento.secuencia))).scalars()
    )


def _comprobar(evento: RegistroEvento) -> None:
    """Válido contra F-17, firmado con el certificado guardado y con su huella."""
    raiz = etree.fromstring(evento.xml_firmado)
    firma.validar(raiz, firma.Esquema.EVENTOS)
    verificada = firma.verificar(
        evento.xml_firmado, en=datetime.fromisoformat(evento.fecha_hora_huso_gen)
    )
    assert verificada.huella == evento.certificado_huella
    assert eventos_sif.recompute_huella(evento) == evento.huella
    huella = raiz.find(f"{{{NS_EVENTOS}}}Evento/{{{NS_EVENTOS}}}HuellaEvento")
    assert huella is not None
    assert huella.text == evento.huella


async def test_el_primer_evento_se_firma_y_lleva_la_huella_de_f2(db: AsyncSession) -> None:
    evento = await eventos_sif.record_evento(db, NuevoEvento(TipoEventoSif.INICIO))

    assert evento is not None
    assert evento.secuencia == 1
    assert evento.primer_evento
    assert evento.contenido["Evento"]["Encadenamiento"] == {"PrimerEvento": "S"}
    _comprobar(evento)
    ajustes = get_settings()
    # Sin emisor configurado, el obligado es el productor (uso propio).
    esperada = CamposHuellaEvento(
        nif_sistema=ajustes.sif_productor_nif,
        id_otro_sistema="",
        id_sistema=ajustes.sif_id_sistema,
        version="0.4.0",
        numero_instalacion=ajustes.sif_numero_instalacion,
        nif_obligado=ajustes.sif_productor_nif,
        tipo_evento="01",
        huella_anterior="",
        fecha_hora_huso_gen=evento.fecha_hora_huso_gen,
    )
    assert evento.huella == compute_huella(esperada.cadena())


async def test_cada_evento_encadena_con_el_anterior_y_el_obligado_es_el_emisor(
    db: AsyncSession,
) -> None:
    primero = await eventos_sif.record_evento(db, NuevoEvento(TipoEventoSif.INICIO))
    await configurar_facturacion(db)

    segundo = await eventos_sif.record_evento(
        db, NuevoEvento(TipoEventoSif.FIN, otros_datos=eventos_sif.TEXTO_PARADA)
    )

    assert primero is not None
    assert segundo is not None
    assert segundo.secuencia == primero.secuencia + 1
    assert not segundo.primer_evento
    assert segundo.huella_anterior == primero.huella
    assert segundo.contenido["Evento"]["Encadenamiento"] == {
        "EventoAnterior": {
            "TipoEvento": "01",
            "FechaHoraHusoGenEvento": primero.fecha_hora_huso_gen,
            "HuellaEvento": primero.huella,
        }
    }
    assert segundo.contenido["Evento"]["ObligadoEmision"] == {
        "NombreRazon": "Joyería Blanco, S.L.",
        "NIF": "B12345674",
    }
    assert segundo.contenido["Evento"]["OtrosDatosEvento"] == eventos_sif.TEXTO_PARADA
    _comprobar(segundo)


async def test_el_evento_se_conserva_aunque_se_deshaga_quien_lo_pidio(
    conexion: AsyncConnection,
    conexion_owner: AsyncConnection,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R-7: el evento va en otra sesión y otra transacción, no en la de la operación."""
    monkeypatch.setattr(
        eventos_sif,
        "abrir_sesion",
        lambda _origen: AsyncSession(
            bind=conexion, join_transaction_mode="create_savepoint", expire_on_commit=False
        ),
    )
    operacion = AsyncSession(bind=conexion_owner, expire_on_commit=False)
    async with conexion_owner.begin_nested() as transaccion:
        await eventos_sif.record_evento(operacion, NuevoEvento(TipoEventoSif.INICIO))
        await transaccion.rollback()  # la operación falla y se deshace

    [evento] = await _eventos(db)
    assert evento.tipo_evento == "01"


@pytest.fixture
def sin_certificado(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    monkeypatch.setenv("CERTIFICADO_RUTA", str(tmp_path / "no-existe.p12"))
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


@pytest.mark.usefixtures("sin_certificado")
async def test_sin_certificado_no_se_genera_y_queda_un_aviso(
    db: AsyncSession, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="app.services.eventos_sif"):
        evento = await eventos_sif.record_evento(db, NuevoEvento(TipoEventoSif.INICIO))

    assert evento is None
    assert await _eventos(db) == []
    [aviso] = [r for r in caplog.records if r.name == "app.services.eventos_sif"]
    assert aviso.getMessage() == "Evento del sistema sin generar: certificado no utilizable"
    assert aviso.__dict__["motivo"] == "no_instalado"


async def test_si_el_ultimo_evento_esta_alterado_se_registra_la_anomalia_antes(
    conexion_owner: AsyncConnection,
) -> None:
    """FR-015 (art. 9.3, por analogía con el 7.i): la anomalía 01 en eventos, una sola vez."""
    db_owner = AsyncSession(
        bind=conexion_owner, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    primero = await eventos_sif.record_evento(db_owner, NuevoEvento(TipoEventoSif.INICIO))
    assert primero is not None
    await conexion_owner.execute(text("ALTER TABLE registros_evento DISABLE TRIGGER USER"))
    await conexion_owner.execute(
        text(
            "UPDATE registros_evento SET contenido = jsonb_set(contenido, "
            "'{Evento,ObligadoEmision,NIF}', '\"12345678Z\"') WHERE secuencia = 1"
        )
    )
    await conexion_owner.execute(text("ALTER TABLE registros_evento ENABLE TRIGGER USER"))

    pedido = await eventos_sif.record_evento(db_owner, NuevoEvento(TipoEventoSif.FIN))
    otro = await eventos_sif.record_evento(db_owner, NuevoEvento(TipoEventoSif.INICIO))

    cadena = await _eventos(db_owner)
    assert [e.tipo_evento for e in cadena] == ["01", "06", "02", "01"]
    anomalia = cadena[1]
    assert anomalia.tipo_anomalia == "01"
    assert anomalia.secuencia_afectada == 1
    assert anomalia.contenido["Evento"]["DatosPropiosEvento"] == {
        "DeteccionAnomaliasRegEvento": {
            "TipoAnomalia": "01",
            "OtrosDatosAnomalia": "La huella del último evento no coincide con sus datos",
            "RegEventoAnomalo": {
                "TipoEvento": "01",
                "FechaHoraHusoEvento": primero.fecha_hora_huso_gen,
                "HuellaEvento": primero.huella,
            },
        }
    }
    assert pedido is not None
    assert pedido.huella_anterior == anomalia.huella
    assert otro is not None
    _comprobar(anomalia)


# --------------------------------------------------------------------------- resumen (9.2)


async def test_el_resumen_cuenta_eventos_y_registros_desde_el_anterior(db: AsyncSession) -> None:
    admin = Usuario(
        nombre_usuario=f"resumen.{uuid.uuid4().hex[:6]}",
        nombre="Resumen",
        rol=Rol.ADMINISTRADOR.value,
        hash_contrasena=hash_password("x" * 12),
        contrasena_temporal=False,
    )
    db.add(admin)
    await db.flush()
    await eventos_sif.record_evento(db, NuevoEvento(TipoEventoSif.INICIO))
    await configurar_facturacion(db)
    cliente = await crear_cliente(db, admin.id)
    facturas = []
    for precio in ("100", "200"):
        factura, _ = await emision.emit_factura(
            db,
            emision.DatosFactura(
                fecha_expedicion=hoy(),
                cliente_id=cliente.id,
                lineas=(emision.DatosLinea(Decimal(1), "Anillo", Decimal(precio)),),
            ),
            actor=admin,
            origen=ORIGEN,
            clave=uuid.uuid4(),
        )
        facturas.append(factura)
    await emision.anular_factura(
        db, facturas[0].id, motivo_texto="Duplicada", actor=admin, origen=ORIGEN, clave=uuid.uuid4()
    )

    resumen = await eventos_sif.record_resumen(db)
    vacio = await eventos_sif.record_resumen(db)

    assert resumen is not None
    datos: dict[str, Any] = resumen.contenido["Evento"]["DatosPropiosEvento"]["ResumenEventos"]
    assert datos["TipoEvento"] == [{"TipoEvento": "01", "NumeroDeEventos": "1"}]
    assert datos["RegistroFacturacionInicialPeriodo"]["NumSerieFactura"] == facturas[0].num_serie
    assert datos["RegistroFacturacionFinalPeriodo"]["NumSerieFactura"] == facturas[0].num_serie
    assert datos["NumeroDeRegistrosFacturacionAltaGenerados"] == "2"
    assert datos["NumeroDeRegistrosFacturacionAnulacionGenerados"] == "1"
    assert datos["SumaCuotaTotalAlta"] == "63.00"  # 21 + 42
    assert datos["SumaImporteTotalAlta"] == "363.00"
    _comprobar(resumen)
    assert vacio is not None
    datos_vacio = vacio.contenido["Evento"]["DatosPropiosEvento"]["ResumenEventos"]
    assert datos_vacio["TipoEvento"] == [{"TipoEvento": "10", "NumeroDeEventos": "0"}]
    assert "RegistroFacturacionInicialPeriodo" not in datos_vacio
    assert datos_vacio["NumeroDeRegistrosFacturacionAltaGenerados"] == "0"


# ---------------------------------------------------------------- concurrencia (confirmada)


async def test_20_eventos_simultaneos_forman_una_cadena_sin_huecos(
    engine_app: AsyncEngine, engine_owner: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cada evento en su propia conexión, confirmado de verdad, como en producción."""
    monkeypatch.setattr(eventos_sif, "abrir_sesion", lambda _origen: AsyncSession(engine_app))
    try:
        generados = await asyncio.gather(*(eventos_sif.record_resumen(None) for _ in range(20)))
        async with AsyncSession(engine_app) as sesion:
            cadena = await _eventos(sesion)
    finally:
        await limpiar_facturacion_confirmada(engine_owner, clientes=[], usuarios=[])

    assert all(g is not None for g in generados)
    assert [e.secuencia for e in cadena] == list(range(1, 21))
    for anterior, actual in pairwise(cadena):
        assert actual.huella_anterior == anterior.huella
        assert eventos_sif.recompute_huella(actual) == actual.huella

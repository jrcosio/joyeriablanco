"""⚖️ US3 de 004 — Comprobar la integridad y detectar anomalías (FR-017, FR-018, SC-003).

Constitución VII (2.4.0). La cadena se genera con los servicios reales, firmada (No VERI*FACTU), en
una transacción de `jb_owner` que se deshace al final. Cada alteración «por fuera del sistema»
(triggers desactivados como dueño) se detecta con su tipo de anomalía de F-17 (research R-10) y
deja su evento 04 o 06. La comprobación genera además el 03 y el 05 con los recuentos y queda
guardada con su alcance.
"""

import uuid
from collections.abc import AsyncIterator
from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app.core.http import Origen
from app.core.security import hash_password
from app.core.tiempo import ahora, hoy
from app.domain.huella import format_timestamp
from app.domain.tipos import Rol, TipoAnomalia, TipoEventoSif
from app.models import ComprobacionIntegridad, Factura, RegistroEvento, Usuario
from app.services import emision, eventos_sif, integridad
from app.services.eventos_sif import NuevoEvento
from tests.integration.facturacion_datos import configurar_facturacion, crear_cliente

ORIGEN = Origen(ip=None, agente="pytest")
A = TipoAnomalia


@pytest.fixture
async def db_owner(conexion_owner: AsyncConnection) -> AsyncIterator[AsyncSession]:
    session = AsyncSession(
        bind=conexion_owner, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    try:
        yield session
    finally:
        await session.close()


@pytest.fixture
async def cuatro(db_owner: AsyncSession) -> list[Factura]:
    """Un evento de inicio y cuatro altas firmadas (secuencias 1 a 4)."""
    admin = Usuario(
        nombre_usuario=f"integ.{uuid.uuid4().hex[:6]}",
        nombre="Integridad",
        rol=Rol.ADMINISTRADOR.value,
        hash_contrasena=hash_password("x" * 12),
        contrasena_temporal=False,
    )
    db_owner.add(admin)
    await db_owner.flush()
    await configurar_facturacion(db_owner)
    await eventos_sif.record_evento(db_owner, NuevoEvento(TipoEventoSif.INICIO))
    cliente = await crear_cliente(db_owner, admin.id)
    emitidas = []
    for precio in ("100", "200", "300", "400"):
        factura, _ = await emision.emit_factura(
            db_owner,
            emision.DatosFactura(
                fecha_expedicion=hoy(),
                cliente_id=cliente.id,
                lineas=(emision.DatosLinea(Decimal(1), "Anillo", Decimal(precio)),),
            ),
            actor=admin,
            origen=ORIGEN,
            clave=uuid.uuid4(),
        )
        emitidas.append(factura)
    return emitidas


async def _alterar(conn: AsyncConnection, tabla: str, sentencia: str, **params: Any) -> None:
    await conn.execute(text(f"ALTER TABLE {tabla} DISABLE TRIGGER USER"))
    await conn.execute(text(sentencia), params)
    await conn.execute(text(f"ALTER TABLE {tabla} ENABLE TRIGGER USER"))


async def _eventos(db: AsyncSession, tipo: str) -> list[RegistroEvento]:
    resultado = await db.execute(
        select(RegistroEvento)
        .where(RegistroEvento.tipo_evento == tipo)
        .order_by(RegistroEvento.secuencia)
    )
    return list(resultado.scalars())


def _halladas(resultado: integridad.ResultadoIntegridad) -> set[tuple[str, int | None, A]]:
    return {(a.cadena, a.secuencia, a.tipo) for a in resultado.anomalias}


async def test_una_cadena_integra_genera_sus_lanzamientos_y_queda_guardada(
    db_owner: AsyncSession, cuatro: list[Factura]
) -> None:
    resultado = await integridad.verify_chain(db_owner)

    assert resultado.integra, resultado.anomalias
    assert (resultado.registros, resultado.eventos) == (4, 1)
    [facturacion] = await _eventos(db_owner, "03")
    [de_eventos] = await _eventos(db_owner, "05")
    datos = facturacion.contenido["Evento"]["DatosPropiosEvento"]
    assert datos["LanzamientoProcesoDeteccionAnomaliasRegFacturacion"] == {
        "RealizadoProcesoSobreIntegridadHuellasRegFacturacion": "S",
        "NumeroDeRegistrosFacturacionProcesadosSobreIntegridadHuellas": "4",
        "RealizadoProcesoSobreIntegridadFirmasRegFacturacion": "S",
        "NumeroDeRegistrosFacturacionProcesadosSobreIntegridadFirmas": "4",
        "RealizadoProcesoSobreTrazabilidadCadenaRegFacturacion": "S",
        "NumeroDeRegistrosFacturacionProcesadosSobreTrazabilidadCadena": "4",
        "RealizadoProcesoSobreTrazabilidadFechasRegFacturacion": "S",
        "NumeroDeRegistrosFacturacionProcesadosSobreTrazabilidadFechas": "4",
    }
    lanzado = de_eventos.contenido["Evento"]["DatosPropiosEvento"]
    assert (
        lanzado["LanzamientoProcesoDeteccionAnomaliasRegEvento"][
            "NumeroDeRegistrosEventoProcesadosSobreIntegridadFirmas"
        ]
        == "1"
    )
    assert await _eventos(db_owner, "04") == []
    [comprobacion] = list((await db_owner.execute(select(ComprobacionIntegridad))).scalars())
    assert comprobacion.origen == "consola"
    assert (comprobacion.desde_secuencia, comprobacion.hasta_secuencia) == (1, 4)
    assert comprobacion.llega_al_final
    assert (comprobacion.registros, comprobacion.eventos, comprobacion.anomalias) == (4, 1, 0)
    assert comprobacion.evento_lanzamiento_id == facturacion.id


@pytest.mark.parametrize(
    ("sentencia", "esperadas"),
    [
        (
            "UPDATE registros_facturacion SET huella = repeat('A', 64) WHERE secuencia = 2",
            {(2, A.HUELLA), (2, A.HUELLA_NO_ENLAZA_CON_POSTERIOR)},
        ),
        (
            "UPDATE registros_facturacion SET xml_firmado = "
            "replace(convert_from(xml_firmado, 'UTF8'), 'Anillo', 'Pulsera')::bytea "
            "WHERE secuencia = 2",
            {(2, A.FIRMA), (2, A.INTEGRIDAD_OTROS)},
        ),
        (
            "UPDATE registros_facturacion SET contenido = jsonb_set(contenido, "
            "'{DescripcionOperacion}', '\"Otra cosa\"') WHERE secuencia = 2",
            {(2, A.INTEGRIDAD_OTROS)},
        ),
        (
            "DELETE FROM registros_facturacion WHERE secuencia = 2",
            {(1, A.SIN_POSTERIOR), (3, A.SIN_ANTERIOR)},
        ),
        (
            "UPDATE registros_facturacion SET huella_anterior = repeat('0', 64) "
            "WHERE secuencia = 3",
            {(3, A.HUELLA_ANTERIOR_ERRONEA)},
        ),
        (
            "UPDATE registros_facturacion SET fecha_hora_huso_gen = :antes WHERE secuencia = 3",
            {(3, A.FECHA_ANTERIOR_A_LA_PREVIA)},
        ),
        (
            "UPDATE registros_facturacion SET fecha_hora_huso_gen = :futura WHERE secuencia = 4",
            {(4, A.FECHA_FUTURA)},
        ),
    ],
    ids=["huella", "xml-firmado", "contenido", "borrado", "huella-anterior", "fecha", "futura"],
)
async def test_cada_alteracion_de_un_registro_da_su_anomalia_y_su_evento_04(
    conexion_owner: AsyncConnection,
    db_owner: AsyncSession,
    cuatro: list[Factura],
    sentencia: str,
    esperadas: set[tuple[int, A]],
) -> None:
    await _alterar(
        conexion_owner,
        "registros_facturacion",
        sentencia,
        **{
            k: v
            for k, v in {
                "antes": format_timestamp(ahora() - timedelta(days=1)),
                "futura": format_timestamp(ahora() + timedelta(hours=1)),
            }.items()
            if f":{k}" in sentencia
        },
    )
    db_owner.expire_all()

    resultado = await integridad.verify_chain(db_owner)

    halladas = {(s, t) for c, s, t in _halladas(resultado) if c == "facturacion"}
    assert esperadas <= halladas, halladas
    detectadas = {(e.secuencia_afectada, e.tipo_anomalia) for e in await _eventos(db_owner, "04")}
    assert {(s, t.value) for s, t in esperadas} <= detectadas
    [comprobacion] = list((await db_owner.execute(select(ComprobacionIntegridad))).scalars())
    assert comprobacion.anomalias == len(resultado.anomalias)
    assert comprobacion.max_secuencia_anomala == max(s or 0 for s, _ in halladas)


async def test_un_evento_alterado_da_su_anomalia_y_su_evento_06(
    conexion_owner: AsyncConnection, db_owner: AsyncSession, cuatro: list[Factura]
) -> None:
    await eventos_sif.record_evento(
        db_owner, NuevoEvento(TipoEventoSif.FIN)
    )  # el 2, ya no el último
    await _alterar(
        conexion_owner,
        "registros_evento",
        "UPDATE registros_evento SET certificado_huella = repeat('B', 64) WHERE secuencia = 1",
    )
    db_owner.expire_all()

    resultado = await integridad.verify_chain(db_owner)

    assert ("eventos", 1, A.FIRMA) in _halladas(resultado)
    [anomalia] = await _eventos(db_owner, "06")
    assert (anomalia.tipo_anomalia, anomalia.secuencia_afectada) == ("02", 1)
    assert (
        anomalia.contenido["Evento"]["DatosPropiosEvento"]["DeteccionAnomaliasRegEvento"][
            "RegEventoAnomalo"
        ]["TipoEvento"]
        == "01"
    )


async def test_un_rango_parcial_no_llega_al_final(
    db_owner: AsyncSession, cuatro: list[Factura]
) -> None:
    resultado = await integridad.verify_chain(db_owner, desde=2, hasta=3)

    assert resultado.integra
    assert resultado.registros == 2
    [comprobacion] = list((await db_owner.execute(select(ComprobacionIntegridad))).scalars())
    assert (comprobacion.desde_secuencia, comprobacion.hasta_secuencia) == (2, 3)
    assert not comprobacion.llega_al_final


async def test_una_anomalia_ya_registrada_no_se_repite(
    conexion_owner: AsyncConnection, db_owner: AsyncSession, cuatro: list[Factura]
) -> None:
    await _alterar(
        conexion_owner,
        "registros_facturacion",
        "UPDATE registros_facturacion SET huella_anterior = repeat('0', 64) WHERE secuencia = 3",
    )
    db_owner.expire_all()

    primera = await integridad.verify_chain(db_owner)
    segunda = await integridad.verify_chain(db_owner)

    assert _halladas(primera) == _halladas(segunda)
    detectadas = [(e.secuencia_afectada, e.tipo_anomalia) for e in await _eventos(db_owner, "04")]
    assert len(detectadas) == len(set(detectadas))  # una vez cada una
    comprobaciones = list(
        (
            await db_owner.execute(
                select(ComprobacionIntegridad).order_by(ComprobacionIntegridad.lanzada_en)
            )
        ).scalars()
    )
    assert [c.max_secuencia_anomala for c in comprobaciones] == [3, None]  # solo las nuevas

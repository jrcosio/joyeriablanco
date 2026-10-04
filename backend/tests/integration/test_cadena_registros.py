"""⚖️ Test obligatorio (constitución VII): encadenamiento de los registros en la BD (FR-029, R-6).

- El trigger `validar_encadenamiento` impone una cadena lineal: primer registro con secuencia 1,
  y cada uno siguiente con secuencia + 1 y la huella del último como huella anterior.
- `services/cadena` encadena altas y anulaciones y hace la comprobación previa de F-10, art. 7.i.
"""

import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app.core.errors import CadenaInconsistente
from app.core.http import Origen
from app.core.security import hash_password
from app.core.tiempo import ahora, hoy
from app.domain.tipos import Rol, TipoEvento
from app.models import Factura, RegistroEvento, RegistroFacturacion, Usuario
from app.repositories import registros
from app.services import cadena, emision
from tests.conftest import eventos
from tests.integration.facturacion_datos import configurar_facturacion, crear_cliente
from tests.integration.facturacion_sql import (
    huella_de_prueba,
    insertar_factura,
    insertar_registro,
    insertar_usuario_y_cliente,
)

INTEGRIDAD = "23000"


async def _falla(conn: AsyncConnection, coro: object) -> DBAPIError:
    with pytest.raises(DBAPIError) as info:
        async with conn.begin_nested():
            await coro  # type: ignore[misc]
    return info.value


# ----------------------------------------------------------------- trigger de la BD


async def test_el_primer_registro_debe_tener_secuencia_1_y_marcarse(
    conexion: AsyncConnection,
) -> None:
    usuario, cliente = await insertar_usuario_y_cliente(conexion)
    factura = await insertar_factura(conexion, usuario, cliente, 1)

    error = await _falla(
        conexion,
        insertar_registro(
            conexion, factura, secuencia=2, huella=huella_de_prueba("x"), huella_anterior=None
        ),
    )

    assert "primer registro" in str(error.orig)


async def test_la_cadena_no_admite_saltos_ni_huellas_que_no_encadenan(
    conexion: AsyncConnection,
) -> None:
    usuario, cliente = await insertar_usuario_y_cliente(conexion)
    factura = await insertar_factura(conexion, usuario, cliente, 1)
    h1 = huella_de_prueba("1")
    await insertar_registro(conexion, factura, secuencia=1, huella=h1, huella_anterior=None)

    salto = await _falla(
        conexion,
        insertar_registro(
            conexion, factura, secuencia=3, huella=huella_de_prueba("3"), huella_anterior=h1
        ),
    )
    ajena = await _falla(
        conexion,
        insertar_registro(
            conexion,
            factura,
            secuencia=2,
            huella=huella_de_prueba("2"),
            huella_anterior=huella_de_prueba("otra"),
        ),
    )
    segundo_primero = await _falla(
        conexion,
        insertar_registro(
            conexion, factura, secuencia=2, huella=huella_de_prueba("2b"), huella_anterior=None
        ),
    )

    for error in (salto, ajena, segundo_primero):
        assert getattr(error.orig, "sqlstate", None) == INTEGRIDAD
        assert "no encadena" in str(error.orig)
    await insertar_registro(
        conexion, factura, secuencia=2, huella=huella_de_prueba("2"), huella_anterior=h1
    )


# ---------------------------------------------------------------- services/cadena


async def _factura_con_desglose(conn: AsyncConnection, numero: int) -> uuid.UUID:
    usuario, cliente = await insertar_usuario_y_cliente(conn)
    factura = await insertar_factura(conn, usuario, cliente, numero)
    await conn.execute(
        text(
            "INSERT INTO desgloses_factura (factura_id, orden, tipo_iva, clave_regimen, "
            "calificacion_operacion, base, cuota) VALUES (:f, 1, 21, '01', 'S1', 100, 21)"
        ),
        {"f": factura},
    )
    return factura


@pytest.fixture
async def db_owner(conexion_owner: AsyncConnection) -> AsyncIterator[AsyncSession]:
    session = AsyncSession(
        bind=conexion_owner, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    try:
        yield session
    finally:
        await session.close()


async def test_altas_y_anulaciones_se_encadenan(
    conexion: AsyncConnection, db: AsyncSession
) -> None:
    f1 = await db.get(Factura, await _factura_con_desglose(conexion, 1))
    f2 = await db.get(Factura, await _factura_con_desglose(conexion, 2))
    assert f1 is not None
    assert f2 is not None

    await cadena.lock_and_verify(db, origen=None, actor=None)
    alta1 = await cadena.create_registro_alta(db, f1)
    alta2 = await cadena.create_registro_alta(db, f2)
    anulacion = await cadena.create_registro_anulacion(db, f1, modalidad="verifactu")

    assert [r.secuencia for r in (alta1, alta2, anulacion)] == [1, 2, 3]
    assert alta1.primer_registro
    assert alta1.huella_anterior is None
    assert alta1.contenido["Encadenamiento"] == {"PrimerRegistro": "S"}
    assert alta2.huella_anterior == alta1.huella
    assert anulacion.huella_anterior == alta2.huella
    assert anulacion.contenido["Encadenamiento"]["RegistroAnterior"]["Huella"] == alta2.huella
    for registro in (alta1, alta2, anulacion):
        assert cadena.recompute_huella(registro) == registro.huella
        assert registro.contenido["Huella"] == registro.huella
        assert registro.estado_remision == "pendiente"
        assert registro.modalidad == "verifactu"


async def test_la_hora_de_generacion_va_en_madrid_con_desfase(
    conexion: AsyncConnection, db: AsyncSession
) -> None:
    factura = await db.get(Factura, await _factura_con_desglose(conexion, 1))
    assert factura is not None

    registro = await cadena.create_registro_alta(db, factura)

    momento = datetime.fromisoformat(registro.fecha_hora_huso_gen)
    assert momento.utcoffset() in (timedelta(hours=1), timedelta(hours=2))
    assert abs(momento - ahora()) < timedelta(minutes=1)
    assert len(registro.fecha_hora_huso_gen) == 25


async def test_un_ultimo_registro_alterado_detiene_la_cadena(
    conexion_owner: AsyncConnection, db_owner: AsyncSession
) -> None:
    factura = await db_owner.get(Factura, await _factura_con_desglose(conexion_owner, 1))
    assert factura is not None
    await cadena.create_registro_alta(db_owner, factura)
    # Alteración «por fuera del sistema»: solo posible desactivando los triggers como dueño.
    await conexion_owner.execute(text("ALTER TABLE registros_facturacion DISABLE TRIGGER USER"))
    await conexion_owner.execute(text("UPDATE registros_facturacion SET importe_total = 1"))
    await conexion_owner.execute(text("ALTER TABLE registros_facturacion ENABLE TRIGGER USER"))
    db_owner.expire_all()

    with pytest.raises(CadenaInconsistente):
        await cadena.lock_and_verify(db_owner, origen=None, actor=None)

    avisos = await eventos(db_owner, TipoEvento.CADENA_INCONSISTENTE)
    assert avisos
    assert "huella" in avisos[-1].detalle["motivo"]


async def test_un_ultimo_registro_con_hora_futura_detiene_la_cadena(
    conexion: AsyncConnection, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    factura = await db.get(Factura, await _factura_con_desglose(conexion, 1))
    assert factura is not None
    registro = await cadena.create_registro_alta(db, factura)
    generado = datetime.fromisoformat(registro.fecha_hora_huso_gen)

    monkeypatch.setattr(cadena, "ahora", lambda: generado - timedelta(minutes=2))
    with pytest.raises(CadenaInconsistente):
        await cadena.lock_and_verify(db, origen=None, actor=None)

    monkeypatch.setattr(cadena, "ahora", lambda: generado - timedelta(seconds=30))
    await cadena.lock_and_verify(db, origen=None, actor=None)  # dentro del margen de un minuto


async def test_sin_registros_la_comprobacion_no_bloquea(db: AsyncSession) -> None:
    await cadena.lock_and_verify(db, origen=None, actor=None)

    assert await db.get(RegistroFacturacion, uuid.uuid4()) is None


# --------------------------------------------------- No VERI*FACTU: no se interrumpe (004, R-5)


async def _emitida(db_owner: AsyncSession, admin: Usuario, cliente_id: uuid.UUID) -> Factura:
    factura, _ = await emision.emit_factura(
        db_owner,
        emision.DatosFactura(
            fecha_expedicion=hoy(),
            cliente_id=cliente_id,
            lineas=(emision.DatosLinea(Decimal(1), "Anillo", Decimal(100)),),
        ),
        actor=admin,
        origen=Origen(ip=None, agente="pytest"),
        clave=uuid.uuid4(),
    )
    return factura


@pytest.fixture
async def emisor_no_verifactu(db_owner: AsyncSession) -> tuple[Usuario, uuid.UUID]:
    admin = Usuario(
        nombre_usuario=f"r5.{uuid.uuid4().hex[:6]}",
        nombre="R-5",
        rol=Rol.ADMINISTRADOR.value,
        hash_contrasena=hash_password("x" * 12),
        contrasena_temporal=False,
    )
    db_owner.add(admin)
    await db_owner.flush()
    await configurar_facturacion(db_owner)  # No VERI*FACTU
    cliente = await crear_cliente(db_owner, admin.id)
    return admin, cliente.id


async def test_en_no_verifactu_un_ultimo_registro_alterado_no_impide_emitir(
    conexion_owner: AsyncConnection,
    db_owner: AsyncSession,
    emisor_no_verifactu: tuple[Usuario, uuid.UUID],
) -> None:
    """⚖️ FR-010: se registra el evento 04 y la nueva alta encadena con la huella guardada."""
    admin, cliente_id = emisor_no_verifactu
    await _emitida(db_owner, admin, cliente_id)
    await conexion_owner.execute(text("ALTER TABLE registros_facturacion DISABLE TRIGGER USER"))
    await conexion_owner.execute(text("UPDATE registros_facturacion SET importe_total = 1"))
    await conexion_owner.execute(text("ALTER TABLE registros_facturacion ENABLE TRIGGER USER"))
    db_owner.expire_all()
    await db_owner.refresh(admin)
    [primero] = (await db_owner.execute(select(RegistroFacturacion))).scalars().all()

    segunda = await _emitida(db_owner, admin, cliente_id)

    [alta] = await registros.list_by_factura(db_owner, segunda.id)
    assert alta.huella_anterior == primero.huella
    [anomalia] = (
        (await db_owner.execute(select(RegistroEvento).where(RegistroEvento.tipo_evento == "04")))
        .scalars()
        .all()
    )
    assert (anomalia.tipo_anomalia, anomalia.secuencia_afectada) == ("01", 1)
    assert await eventos(db_owner, TipoEvento.CADENA_INCONSISTENTE)  # el aviso de 002 sigue


async def test_en_no_verifactu_un_ultimo_registro_con_hora_futura_no_impide_emitir(
    db_owner: AsyncSession,
    emisor_no_verifactu: tuple[Usuario, uuid.UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-010 y Orden, art. 7.i: hora del último registro posterior a la actual (anomalía 13)."""
    admin, cliente_id = emisor_no_verifactu
    await _emitida(db_owner, admin, cliente_id)
    [primero] = (await db_owner.execute(select(RegistroFacturacion))).scalars().all()
    generado = datetime.fromisoformat(primero.fecha_hora_huso_gen)
    monkeypatch.setattr(cadena, "ahora", lambda: generado - timedelta(minutes=2))

    await cadena.lock_and_verify(db_owner, origen=None, actor=None)

    [anomalia] = (
        (await db_owner.execute(select(RegistroEvento).where(RegistroEvento.tipo_evento == "04")))
        .scalars()
        .all()
    )
    assert (anomalia.tipo_anomalia, anomalia.secuencia_afectada) == ("13", 1)

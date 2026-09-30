"""Comprobación de integridad de la cadena y de los documentos (US6; FR-031, SC-004).

La cadena se genera con los servicios reales (emisiones y correcciones) en una transacción de
`jb_owner` que se deshace al final. Las alteraciones reproducen lo único que podría hacerse «por
fuera del sistema»: desactivar los triggers como dueño y hacer `UPDATE` (research R-8). Cada una
se detecta y se señala el registro afectado.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession
from typer.testing import CliRunner

from app.cli import app as cli
from app.core.http import Origen
from app.core.security import hash_password
from app.core.tiempo import hoy
from app.domain.tipos import CausaRectificacion, MotivoModificacion, Rol, TipoEvento
from app.models import Factura, Usuario
from app.services import emision, integridad
from tests.conftest import eventos
from tests.integration.facturacion_datos import configurar_facturacion, crear_cliente

ORIGEN = Origen(ip=None, agente="pytest")


@pytest.fixture
async def db_owner(conexion_owner: AsyncConnection) -> AsyncIterator[AsyncSession]:
    session = AsyncSession(
        bind=conexion_owner, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    try:
        yield session
    finally:
        await session.close()


@dataclass(frozen=True, slots=True)
class Cadena:
    """Registros: 1 alta de A, 2 alta de B, 3 anulación de A, 4 alta de la REC de B, 5 alta de
    la exenta (oro de inversión, R-21), 6 alta de A2, con IVA, y 7 alta de su REC exenta
    (US5-9). Mezcla facturas sujetas y exentas (SC-013)."""

    a: Factura
    b: Factura
    rec: Factura
    exenta: Factura
    rec_exenta: Factura


@pytest.fixture
async def cadena_generada(db_owner: AsyncSession) -> Cadena:
    admin = Usuario(
        nombre_usuario=f"verif.{uuid.uuid4().hex[:6]}",
        nombre="Verificación",
        rol=Rol.ADMINISTRADOR.value,
        hash_contrasena=hash_password("x" * 12),
        contrasena_temporal=False,
    )
    db_owner.add(admin)
    await db_owner.flush()
    await configurar_facturacion(db_owner)
    cliente = await crear_cliente(db_owner, admin.id)
    await db_owner.refresh(cliente, ["provincia"])

    async def emitir(precio: str, *, oro_inversion: bool = False) -> Factura:
        factura, _ = await emision.emit_factura(
            db_owner,
            emision.DatosFactura(
                fecha_expedicion=hoy(),
                cliente_id=cliente.id,
                lineas=(
                    emision.DatosLinea(Decimal(1), "Anillo", Decimal(precio)),
                    emision.DatosLinea(Decimal(2), "Ajuste", Decimal(45)),
                ),
                oro_inversion=oro_inversion,
            ),
            actor=admin,
            origen=ORIGEN,
            clave=uuid.uuid4(),
        )
        return factura

    a = await emitir("1200")
    b = await emitir("800")
    await emision.anular_factura(
        db_owner, a.id, motivo_texto="Duplicada", actor=admin, origen=ORIGEN, clave=uuid.uuid4()
    )
    rec, _ = await emision.modify_factura(
        db_owner,
        b.id,
        emision.DatosModificacion(
            motivo=MotivoModificacion.FACTURA_ENTREGADA,
            causa=CausaRectificacion.ERROR_DATOS,
            motivo_texto="Precio",
            cliente_id=cliente.id,
            lineas=(emision.DatosLinea(Decimal(1), "Anillo", Decimal(700)),),
        ),
        actor=admin,
        origen=ORIGEN,
        clave=uuid.uuid4(),
    )
    exenta = await emitir("7450", oro_inversion=True)
    a2 = await emitir("3700")
    rec_exenta, _ = await emision.modify_factura(
        db_owner,
        a2.id,
        emision.DatosModificacion(
            motivo=MotivoModificacion.FACTURA_ENTREGADA,
            causa=CausaRectificacion.DEVOLUCION_O_PRECIO,
            motivo_texto="IVA mal aplicado: oro de inversión",
            cliente_id=cliente.id,
            lineas=(emision.DatosLinea(Decimal(1), "Lingote de oro 50 g", Decimal(3700)),),
            oro_inversion=True,
        ),
        actor=admin,
        origen=ORIGEN,
        clave=uuid.uuid4(),
    )
    return Cadena(a=a, b=b, rec=rec, exenta=exenta, rec_exenta=rec_exenta)


async def _alterar(conn: AsyncConnection, tabla: str, sentencia: str, **params: object) -> None:
    """Alteración «por fuera del sistema»: solo posible desactivando los triggers como dueño."""
    await conn.execute(text(f"ALTER TABLE {tabla} DISABLE TRIGGER USER"))
    await conn.execute(text(sentencia), params)
    await conn.execute(text(f"ALTER TABLE {tabla} ENABLE TRIGGER USER"))


async def test_una_cadena_sin_alterar_es_integra(
    db_owner: AsyncSession, cadena_generada: Cadena
) -> None:
    resultado = await integridad.verify_chain(db_owner)

    assert resultado.integra
    assert resultado.registros == 7
    [evento] = await eventos(db_owner, TipoEvento.CADENA_VERIFICADA)
    assert evento.detalle == {"registros": 7}
    assert evento.actor_nombre_usuario == "consola"


@pytest.mark.parametrize(
    ("tabla", "sentencia", "factura", "secuencia", "motivo"),
    [
        (
            "registros_facturacion",
            "UPDATE registros_facturacion SET cuota_total = cuota_total + 1 WHERE secuencia = 2",
            "b",
            2,
            "huella",
        ),
        (
            "lineas_factura",
            "UPDATE lineas_factura SET precio_unitario = 999 WHERE factura_id = :f AND orden = 1",
            "a",
            1,
            "línea 1",
        ),
        (
            "desgloses_factura",
            "UPDATE desgloses_factura SET base = base + 1 WHERE factura_id = :f",
            "b",
            2,
            "contenido",
        ),
        (
            "registros_facturacion",
            "UPDATE registros_facturacion SET contenido = jsonb_set(contenido, "
            "'{DescripcionOperacion}', '\"Otra cosa\"') WHERE secuencia = 4",
            "rec",
            4,
            "contenido",
        ),
        (
            "facturas",
            "UPDATE facturas SET dest_nombre = 'Otra persona' WHERE id = :f",
            "rec",
            4,
            "contenido",
        ),
        (
            # El CHECK de la BD ya exige base + cuota = total: se alteran juntos.
            "facturas",
            "UPDATE facturas SET cuota_total = cuota_total + 1, importe_total = importe_total + 1 "
            "WHERE id = :f",
            "a",
            1,
            "cuota_total",
        ),
    ],
    ids=["campo-de-la-huella", "linea", "desglose", "contenido", "destinatario", "total"],
)
async def test_cada_alteracion_se_detecta_y_se_senala_el_registro(
    conexion_owner: AsyncConnection,
    db_owner: AsyncSession,
    cadena_generada: Cadena,
    tabla: str,
    sentencia: str,
    factura: str,
    secuencia: int,
    motivo: str,
) -> None:
    await _alteracion_detectada(
        conexion_owner, db_owner, cadena_generada, tabla, sentencia, factura, secuencia, motivo
    )


@pytest.mark.parametrize(
    ("tabla", "sentencia", "factura", "secuencia", "motivo"),
    [
        (
            "desgloses_factura",
            "UPDATE desgloses_factura SET base = base + 1 WHERE factura_id = :f",
            "exenta",
            5,
            "contenido",
        ),
        (
            # Convertir el detalle exento en sujeto: el contenido del registro deja de cuadrar.
            "desgloses_factura",
            "UPDATE desgloses_factura SET operacion_exenta = NULL, calificacion_operacion = 'S1', "
            "tipo_iva = 0, clave_regimen = '01' WHERE factura_id = :f",
            "exenta",
            5,
            "contenido",
        ),
        (
            "lineas_factura",
            "UPDATE lineas_factura SET tipo_iva = 21 WHERE factura_id = :f AND orden = 1",
            "rec_exenta",
            7,
            "tipo",
        ),
    ],
    ids=["base-exenta", "exento-a-sujeto", "linea-exenta-con-tipo"],
)
async def test_las_alteraciones_de_una_factura_exenta_se_detectan(
    conexion_owner: AsyncConnection,
    db_owner: AsyncSession,
    cadena_generada: Cadena,
    tabla: str,
    sentencia: str,
    factura: str,
    secuencia: int,
    motivo: str,
) -> None:
    await _alteracion_detectada(
        conexion_owner, db_owner, cadena_generada, tabla, sentencia, factura, secuencia, motivo
    )


async def _alteracion_detectada(
    conexion_owner: AsyncConnection,
    db_owner: AsyncSession,
    cadena_generada: Cadena,
    tabla: str,
    sentencia: str,
    factura: str,
    secuencia: int,
    motivo: str,
) -> None:
    afectada: Factura = getattr(cadena_generada, factura)
    num_serie = afectada.num_serie
    await _alterar(conexion_owner, tabla, sentencia, f=afectada.id)
    db_owner.expire_all()

    resultado = await integridad.verify_chain(db_owner)

    assert not resultado.integra
    assert resultado.discrepancia is not None
    assert resultado.discrepancia.secuencia == secuencia
    assert resultado.discrepancia.num_serie == num_serie
    assert motivo in resultado.discrepancia.motivo
    [aviso] = await eventos(db_owner, TipoEvento.CADENA_INCONSISTENTE)
    assert aviso.detalle["secuencia"] == secuencia
    assert aviso.detalle["momento"] == "verificacion"


async def test_un_registro_intercalado_rompe_el_encadenamiento(
    conexion_owner: AsyncConnection, db_owner: AsyncSession, cadena_generada: Cadena
) -> None:
    await _alterar(
        conexion_owner,
        "registros_facturacion",
        "UPDATE registros_facturacion SET huella_anterior = repeat('0', 64) WHERE secuencia = 3",
    )
    db_owner.expire_all()

    resultado = await integridad.verify_chain(db_owner)

    assert resultado.discrepancia is not None
    assert resultado.discrepancia.secuencia == 3
    assert "encadena" in resultado.discrepancia.motivo


# ------------------------------------------------------------------------------------ CLI


async def test_la_cli_informa_y_devuelve_el_codigo() -> None:
    # La BD de test no tiene registros confirmados: la cadena vacía es íntegra.
    resultado = await asyncio.to_thread(CliRunner().invoke, cli, ["verificar-cadena"])

    assert resultado.exit_code == 0, resultado.output
    assert "Cadena íntegra (0 registros)." in resultado.output


async def test_la_cli_senala_la_discrepancia_con_codigo_1(monkeypatch: pytest.MonkeyPatch) -> None:
    async def inconsistente(*_: object, **__: object) -> integridad.ResultadoIntegridad:
        return integridad.ResultadoIntegridad(
            registros=4,
            discrepancia=integridad.Discrepancia(2, "FAC-2026-0002", "la huella no coincide"),
        )

    monkeypatch.setattr(integridad, "verify_chain", inconsistente)
    resultado = await asyncio.to_thread(CliRunner().invoke, cli, ["verificar-cadena"])

    assert resultado.exit_code == 1
    assert "registro nº 2 (FAC-2026-0002): la huella no coincide" in resultado.output

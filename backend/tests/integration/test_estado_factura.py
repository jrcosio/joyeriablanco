"""Estado derivado de una factura (research R-8, R-12; FR-048): una sola regla, tres lecturas.

La función SQL `estado_factura()`, la vista `v_listado_facturas` y el detalle del servicio dan el
mismo estado, y el trigger `validar_correccion` solo deja corregir las vigentes, en todos los casos:
anulada, rectificada, rectificativa anulada que reactiva la original y rectificativa de una
rectificativa.
"""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.http import Origen
from app.core.tiempo import hoy
from app.domain.tipos import CausaRectificacion, EstadoFactura, MotivoModificacion
from app.models import Cliente, Factura, Usuario
from app.repositories.facturas import v_listado
from app.services import emision
from app.services import facturas as servicio
from tests.conftest import CrearUsuario
from tests.integration.facturacion_datos import configurar_facturacion, crear_cliente
from tests.integration.facturacion_sql import PRIVILEGIO_INSUFICIENTE

ORIGEN = Origen(ip=None, agente="pytest")
LINEA = (emision.DatosLinea(Decimal(1), "Anillo", Decimal(100)),)
DESCUENTO = (emision.DatosLinea(Decimal(1), "Anillo", Decimal(80)),)


@pytest.fixture
async def admin(crear_usuario: CrearUsuario) -> Usuario:
    return await crear_usuario("admin.estado")


@pytest.fixture
async def maria(db: AsyncSession, admin: Usuario) -> Cliente:
    await configurar_facturacion(db)
    return await crear_cliente(db, admin.id)


async def _emitir(db: AsyncSession, admin: Usuario, cliente: Cliente) -> Factura:
    factura, _ = await emision.emit_factura(
        db,
        emision.DatosFactura(fecha_expedicion=hoy(), cliente_id=cliente.id, lineas=LINEA),
        actor=admin,
        origen=ORIGEN,
        clave=uuid.uuid4(),
    )
    return factura


async def _rectificar(
    db: AsyncSession,
    admin: Usuario,
    cliente: Cliente,
    factura: Factura,
    lineas: tuple[emision.DatosLinea, ...] = (),
) -> Factura:
    """Rectificativa R1: devolución total (sin líneas) o con las líneas dadas."""
    nueva, _ = await emision.modify_factura(
        db,
        factura.id,
        emision.DatosModificacion(
            motivo=MotivoModificacion.FACTURA_ENTREGADA,
            causa=CausaRectificacion.DEVOLUCION_O_PRECIO,
            motivo_texto="Devolución",
            cliente_id=cliente.id,
            lineas=lineas,
        ),
        actor=admin,
        origen=ORIGEN,
        clave=uuid.uuid4(),
    )
    return nueva


async def _anular(db: AsyncSession, admin: Usuario, factura: Factura) -> None:
    await emision.anular_factura(
        db, factura.id, motivo_texto="Error", actor=admin, origen=ORIGEN, clave=uuid.uuid4()
    )


async def _estados(db: AsyncSession, factura: Factura) -> set[EstadoFactura]:
    """El estado según la función, la vista y el detalle del servicio."""
    funcion = await db.scalar(select(func.estado_factura(factura.id)))
    vista = await db.scalar(select(v_listado.c.estado).where(v_listado.c.id == factura.id))
    detalle = (await servicio.get_factura(db, factura.id)).estado
    return {EstadoFactura(str(funcion)), EstadoFactura(str(vista)), detalle}


async def _rechazo_del_trigger(
    db: AsyncSession, admin: Usuario, factura: Factura, comodin: Factura
) -> str | None:
    """Intenta en SQL una rectificación de `factura` y la deshace. Devuelve el SQLSTATE del
    rechazo, o `None` si se admitió. `comodin` hace de factura nueva: una que no lo es de nadie."""
    conn = await db.connection()
    try:
        async with conn.begin_nested() as intento:
            await conn.execute(
                text(
                    "INSERT INTO correcciones_factura (factura_id, tipo, motivo, motivo_texto, "
                    "factura_nueva_id, creada_por_id) VALUES (:f, 'rectificacion_sustitucion', "
                    "'factura_entregada', 'Prueba', :n, :u)"
                ),
                {"f": factura.id, "n": comodin.id, "u": admin.id},
            )
            await intento.rollback()
    except DBAPIError as error:
        return str(getattr(error.orig, "sqlstate", ""))
    return None


async def _comprobar(
    db: AsyncSession, admin: Usuario, factura: Factura, esperado: EstadoFactura
) -> None:
    assert await _estados(db, factura) == {esperado}, factura.num_serie
    comodin = await _emitir(db, admin, await crear_cliente(db, admin.id, numero=_nif()))
    rechazo = await _rechazo_del_trigger(db, admin, factura, comodin)
    esperado_rechazo = None if esperado is EstadoFactura.VIGENTE else PRIVILEGIO_INSUFICIENTE
    assert rechazo == esperado_rechazo, factura.num_serie


_CONTADOR = iter(range(10_000_000, 99_999_999))


def _nif() -> str:
    numero = next(_CONTADOR)
    return f"{numero:08d}{'TRWAGMYFPDXBNJZSQVHLCKE'[numero % 23]}"


async def test_vigente_y_anulada(db: AsyncSession, admin: Usuario, maria: Cliente) -> None:
    factura = await _emitir(db, admin, maria)
    await _comprobar(db, admin, factura, EstadoFactura.VIGENTE)

    await _anular(db, admin, factura)

    await _comprobar(db, admin, factura, EstadoFactura.ANULADA)


async def test_rectificada_y_rectificativa_de_una_rectificativa(
    db: AsyncSession, admin: Usuario, maria: Cliente
) -> None:
    original = await _emitir(db, admin, maria)
    primera = await _rectificar(db, admin, maria, original, DESCUENTO)
    await _comprobar(db, admin, original, EstadoFactura.RECTIFICADA)
    await _comprobar(db, admin, primera, EstadoFactura.VIGENTE)

    segunda = await _rectificar(db, admin, maria, primera)

    await _comprobar(db, admin, original, EstadoFactura.RECTIFICADA)
    await _comprobar(db, admin, primera, EstadoFactura.RECTIFICADA)
    await _comprobar(db, admin, segunda, EstadoFactura.VIGENTE)


async def test_anular_la_rectificativa_reactiva_la_original(
    db: AsyncSession, admin: Usuario, maria: Cliente
) -> None:
    original = await _emitir(db, admin, maria)
    rectificativa = await _rectificar(db, admin, maria, original)

    await _anular(db, admin, rectificativa)

    await _comprobar(db, admin, rectificativa, EstadoFactura.ANULADA)
    await _comprobar(db, admin, original, EstadoFactura.VIGENTE)
    # La original, de nuevo vigente, se puede volver a rectificar y queda rectificada otra vez.
    otra = await _rectificar(db, admin, maria, original)
    await _comprobar(db, admin, original, EstadoFactura.RECTIFICADA)
    await _comprobar(db, admin, otra, EstadoFactura.VIGENTE)


async def test_anular_la_segunda_rectificativa_reactiva_solo_la_primera(
    db: AsyncSession, admin: Usuario, maria: Cliente
) -> None:
    original = await _emitir(db, admin, maria)
    primera = await _rectificar(db, admin, maria, original, DESCUENTO)
    segunda = await _rectificar(db, admin, maria, primera)

    await _anular(db, admin, segunda)

    await _comprobar(db, admin, primera, EstadoFactura.VIGENTE)
    await _comprobar(db, admin, original, EstadoFactura.RECTIFICADA)

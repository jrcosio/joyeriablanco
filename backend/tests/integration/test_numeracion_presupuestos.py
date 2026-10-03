"""⚖️ Test obligatorio (constitución VII): numeración PRE bajo concurrencia (005; FR-002, SC-002).

Sesiones reales que confirman, como `test_numeracion_concurrencia.py` de 002: 200 emisiones
repartidas en 10 sesiones simultáneas dan los números 1..200 sin huecos ni duplicados. Con
facturas emitiéndose a la vez, las dos series son independientes. Una emisión que falla no
consume número, y la misma clave de idempotencia en paralelo da un solo presupuesto.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.http import Origen
from app.core.security import hash_password
from app.core.tiempo import hoy
from app.domain.tipos import Rol
from app.models import Factura, Presupuesto, RegistroFacturacion, Usuario
from app.repositories import presupuestos as repo_presupuestos
from app.services import contenido, emision, presupuestos
from tests.integration.facturacion_datos import (
    configurar_facturacion,
    crear_cliente,
    limpiar_facturacion_confirmada,
)

ORIGEN = Origen(ip=None, agente=None)
SESIONES = 10
POR_SESION = 20
LINEA = (contenido.DatosLinea(Decimal(1), "Anillo", Decimal("100.00")),)


@dataclass(frozen=True, slots=True)
class Escenario:
    usuario_id: uuid.UUID
    cliente_id: uuid.UUID


@pytest.fixture
async def escenario(engine_app: AsyncEngine, engine_owner: AsyncEngine) -> AsyncIterator[Escenario]:
    async with AsyncSession(engine_app, expire_on_commit=False) as sesion:
        assert (await sesion.execute(select(func.count(Presupuesto.id)))).scalar() == 0
        usuario = Usuario(
            nombre_usuario=f"conc.pre.{uuid.uuid4().hex[:6]}",
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
        yield Escenario(usuario_id=usuario.id, cliente_id=cliente.id)
    finally:
        await limpiar_facturacion_confirmada(
            engine_owner, clientes=[cliente.id], usuarios=[usuario.id]
        )


def _datos(escenario: Escenario, fecha: date | None = None) -> presupuestos.DatosPresupuesto:
    fecha = fecha or hoy()
    return presupuestos.DatosPresupuesto(
        fecha=fecha,
        valido_hasta=fecha + timedelta(days=30),
        cliente_id=escenario.cliente_id,
        lineas=LINEA,
    )


async def _emitir(
    engine_app: AsyncEngine,
    escenario: Escenario,
    clave: uuid.UUID | None = None,
    fecha: date | None = None,
) -> Presupuesto:
    async with AsyncSession(engine_app, expire_on_commit=False) as sesion:
        actor = await sesion.get(Usuario, escenario.usuario_id)
        assert actor is not None
        presupuesto, _ = await presupuestos.emit_presupuesto(
            sesion,
            _datos(escenario, fecha),
            actor=actor,
            origen=ORIGEN,
            clave=clave or uuid.uuid4(),
        )
        await sesion.commit()
        return presupuesto


async def _emitir_factura(engine_app: AsyncEngine, escenario: Escenario) -> Factura:
    async with AsyncSession(engine_app, expire_on_commit=False) as sesion:
        actor = await sesion.get(Usuario, escenario.usuario_id)
        assert actor is not None
        factura, _ = await emision.emit_factura(
            sesion,
            emision.DatosFactura(
                fecha_expedicion=hoy(), cliente_id=escenario.cliente_id, lineas=LINEA
            ),
            actor=actor,
            origen=ORIGEN,
            clave=uuid.uuid4(),
        )
        await sesion.commit()
        return factura


async def _numeros(engine_app: AsyncEngine, anio: int) -> list[int]:
    async with AsyncSession(engine_app) as sesion:
        return list(
            (
                await sesion.execute(
                    select(Presupuesto.numero)
                    .where(Presupuesto.anio == anio)
                    .order_by(Presupuesto.numero)
                )
            ).scalars()
        )


async def test_200_emisiones_simultaneas_sin_huecos_ni_duplicados(
    engine_app: AsyncEngine, escenario: Escenario
) -> None:
    async def trabajador() -> list[int]:
        return [(await _emitir(engine_app, escenario)).numero for _ in range(POR_SESION)]

    resultados = await asyncio.gather(*(trabajador() for _ in range(SESIONES)))

    emitidos = sorted(n for lote in resultados for n in lote)
    assert emitidos == list(range(1, SESIONES * POR_SESION + 1))
    assert await _numeros(engine_app, hoy().year) == emitidos


async def test_series_independientes_con_facturas_simultaneas(
    engine_app: AsyncEngine, escenario: Escenario
) -> None:
    async def presupuestos_() -> list[int]:
        return [(await _emitir(engine_app, escenario)).numero for _ in range(15)]

    async def facturas_() -> list[int]:
        return [(await _emitir_factura(engine_app, escenario)).numero for _ in range(15)]

    resultados = await asyncio.gather(presupuestos_(), facturas_(), presupuestos_(), facturas_())

    numeros_pre = sorted(resultados[0] + resultados[2])
    numeros_fac = sorted(resultados[1] + resultados[3])
    assert numeros_pre == list(range(1, 31))
    assert numeros_fac == list(range(1, 31))
    async with AsyncSession(engine_app) as sesion:
        # Solo las facturas generan registros (FR-005).
        assert await sesion.scalar(select(func.count(RegistroFacturacion.id))) == 30


async def test_una_emision_que_falla_no_consume_numero(
    engine_app: AsyncEngine, escenario: Escenario, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _emitir(engine_app, escenario)
    original = repo_presupuestos.insert_emitido

    async def falla(*_: object, **__: object) -> Presupuesto:
        raise RuntimeError("fallo provocado tras asignar el número")

    monkeypatch.setattr(repo_presupuestos, "insert_emitido", falla)
    with pytest.raises(RuntimeError, match="provocado"):
        await _emitir(engine_app, escenario)
    monkeypatch.setattr(repo_presupuestos, "insert_emitido", original)

    siguiente = await _emitir(engine_app, escenario)

    assert siguiente.numero == 2
    assert await _numeros(engine_app, hoy().year) == [1, 2]


async def test_la_misma_clave_en_paralelo_emite_un_solo_presupuesto(
    engine_app: AsyncEngine, escenario: Escenario
) -> None:
    clave = uuid.uuid4()

    emitidos = await asyncio.gather(*(_emitir(engine_app, escenario, clave) for _ in range(5)))

    assert len({p.id for p in emitidos}) == 1
    assert await _numeros(engine_app, hoy().year) == [1]


async def test_el_correlativo_es_por_anio(engine_app: AsyncEngine, escenario: Escenario) -> None:
    anterior = date(hoy().year - 1, 12, 31)
    await _emitir(engine_app, escenario, fecha=anterior)
    await _emitir(engine_app, escenario, fecha=anterior)

    del_anio = await _emitir(engine_app, escenario)

    assert del_anio.num_serie == f"PRE-{hoy().year}-0001"
    assert await _numeros(engine_app, anterior.year) == [1, 2]

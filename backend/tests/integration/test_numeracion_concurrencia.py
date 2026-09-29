"""⚖️ Test obligatorio (constitución VII): numeración correlativa bajo concurrencia (SC-002, R-7).

Sesiones reales que confirman, como en `test_usuarios.py`: 200 emisiones repartidas en 10
sesiones simultáneas producen los números 1..200 sin huecos ni duplicados y una única cadena
lineal de registros. Una emisión que falla no consume número, un ajuste del contador en paralelo
nunca provoca duplicados y la misma clave de idempotencia en paralelo emite una sola factura.
"""

import asyncio
import itertools
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.http import Origen
from app.core.security import hash_password
from app.core.tiempo import hoy
from app.domain.tipos import Rol, Serie
from app.models import Factura, RegistroFacturacion, Usuario
from app.repositories import contadores
from app.schemas.configuracion_facturacion import AjusteContadorEntrada
from app.services import cadena, configuracion_facturacion, emision
from tests.integration.facturacion_datos import (
    configurar_facturacion,
    crear_cliente,
    limpiar_facturacion_confirmada,
)

ORIGEN = Origen(ip=None, agente=None)
SESIONES = 10
POR_SESION = 20


@dataclass(frozen=True, slots=True)
class Escenario:
    usuario_id: uuid.UUID
    cliente_id: uuid.UUID


@pytest.fixture
async def escenario(engine_app: AsyncEngine, engine_owner: AsyncEngine) -> AsyncIterator[Escenario]:
    async with AsyncSession(engine_app, expire_on_commit=False) as sesion:
        assert (await sesion.execute(select(func.count(RegistroFacturacion.id)))).scalar() == 0
        usuario = Usuario(
            nombre_usuario=f"conc.fact.{uuid.uuid4().hex[:6]}",
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


def _datos(escenario: Escenario) -> emision.DatosFactura:
    return emision.DatosFactura(
        fecha_expedicion=hoy(),
        cliente_id=escenario.cliente_id,
        lineas=(
            emision.DatosLinea(
                unidades=Decimal(1), descripcion="Anillo", precio_unitario=Decimal("100.00")
            ),
        ),
    )


async def _emitir(
    engine_app: AsyncEngine, escenario: Escenario, clave: uuid.UUID | None = None
) -> Factura:
    async with AsyncSession(engine_app, expire_on_commit=False) as sesion:
        actor = await sesion.get(Usuario, escenario.usuario_id)
        assert actor is not None
        factura, _ = await emision.emit_factura(
            sesion, _datos(escenario), actor=actor, origen=ORIGEN, clave=clave or uuid.uuid4()
        )
        await sesion.commit()
        return factura


async def _numeros_y_cadena(engine_app: AsyncEngine) -> tuple[list[int], list[RegistroFacturacion]]:
    async with AsyncSession(engine_app) as sesion:
        numeros = list(
            (await sesion.execute(select(Factura.numero).order_by(Factura.numero))).scalars()
        )
        registros = list(
            (
                await sesion.execute(
                    select(RegistroFacturacion).order_by(RegistroFacturacion.secuencia)
                )
            ).scalars()
        )
    return numeros, registros


def _cadena_lineal(registros: list[RegistroFacturacion]) -> None:
    assert [r.secuencia for r in registros] == list(range(1, len(registros) + 1))
    assert registros[0].primer_registro
    for anterior, actual in itertools.pairwise(registros):
        assert actual.huella_anterior == anterior.huella
        assert cadena.recompute_huella(actual) == actual.huella


async def test_200_emisiones_simultaneas_sin_huecos_ni_duplicados(
    engine_app: AsyncEngine, escenario: Escenario
) -> None:
    async def trabajador() -> list[int]:
        return [(await _emitir(engine_app, escenario)).numero for _ in range(POR_SESION)]

    resultados = await asyncio.gather(*(trabajador() for _ in range(SESIONES)))

    emitidos = sorted(n for lote in resultados for n in lote)
    assert emitidos == list(range(1, SESIONES * POR_SESION + 1))
    numeros, registros = await _numeros_y_cadena(engine_app)
    assert numeros == emitidos
    assert len(registros) == SESIONES * POR_SESION
    _cadena_lineal(registros)


async def test_una_emision_que_falla_no_consume_numero(
    engine_app: AsyncEngine, escenario: Escenario, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _emitir(engine_app, escenario)
    original = cadena.create_registro_alta

    async def falla(*_: object, **__: object) -> RegistroFacturacion:
        raise RuntimeError("fallo provocado tras asignar el número")

    monkeypatch.setattr(cadena, "create_registro_alta", falla)
    with pytest.raises(RuntimeError, match="provocado"):
        await _emitir(engine_app, escenario)
    monkeypatch.setattr(cadena, "create_registro_alta", original)

    siguiente = await _emitir(engine_app, escenario)

    assert siguiente.numero == 2
    numeros, registros = await _numeros_y_cadena(engine_app)
    assert numeros == [1, 2]
    _cadena_lineal(registros)


async def test_ajustar_el_contador_en_paralelo_nunca_duplica(
    engine_app: AsyncEngine, escenario: Escenario
) -> None:
    async def ajustar() -> None:
        async with AsyncSession(engine_app, expire_on_commit=False) as sesion:
            actor = await sesion.get(Usuario, escenario.usuario_id)
            assert actor is not None
            await configuracion_facturacion.adjust_counter(
                sesion,
                AjusteContadorEntrada(proximo_numero=500, motivo="Prueba", simular=False),
                actor=actor,
                origen=ORIGEN,
            )
            await sesion.commit()

    async def emitir_varias() -> list[int]:
        return [(await _emitir(engine_app, escenario)).numero for _ in range(10)]

    resultados = await asyncio.gather(emitir_varias(), ajustar(), emitir_varias())

    emitidos = [n for lote in (resultados[0], resultados[2]) for n in lote]
    assert len(set(emitidos)) == len(emitidos) == 20
    async with AsyncSession(engine_app) as sesion:
        assert await contadores.last_used(sesion, Serie.ORDINARIA, hoy().year) >= 499
    _cadena_lineal((await _numeros_y_cadena(engine_app))[1])


async def test_la_misma_clave_en_paralelo_emite_una_sola_factura(
    engine_app: AsyncEngine, escenario: Escenario
) -> None:
    clave = uuid.uuid4()

    facturas = await asyncio.gather(*(_emitir(engine_app, escenario, clave) for _ in range(5)))

    assert len({f.id for f in facturas}) == 1
    numeros, registros = await _numeros_y_cadena(engine_app)
    assert numeros == [1]
    assert len(registros) == 1

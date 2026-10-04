"""US2 de 004 — Inicio, resumen periódico y fin del servicio (FR-012 a, b; FR-013; research R-8).

Con dos procesos (`uvicorn --workers 2`) solo uno genera los eventos del servicio: el que consigue
el cerrojo consultivo de sesión. El cerrojo va en conexiones reales; los eventos, en la transacción
del test (conftest). El reloj se simula para no esperar 6 horas.
"""

from collections.abc import AsyncIterator, Callable
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.tiempo import ahora
from app.models import RegistroEvento
from app.services import eventos_sif
from app.services.eventos_sif import Lider


class Reloj:
    def __init__(self) -> None:
        self.momento = ahora()

    def __call__(self) -> datetime:
        return self.momento


@pytest.fixture
def reloj(monkeypatch: pytest.MonkeyPatch) -> Reloj:
    """La misma hora simulada para decidir el resumen y para fechar los eventos."""
    simulado = Reloj()
    monkeypatch.setattr(eventos_sif, "ahora", simulado)
    return simulado


@pytest.fixture
async def lideres(engine_app: AsyncEngine) -> AsyncIterator[Callable[[Reloj], Lider]]:
    creados: list[Lider] = []

    def _nuevo(reloj: Reloj) -> Lider:
        lider = Lider(engine_app, reloj=reloj)
        creados.append(lider)
        return lider

    yield _nuevo
    for lider in creados:  # que ningún cerrojo quede tomado para otros tests
        await lider.detener()


async def _tipos(db: AsyncSession) -> list[str]:
    resultado = await db.execute(
        select(RegistroEvento.tipo_evento).order_by(RegistroEvento.secuencia)
    )
    return list(resultado.scalars())


async def test_con_dos_procesos_solo_uno_genera_el_inicio(
    db: AsyncSession, lideres: Callable[[Reloj], Lider], reloj: Reloj
) -> None:
    primero, segundo = lideres(reloj), lideres(reloj)

    await primero.tick()
    await segundo.tick()

    assert primero.es_lider
    assert not segundo.es_lider
    assert await _tipos(db) == ["01"]


async def test_cada_6_horas_un_resumen_aunque_no_pase_nada(
    db: AsyncSession, lideres: Callable[[Reloj], Lider], reloj: Reloj
) -> None:
    lider = lideres(reloj)
    await lider.tick()

    reloj.momento += timedelta(hours=5, minutes=59)
    await lider.tick()
    assert await _tipos(db) == ["01"]

    reloj.momento += timedelta(minutes=1)
    await lider.tick()
    await lider.tick()  # el resumen recién hecho cuenta como el último
    assert await _tipos(db) == ["01", "10"]


async def test_al_parar_resumen_y_fin_y_otro_proceso_toma_el_relevo(
    db: AsyncSession, lideres: Callable[[Reloj], Lider], reloj: Reloj
) -> None:
    primero, segundo = lideres(reloj), lideres(reloj)
    await primero.tick()
    await segundo.tick()

    await primero.detener()
    await segundo.tick()

    assert not primero.es_lider
    assert segundo.es_lider
    assert await _tipos(db) == ["01", "10", "02", "01"]


async def test_si_el_lider_cae_sin_parar_otro_genera_su_inicio(
    db: AsyncSession, lideres: Callable[[Reloj], Lider], reloj: Reloj
) -> None:
    primero, segundo = lideres(reloj), lideres(reloj)
    await primero.tick()

    await primero._conexion.close()  # type: ignore[union-attr]  # el proceso muere
    primero._conexion = None
    await segundo.tick()

    assert segundo.es_lider
    assert await _tipos(db) == ["01", "01"]

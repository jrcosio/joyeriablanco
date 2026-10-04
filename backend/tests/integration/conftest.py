"""Fijaciones comunes de los tests de integración."""

import pytest
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app.services import eventos_sif


@pytest.fixture(autouse=True)
def eventos_en_la_transaccion_del_test(
    monkeypatch: pytest.MonkeyPatch, conexion: AsyncConnection
) -> None:
    """Los eventos del sistema se generan en su propia sesión (004, R-7). En los tests esa sesión
    va sobre la conexión de quien los pide, o la del test si no hay nadie (el líder), en modo
    *savepoint*: así se deshacen con el test y no quedan eventos confirmados de verdad."""

    def _abrir(origen: AsyncSession | None) -> AsyncSession:
        enlace = origen.bind if origen is not None else conexion
        return AsyncSession(
            bind=enlace, join_transaction_mode="create_savepoint", expire_on_commit=False
        )

    monkeypatch.setattr(eventos_sif, "abrir_sesion", _abrir)

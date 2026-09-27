"""Infraestructura de tests contra PostgreSQL real (research R-16).

- Base de datos aislada `joyeriablanco_test` del servicio `db` de docker compose.
- Al empezar la sesión se reconstruye el esquema (downgrade base + upgrade head) como jb_owner.
- Cada test corre dentro de una transacción que se revierte al terminar. La API usa sesiones
  sobre la misma conexión en modo *savepoint*, así que sus `commit()` no escapan del test.
- `TEST_DB_NAME`, `TEST_DATABASE_URL_APP` y `TEST_DATABASE_URL_OWNER` permiten apuntar a otra BD
  (por ejemplo, desde dentro del contenedor).
"""

import os

os.environ["ENTORNO"] = "test"
os.environ["DB_NAME"] = os.environ.get("TEST_DB_NAME", "joyeriablanco_test")
os.environ["SESION_COOKIE_SEGURA"] = "true"
os.environ["ORIGEN_PERMITIDO"] = "http://localhost:5173"
for _var in ("APP", "OWNER"):
    if _url := os.environ.get(f"TEST_DATABASE_URL_{_var}"):
        os.environ[f"DATABASE_URL_{_var}"] = _url

from collections.abc import AsyncIterator  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.pool import NullPool  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.db import get_db  # noqa: E402
from app.main import create_app  # noqa: E402

ORIGEN = "http://localhost:5173"
BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def _esquema_limpio() -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.attributes["configurar_logging"] = False
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
async def engine_app() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(get_settings().url_app, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
async def engine_owner() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(get_settings().url_owner, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest.fixture
async def conexion(engine_app: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    """Conexión como jb_app dentro de una transacción que se revierte al final del test."""
    async with engine_app.connect() as conn:
        transaccion = await conn.begin()
        try:
            yield conn
        finally:
            await transaccion.rollback()


@pytest.fixture
async def conexion_owner(engine_owner: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    async with engine_owner.connect() as conn:
        transaccion = await conn.begin()
        try:
            yield conn
        finally:
            await transaccion.rollback()


def _sesion(conn: AsyncConnection) -> AsyncSession:
    return AsyncSession(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)


@pytest.fixture
async def db(conexion: AsyncConnection) -> AsyncIterator[AsyncSession]:
    session = _sesion(conexion)
    try:
        yield session
    finally:
        await session.close()


@pytest.fixture
def app(conexion: AsyncConnection) -> FastAPI:
    aplicacion = create_app()

    async def _get_db() -> AsyncIterator[AsyncSession]:
        async with _sesion(conexion) as session:
            try:
                yield session
                await session.commit()
            except BaseException:
                await session.rollback()
                raise

    aplicacion.dependency_overrides[get_db] = _get_db
    return aplicacion


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="https://testserver",
        headers={"Origin": ORIGEN},
    ) as cliente:
        yield cliente

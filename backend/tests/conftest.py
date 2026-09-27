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
)
from sqlalchemy.pool import NullPool  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.db import build_engine, get_db  # noqa: E402
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
    engine = build_engine(get_settings().url_app, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
async def engine_owner() -> AsyncIterator[AsyncEngine]:
    engine = build_engine(get_settings().url_owner, poolclass=NullPool)
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


# ------------------------------------------------------------------ factorías y utilidades

from collections.abc import Awaitable, Callable  # noqa: E402
from datetime import timedelta  # noqa: E402
from typing import Protocol  # noqa: E402

from fastapi import APIRouter, Depends  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.core.tiempo import ahora  # noqa: E402
from app.domain.tipos import Rol, TipoEvento  # noqa: E402
from app.models import EventoAuditoria, Usuario  # noqa: E402

CONTRASENA_VALIDA = "Cuarzo-Rubí-Esmeralda-42"
_HASH_VALIDO = hash_password(CONTRASENA_VALIDA)


class CrearUsuario(Protocol):
    def __call__(
        self,
        nombre_usuario: str = ...,
        *,
        rol: Rol = ...,
        nombre: str = ...,
        temporal: bool = ...,
        activo: bool = ...,
    ) -> Awaitable[Usuario]: ...


@pytest.fixture
def crear_usuario(db: AsyncSession) -> CrearUsuario:
    async def _crear(
        nombre_usuario: str = "ana.garcia",
        *,
        rol: Rol = Rol.EMPLEADO,
        nombre: str = "Ana García",
        temporal: bool = False,
        activo: bool = True,
    ) -> Usuario:
        usuario = Usuario(
            nombre_usuario=nombre_usuario,
            nombre=nombre,
            rol=rol.value,
            hash_contrasena=_HASH_VALIDO,
            contrasena_temporal=temporal,
            contrasena_temporal_expira_en=ahora() + timedelta(hours=72) if temporal else None,
            activo=activo,
        )
        db.add(usuario)
        await db.commit()
        return usuario

    return _crear


IniciarSesion = Callable[..., Awaitable[str]]


@pytest.fixture
def iniciar_sesion() -> IniciarSesion:
    """Inicia sesión con el cliente dado y devuelve el token CSRF."""

    async def _iniciar(
        cliente: AsyncClient, nombre_usuario: str, contrasena: str = CONTRASENA_VALIDA
    ) -> str:
        respuesta = await cliente.post(
            "/api/v1/sesion", json={"nombre_usuario": nombre_usuario, "contrasena": contrasena}
        )
        assert respuesta.status_code == 200, respuesta.text
        return str(respuesta.json()["csrf_token"])

    return _iniciar


async def eventos(db: AsyncSession, tipo: TipoEvento) -> list[EventoAuditoria]:
    resultado = await db.execute(
        select(EventoAuditoria)
        .where(EventoAuditoria.tipo == tipo.value)
        .order_by(EventoAuditoria.ocurrido_en)
    )
    return list(resultado.scalars())


@pytest.fixture
def ruta_protegida(app: FastAPI) -> None:
    """Añade rutas de prueba protegidas para verificar las puertas comunes (sesión, CSRF...)."""
    from app.api.deps import CurrentSession, get_current_session, require_admin

    router = APIRouter(dependencies=[Depends(get_current_session)])

    @router.get("/_prueba")
    async def _leer(sesion: CurrentSession) -> dict[str, str]:
        return {"usuario": sesion.usuario.nombre_usuario}

    @router.post("/_prueba")
    async def _escribir(sesion: CurrentSession) -> dict[str, str]:
        return {"usuario": sesion.usuario.nombre_usuario}

    @router.get("/_prueba/admin", dependencies=[Depends(require_admin)])
    async def _admin() -> dict[str, bool]:
        return {"admin": True}

    app.include_router(router, prefix="/api/v1")


@pytest.fixture
def otro_cliente(app: FastAPI) -> Callable[[], AsyncClient]:
    """Fábrica de clientes adicionales (otro navegador) sobre la misma app."""

    def _nuevo() -> AsyncClient:
        return AsyncClient(
            transport=ASGITransport(app=app),
            base_url="https://testserver",
            headers={"Origin": ORIGEN},
        )

    return _nuevo

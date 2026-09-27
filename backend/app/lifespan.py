"""Ciclo de vida de la aplicación: tareas de arranque y cierre."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.db import get_engine, get_sessionmaker
from app.services.auth import purge_sessions

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        async with get_sessionmaker()() as session:
            borradas = await purge_sessions(session)
            await session.commit()
        logger.info("Sesiones antiguas purgadas al arrancar", extra={"borradas": borradas})
    except Exception:  # la API arranca aunque la purga falle; se reintenta en el próximo arranque
        logger.warning("No se han podido purgar las sesiones antiguas al arrancar", exc_info=True)
    yield
    await get_engine().dispose()

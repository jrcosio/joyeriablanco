"""Ciclo de vida de la aplicación: tareas de arranque y cierre.

- Al arrancar, purga las sesiones antiguas.
- El líder de los eventos del servicio (004, research R-8): el inicio al arrancar, el resumen cada
  6 horas y, al parar, el resumen y el fin. Nunca impide arrancar ni parar.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.db import get_engine, get_sessionmaker
from app.services.auth import purge_sessions
from app.services.eventos_sif import Lider

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
    lider = Lider(get_engine())
    await lider.iniciar()
    try:
        yield
    finally:
        await lider.detener()
        await get_engine().dispose()

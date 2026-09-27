"""Factoría de la aplicación FastAPI (`uvicorn app.main:create_app --factory`)."""

from fastapi import FastAPI

from app.api import salud
from app.api.v1 import router as v1_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.http import register_middlewares
from app.core.logging import configure_logging
from app.lifespan import lifespan


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    docs = not settings.es_produccion
    app = FastAPI(
        title="Joyería Blanco — API de gestión",
        version="0.1.0",
        docs_url="/api/docs" if docs else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if docs else None,
        lifespan=lifespan,
    )
    register_middlewares(app)
    register_error_handlers(app)
    app.include_router(salud.router, prefix="/api")
    app.include_router(v1_router, prefix="/api/v1")
    return app

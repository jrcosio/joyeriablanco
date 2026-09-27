"""Comprobación pública de estado: solo indica si el servicio está operativo (FR-049)."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import ProblemaError

router = APIRouter(tags=["salud"])


class SaludSalida(BaseModel):
    estado: Literal["ok"]


class ServicioNoDisponible(ProblemaError):
    status, tipo, titulo = 503, "no-disponible", "Servicio no disponible"


@router.get("/salud", response_model=SaludSalida)
async def salud(db: Annotated[AsyncSession, Depends(get_db)]) -> SaludSalida:
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise ServicioNoDisponible from exc
    return SaludSalida(estado="ok")

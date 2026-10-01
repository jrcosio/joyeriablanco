"""Routers de la API v1. Cada historia de usuario añade el suyo aquí."""

from fastapi import APIRouter

from app.api.v1 import (
    auditoria,
    borradores,
    catalogos,
    clientes,
    configuracion,
    facturas,
    sesion,
    usuarios,
)

router = APIRouter()
router.include_router(sesion.router)
router.include_router(catalogos.router)
router.include_router(clientes.router)
router.include_router(usuarios.router)
router.include_router(auditoria.router)
router.include_router(configuracion.router)
router.include_router(facturas.router)
router.include_router(borradores.router)

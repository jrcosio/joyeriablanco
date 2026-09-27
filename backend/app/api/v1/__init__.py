"""Routers de la API v1. Cada historia de usuario añade el suyo aquí."""

from fastapi import APIRouter

from app.api.v1 import sesion

router = APIRouter()
router.include_router(sesion.router)

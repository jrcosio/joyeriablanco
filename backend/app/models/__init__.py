"""Modelos ORM. Importarlos aquí registra las tablas en `Base.metadata` (Alembic)."""

from app.models.base import Base
from app.models.cliente import Cliente
from app.models.evento_auditoria import EventoAuditoria
from app.models.provincia import Provincia
from app.models.sesion import Sesion
from app.models.usuario import Usuario

__all__ = ["Base", "Cliente", "EventoAuditoria", "Provincia", "Sesion", "Usuario"]

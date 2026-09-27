"""Catálogo de provincias (INE, a 1 de enero de 2026; research R-20.3)."""

from sqlalchemy import CHAR, CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Provincia(Base):
    __tablename__ = "provincias"

    codigo: Mapped[str] = mapped_column(CHAR(2), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60))  # literal oficial INE
    nombre_visible: Mapped[str] = mapped_column(String(60))  # orden natural para mostrar

    __table_args__ = (CheckConstraint("codigo ~ '^[0-9]{2}$'", name="formato_codigo"),)

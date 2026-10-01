"""Contador por serie y año (data-model §contadores_factura; research R-7).

Solo avanza: un trigger impide que `ultimo_numero` baje y que la fila se borre (migración 0005).
"""

from datetime import datetime

from sqlalchemy import Integer, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ContadorFactura(Base):
    __tablename__ = "contadores_factura"

    serie: Mapped[str] = mapped_column(String(3), primary_key=True)
    anio: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    ultimo_numero: Mapped[int] = mapped_column(Integer, server_default="0")
    actualizado_en: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

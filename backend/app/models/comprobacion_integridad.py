"""Comprobación de integridad lanzada: SOLO INSERCIÓN (004, data-model; research R-9 y R-11).

Guarda el alcance (de qué secuencia a cuál y si llega al final de la cadena) y el resultado, con
la secuencia anómala más alta de cada cadena. Con eso se deriva la alarma: se apaga cuando una
comprobación posterior a la anomalía garantiza los registros que la siguen (Orden, art. 6.f).
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UuidPkMixin


class ComprobacionIntegridad(UuidPkMixin, Base):
    __tablename__ = "comprobaciones_integridad"

    lanzada_en: Mapped[datetime] = mapped_column(server_default=func.now())
    origen: Mapped[str] = mapped_column(String(10))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    desde_secuencia: Mapped[int | None] = mapped_column(BigInteger)
    hasta_secuencia: Mapped[int | None] = mapped_column(BigInteger)
    llega_al_final: Mapped[bool] = mapped_column(Boolean)
    registros: Mapped[int] = mapped_column(Integer)
    eventos: Mapped[int] = mapped_column(Integer)
    anomalias: Mapped[int] = mapped_column(Integer)
    max_secuencia_anomala: Mapped[int | None] = mapped_column(BigInteger)
    max_evento_anomalo: Mapped[int | None] = mapped_column(BigInteger)
    evento_lanzamiento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("registros_evento.id"))

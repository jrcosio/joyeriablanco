"""Puerto "¿tiene documentos este cliente?" (FR-037, data-model §clientes).

En la feature 001 aún no existen facturas ni presupuestos, así que la implementación nula
responde siempre que no. Las features de facturas y presupuestos proporcionarán la real (además,
sus FK hacia clientes serán ON DELETE RESTRICT como segunda barrera en la BD).
"""

import uuid
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession


class ClienteDocumentosChecker(Protocol):
    async def tiene_documentos(self, db: AsyncSession, cliente_id: uuid.UUID) -> bool: ...


class SinDocumentos:
    async def tiene_documentos(self, db: AsyncSession, cliente_id: uuid.UUID) -> bool:
        return False


def get_documentos_checker() -> ClienteDocumentosChecker:
    return SinDocumentos()

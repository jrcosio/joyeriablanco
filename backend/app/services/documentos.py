"""Puerto "¿tiene documentos este cliente?" (FR-037 de 001; FR-042 de 002).

Con la feature 002 existen facturas y borradores: un cliente con cualquiera de ellos no se puede
borrar. Las FK de `facturas` y `borradores_factura` hacia `clientes` son además
`ON DELETE RESTRICT`, como segunda barrera en la BD. Presupuestos (feature 005) se sumarán aquí.
"""

import uuid
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import facturas


class ClienteDocumentosChecker(Protocol):
    async def tiene_documentos(self, db: AsyncSession, cliente_id: uuid.UUID) -> bool: ...


class SinDocumentos:
    """Implementación nula, útil en tests que aíslan el borrado de clientes."""

    async def tiene_documentos(self, db: AsyncSession, cliente_id: uuid.UUID) -> bool:
        return False


class DocumentosDeFacturacion:
    async def tiene_documentos(self, db: AsyncSession, cliente_id: uuid.UUID) -> bool:
        return await facturas.has_documentos(db, cliente_id)


def get_documentos_checker() -> ClienteDocumentosChecker:
    return DocumentosDeFacturacion()

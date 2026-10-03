"""Puerto "¿tiene documentos este cliente?" (FR-037 de 001; FR-042 de 002; FR-033 de 005).

Un cliente con cualquier factura, presupuesto o borrador de cualquiera de los dos no se puede
borrar. Las FK de `facturas`, `borradores_factura`, `presupuestos` y `borradores_presupuesto` hacia
`clientes` son además `ON DELETE RESTRICT`, como segunda barrera en la BD.
"""

import uuid
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import facturas, presupuestos


class ClienteDocumentosChecker(Protocol):
    async def tiene_documentos(self, db: AsyncSession, cliente_id: uuid.UUID) -> bool: ...


class SinDocumentos:
    """Implementación nula, útil en tests que aíslan el borrado de clientes."""

    async def tiene_documentos(self, db: AsyncSession, cliente_id: uuid.UUID) -> bool:
        return False


class DocumentosDeFacturacion:
    async def tiene_documentos(self, db: AsyncSession, cliente_id: uuid.UUID) -> bool:
        return await facturas.has_documentos(db, cliente_id) or await presupuestos.has_documentos(
            db, cliente_id
        )


def get_documentos_checker() -> ClienteDocumentosChecker:
    return DocumentosDeFacturacion()

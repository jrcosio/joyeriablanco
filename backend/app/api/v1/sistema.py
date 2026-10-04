"""/v1/sistema: datos del sistema y declaración responsable, para cualquier sesión (004).

RRSIF, art. 13.2: la declaración responsable es visible en el propio sistema. Orden, art. 15.3:
se puede descargar en un formato de uso extendido y gratuito.
"""

from typing import Any

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_current_session
from app.core.pdf.respuestas import respuesta_pdf
from app.schemas.sistema import Declaracion, DeclaracionApartado, Productor, SistemaSalida
from app.services import sistema

router = APIRouter(prefix="/sistema", tags=["sistema"], dependencies=[Depends(get_current_session)])

RESPUESTA_PDF: dict[int | str, dict[str, Any]] = {
    status.HTTP_200_OK: {
        "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
        "description": "Declaración responsable en PDF (Orden, art. 15.3)",
    }
}


@router.get("")
async def obtener_sistema() -> SistemaSalida:
    datos = sistema.system_info()
    return SistemaSalida(
        nombre=datos.nombre,
        id_sistema=datos.id_sistema,
        version=datos.version,
        numero_instalacion=datos.numero_instalacion,
        productor=Productor(
            nombre=datos.productor_nombre,
            nif=datos.productor_nif,
            direccion=datos.productor_direccion,
        ),
        modalidad="no_verifactu",
        declaracion=Declaracion(
            titulo="DECLARACIÓN RESPONSABLE DEL SISTEMA INFORMÁTICO DE FACTURACIÓN",
            apartados=[
                DeclaracionApartado(letra=a.letra, texto=a.texto, valor=a.valor)
                for a in datos.declaracion.apartados
            ],
        ),
    )


@router.get("/declaracion-responsable/pdf", response_class=Response, responses=RESPUESTA_PDF)
async def descargar_declaracion() -> Response:
    documento = await sistema.declaration_pdf()
    return respuesta_pdf(documento.nombre, documento.contenido)

"""Los logs de la facturación no contienen datos personales ni importes (FR-051).

Tras emitir, guardar un borrador, rectificar, anular y buscar, en los logs solo aparecen
identificadores internos, números de factura y el tipo de operación.
"""

import io
import logging
from collections.abc import Iterator

import pytest
from httpx import AsyncClient
from pythonjsonlogger.json import JsonFormatter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import RedactionFilter
from app.domain.tipos import Rol
from tests.conftest import CrearUsuario, IniciarSesion
from tests.integration.facturacion_datos import (
    IBAN_DEMO,
    LINGOTE,
    NIF_MARIA,
    cabeceras,
    configurar_facturacion,
    crear_cliente,
    cuerpo_factura,
)

URL = "/api/v1/facturas"
PROHIBIDOS = (
    "María",
    "Maria",
    "López",
    "Lopez",
    NIF_MARIA,
    "Calle Serrano",
    "28001",
    # Importes de la captura (1.290,00 + 270,90 = 1.560,90) y de la rectificativa.
    "1290",
    "1.290",
    "270.9",
    "270,9",
    "1560",
    "1.560",
    "1100",
    "1331",
    # IBAN del emisor (R-22), completo y agrupado, y el importe del lingote exento.
    IBAN_DEMO,
    "ES91 2100",
    "7450",
)


@pytest.fixture
def salida_logs() -> Iterator[io.StringIO]:
    """Captura los logs con el mismo formateador y filtro que producción."""
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    handler.addFilter(RedactionFilter())
    handler.addFilter(lambda registro: not registro.name.startswith(("httpx", "httpcore")))
    raiz = logging.getLogger()
    nivel = raiz.level
    raiz.addHandler(handler)
    raiz.setLevel(logging.DEBUG)
    try:
        yield buffer
    finally:
        raiz.removeHandler(handler)
        raiz.setLevel(nivel)


async def test_emitir_corregir_y_buscar_no_deja_datos_personales_ni_importes(
    client: AsyncClient,
    db: AsyncSession,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    salida_logs: io.StringIO,
) -> None:
    admin = await crear_usuario("admin.logs", rol=Rol.ADMINISTRADOR)
    csrf = await iniciar_sesion(client, "admin.logs")
    await configurar_facturacion(db, iban=IBAN_DEMO)
    maria = await crear_cliente(db, admin.id)
    exenta = await client.post(
        URL,
        json=cuerpo_factura(maria.id, lineas=LINGOTE, oro_inversion=True),
        headers=cabeceras(csrf),
    )
    assert exenta.status_code == 201, exenta.text

    emitida = (
        await client.post(URL, json=cuerpo_factura(maria.id), headers=cabeceras(csrf))
    ).json()
    borrador = await client.post(
        "/api/v1/borradores-factura",
        json=cuerpo_factura(maria.id),
        headers={"X-CSRF-Token": csrf},
    )
    assert borrador.status_code == 201
    rec = await client.post(
        f"{URL}/{emitida['id']}/modificacion",
        json={
            "motivo": "factura_entregada",
            "causa": "error_datos",
            "motivo_texto": "María pidió otra talla",
            "cliente_id": str(maria.id),
            "lineas": [{"unidades": "1", "descripcion": "Anillo", "precio_unitario": "1100"}],
            "oro_inversion": False,
        },
        headers=cabeceras(csrf),
    )
    assert rec.status_code == 201, rec.text
    anulada = await client.post(
        f"{URL}/{rec.json()['id']}/anulacion",
        json={"declaracion_no_debio_emitirse": True, "motivo_texto": "Error con María López"},
        headers=cabeceras(csrf),
    )
    assert anulada.status_code == 200
    await client.get(URL, params={"q": "maria lopez"})
    await client.get(URL, params={"q": NIF_MARIA})

    salida = salida_logs.getvalue()
    for prohibido in PROHIBIDOS:
        assert prohibido not in salida, prohibido
    # Lo que sí queda: los números y la operación.
    assert f"Factura {emitida['num_serie']} expedida (emitir)" in salida
    assert f"Factura {rec.json()['num_serie']} anulada" in salida

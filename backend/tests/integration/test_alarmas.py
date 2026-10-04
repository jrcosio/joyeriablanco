"""US3 de 004 — Alarmas de integridad y de certificado (FR-019, SC-009; research R-11).

Orden, art. 6.f: la alarma se ve en todas las pantallas, para todos los usuarios, y no se apaga
hasta que una comprobación posterior garantiza los registros que siguen al afectado.
"""

import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain import eventos
from app.domain.tipos import Rol, TipoAnomalia, TipoEventoSif
from app.models import Cliente, Usuario
from app.services import eventos_sif, integridad
from app.services.eventos_sif import NuevoEvento
from tests.conftest import CrearUsuario, IniciarSesion
from tests.integration.facturacion_datos import (
    cabeceras,
    configurar_facturacion,
    crear_cliente,
    cuerpo_factura,
)

URL = "/api/v1/alarmas"


@pytest.fixture
async def empleada(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> tuple[Usuario, str]:
    usuario = await crear_usuario("empleada.alarmas")
    return usuario, await iniciar_sesion(client, "empleada.alarmas")


@pytest.fixture
async def maria(db: AsyncSession, empleada: tuple[Usuario, str]) -> Cliente:
    await configurar_facturacion(db)
    return await crear_cliente(db, empleada[0].id)


async def _dos_facturas(client: AsyncClient, csrf: str, cliente: Cliente) -> None:
    for _ in range(2):
        respuesta = await client.post(
            "/api/v1/facturas", json=cuerpo_factura(cliente.id), headers=cabeceras(csrf)
        )
        assert respuesta.status_code == 201, respuesta.text


async def _anomalia_en(db: AsyncSession, secuencia: int) -> None:
    """Como la que deja una comprobación al detectar una huella alterada en ese registro."""
    await eventos_sif.record_evento(
        db,
        NuevoEvento(
            TipoEventoSif.ANOMALIA_FACTURACION,
            datos_propios=eventos.anomalia_facturacion(
                TipoAnomalia.HUELLA, descripcion="Prueba", factura=None
            ),
            tipo_anomalia=TipoAnomalia.HUELLA,
            secuencia_afectada=secuencia,
        ),
    )


async def _alarmas(client: AsyncClient) -> list[dict[str, Any]]:
    respuesta = await client.get(URL)
    assert respuesta.status_code == 200, respuesta.text
    return list(respuesta.json()["alarmas"])


async def test_sin_anomalias_no_hay_alarma(
    client: AsyncClient, empleada: tuple[Usuario, str], maria: Cliente
) -> None:
    await _dos_facturas(client, empleada[1], maria)

    assert await _alarmas(client) == []


async def test_una_anomalia_enciende_la_alarma_para_cualquier_usuario(
    client: AsyncClient, db: AsyncSession, empleada: tuple[Usuario, str], maria: Cliente
) -> None:
    await _dos_facturas(client, empleada[1], maria)
    await _anomalia_en(db, 1)

    [alarma] = await _alarmas(client)

    assert alarma["tipo"] == "integridad"
    assert alarma["mensaje"].startswith(
        "Alarma de integridad: se ha detectado una anomalía en los registros el "
    )
    assert alarma["secuencia_afectada"] == 1


async def test_una_comprobacion_posterior_hasta_el_final_la_apaga(
    client: AsyncClient, db: AsyncSession, empleada: tuple[Usuario, str], maria: Cliente
) -> None:
    await _dos_facturas(client, empleada[1], maria)
    await integridad.verify_chain(db)  # anterior a la anomalía: no cuenta
    await _anomalia_en(db, 1)
    assert len(await _alarmas(client)) == 1

    await integridad.verify_chain(db, desde=1, hasta=1)  # no llega al final
    assert len(await _alarmas(client)) == 1

    await integridad.verify_chain(db, desde=2)  # desde el siguiente al afectado, hasta el final
    assert await _alarmas(client) == []


async def test_una_comprobacion_con_una_anomalia_nueva_posterior_no_la_apaga(
    client: AsyncClient,
    db: AsyncSession,
    empleada: tuple[Usuario, str],
    maria: Cliente,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _dos_facturas(client, empleada[1], maria)
    await _anomalia_en(db, 1)
    real = integridad._check_facturacion

    async def con_anomalia_en_2(*args: Any) -> Any:
        revisados, _ = await real(*args)
        return revisados, [
            integridad.Anomalia("facturacion", TipoAnomalia.FIRMA, "Prueba", 2, "FAC")
        ]

    monkeypatch.setattr(integridad, "_check_facturacion", con_anomalia_en_2)
    await integridad.verify_chain(db)

    [alarma] = await _alarmas(client)
    assert alarma["secuencia_afectada"] == 1


@pytest.fixture
def sin_certificado(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    monkeypatch.setenv("CERTIFICADO_RUTA", str(tmp_path / f"{uuid.uuid4()}.p12"))
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


@pytest.mark.usefixtures("sin_certificado", "maria")
async def test_sin_certificado_utilizable_hay_alarma_de_certificado(client: AsyncClient) -> None:
    [alarma] = await _alarmas(client)

    assert alarma["tipo"] == "certificado"
    assert alarma["mensaje"] == (
        "No se puede facturar: el certificado de firma no es utilizable "
        "(no hay ningún certificado instalado)"
    )
    assert alarma["secuencia_afectada"] is None


@pytest.mark.usefixtures("sin_certificado", "empleada")
async def test_en_verifactu_no_hay_alarma_de_certificado(
    client: AsyncClient, db: AsyncSession
) -> None:
    await configurar_facturacion(db, modalidad="verifactu")

    assert await _alarmas(client) == []


async def test_sin_sesion_401(client: AsyncClient) -> None:
    assert (await client.get(URL)).status_code == 401


async def test_un_administrador_tambien_la_ve(
    client: AsyncClient,
    db: AsyncSession,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
) -> None:
    await crear_usuario("admin.alarmas", rol=Rol.ADMINISTRADOR)
    await iniciar_sesion(client, "admin.alarmas")
    await configurar_facturacion(db)
    await _anomalia_en(db, 7)

    [alarma] = await _alarmas(client)
    assert alarma["tipo"] == "integridad"

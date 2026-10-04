"""US4 de 004 — Exportar los registros de un periodo (FR-022 a FR-026; contracts/exportacion.md).

Orden, art. 8: copia fidedigna de los registros tal como se firmaron, que se pueden verificar fuera
del sistema, y el evento 08 o 09 de la exportación, con «dejan de conservarse» = N.
"""

import asyncio
import csv
import io
import uuid
import zipfile
from collections.abc import Iterator
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typer.testing import CliRunner

from app.cli import app as cli
from app.core.config import get_settings
from app.core.tiempo import hoy
from app.domain.tipos import Rol, TipoEvento
from app.models import Cliente, RegistroEvento, RegistroFacturacion, Usuario
from app.services import exportacion, firma
from tests.conftest import CrearUsuario, IniciarSesion, eventos
from tests.integration.facturacion_datos import (
    cabeceras,
    configurar_facturacion,
    crear_cliente,
    cuerpo_factura,
)

URL = "/api/v1/registro-fiscal/exportacion"


@pytest.fixture
async def admin(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> tuple[Usuario, str]:
    usuario = await crear_usuario("admin.exportacion", rol=Rol.ADMINISTRADOR)
    return usuario, await iniciar_sesion(client, "admin.exportacion")


@pytest.fixture
async def cadena(
    client: AsyncClient, db: AsyncSession, admin: tuple[Usuario, str]
) -> list[dict[str, Any]]:
    """Tres altas y la anulación de la primera, todo de hoy."""
    await configurar_facturacion(db)
    cliente: Cliente = await crear_cliente(db, admin[0].id)
    facturas = []
    for precio in ("100", "200", "300"):
        respuesta = await client.post(
            "/api/v1/facturas",
            json=cuerpo_factura(
                cliente.id,
                lineas=[{"unidades": "1", "descripcion": "Anillo", "precio_unitario": precio}],
            ),
            headers=cabeceras(admin[1]),
        )
        assert respuesta.status_code == 201, respuesta.text
        facturas.append(dict(respuesta.json()))
    anulacion = await client.post(
        f"/api/v1/facturas/{facturas[0]['id']}/anulacion",
        json={"declaracion_no_debio_emitirse": True, "motivo_texto": "Duplicada"},
        headers=cabeceras(admin[1]),
    )
    assert anulacion.status_code == 200, anulacion.text
    return facturas


def _zip(contenido: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(contenido))


async def test_el_zip_de_facturacion_tiene_cada_registro_tal_como_se_firmo(
    client: AsyncClient, db: AsyncSession, cadena: list[dict[str, Any]]
) -> None:
    dia = hoy().isoformat()

    respuesta = await client.get(URL, params={"tipo": "facturacion", "desde": dia, "hasta": dia})

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["content-type"] == "application/zip"
    compacto = f"{hoy():%Y%m%d}"
    assert respuesta.headers["content-disposition"] == (
        f'attachment; filename="registros-facturacion-{compacto}-{compacto}.zip"'
    )
    archivo = _zip(respuesta.content)
    numeros = [f["num_serie"] for f in cadena]
    xmls = [
        f"facturacion/0000001-alta-{numeros[0]}.xml",
        f"facturacion/0000002-alta-{numeros[1]}.xml",
        f"facturacion/0000003-alta-{numeros[2]}.xml",
        f"facturacion/0000004-anulacion-{numeros[0]}.xml",
    ]
    assert archivo.namelist() == [*xmls, "indice.csv", "resumen.txt", "manifiesto.sha256"]
    registros = list(
        (
            await db.execute(select(RegistroFacturacion).order_by(RegistroFacturacion.secuencia))
        ).scalars()
    )
    for ruta, registro in zip(xmls, registros, strict=True):
        xml = archivo.read(ruta)
        assert xml == registro.xml_firmado  # byte a byte (FR-023)
        verificada = firma.verificar(xml, en=datetime.fromisoformat(registro.fecha_hora_huso_gen))
        assert verificada.huella == registro.certificado_huella  # fuera de la BD

    indice = archivo.read("indice.csv").decode("utf-8")
    assert indice.startswith("﻿")
    filas = list(csv.reader(io.StringIO(indice.removeprefix("﻿")), delimiter=";"))
    assert filas[0] == list(exportacion.CABECERA_FACTURACION)
    assert [f[:3] for f in filas[1:]] == [
        ["1", "alta", numeros[0]],
        ["2", "alta", numeros[1]],
        ["3", "alta", numeros[2]],
        ["4", "anulacion", numeros[0]],
    ]
    manifiesto = archivo.read("manifiesto.sha256").decode().splitlines()
    assert len(manifiesto) == 6
    for linea in manifiesto:
        huella, ruta = linea.split("  ")
        assert sha256(archivo.read(ruta)).hexdigest() == huella
    resumen = archivo.read("resumen.txt").decode()
    assert "Registros de alta: 3" in resumen
    assert "Registros de anulación: 1" in resumen
    assert "Suma del importe total de las altas: 726.00 EUR" in resumen  # 121 + 242 + 363
    assert exportacion.CONSERVACION in resumen


async def test_genera_el_evento_08_y_la_auditoria(
    client: AsyncClient, db: AsyncSession, admin: tuple[Usuario, str], cadena: list[dict[str, Any]]
) -> None:
    dia = hoy().isoformat()

    respuesta = await client.get(URL, params={"tipo": "facturacion", "desde": dia, "hasta": dia})

    [evento] = list(
        (
            await db.execute(select(RegistroEvento).where(RegistroEvento.tipo_evento == "08"))
        ).scalars()
    )
    datos = evento.contenido["Evento"]["DatosPropiosEvento"]["ExportacionRegFacturacionPeriodo"]
    assert datos["FechaHoraHusoInicioPeriodoExport"].startswith(f"{dia}T00:00:00")
    assert datos["FechaHoraHusoFinPeriodoExport"].startswith(f"{dia}T23:59:59")
    assert datos["RegistroFacturacionInicialPeriodo"]["NumSerieFactura"] == cadena[0]["num_serie"]
    assert datos["RegistroFacturacionFinalPeriodo"]["NumSerieFactura"] == cadena[0]["num_serie"]
    assert datos["NumeroDeRegistrosFacturacionAltaExportados"] == "3"
    assert datos["SumaCuotaTotalAlta"] == "126.00"
    assert datos["SumaImporteTotalAlta"] == "726.00"
    assert datos["NumeroDeRegistrosFacturacionAnulacionExportados"] == "1"
    assert datos["RegistrosFacturacionExportadosDejanDeConservarse"] == "N"
    [auditada] = await eventos(db, TipoEvento.REGISTROS_EXPORTADOS)
    assert auditada.actor_id == admin[0].id
    assert auditada.detalle["registros"] == 4
    assert auditada.detalle["sha256"] == sha256(respuesta.content).hexdigest()


async def test_los_eventos_se_exportan_y_generan_el_09(
    client: AsyncClient, db: AsyncSession, cadena: list[dict[str, Any]]
) -> None:
    dia = hoy().isoformat()
    await client.get(URL, params={"tipo": "facturacion", "desde": dia, "hasta": dia})  # un 08

    respuesta = await client.get(URL, params={"tipo": "eventos", "desde": dia, "hasta": dia})

    assert respuesta.status_code == 200, respuesta.text
    archivo = _zip(respuesta.content)
    [xml] = [n for n in archivo.namelist() if n.startswith("eventos/")]
    assert xml == "eventos/0000001-08.xml"
    filas = archivo.read("indice.csv").decode().removeprefix("﻿").splitlines()
    assert filas[0] == ";".join(exportacion.CABECERA_EVENTOS)
    [nueve] = list(
        (
            await db.execute(select(RegistroEvento).where(RegistroEvento.tipo_evento == "09"))
        ).scalars()
    )
    datos = nueve.contenido["Evento"]["DatosPropiosEvento"]["ExportacionRegEventoPeriodo"]
    assert datos["NumeroDeRegEventoExportados"] == "1"
    assert datos["RegEventoExportadosDejanDeConservarse"] == "N"


@pytest.mark.usefixtures("cadena")
async def test_un_periodo_vacio_o_al_reves_no_genera_nada(
    client: AsyncClient, db: AsyncSession
) -> None:
    ayer = (hoy() - timedelta(days=1)).isoformat()

    vacio = await client.get(URL, params={"tipo": "facturacion", "desde": ayer, "hasta": ayer})
    al_reves = await client.get(
        URL, params={"tipo": "facturacion", "desde": hoy().isoformat(), "hasta": ayer}
    )
    sin_tipo = await client.get(URL, params={"tipo": "otros", "desde": ayer, "hasta": ayer})

    assert vacio.status_code == 422
    assert vacio.json()["type"] == "/problemas/sin-registros"
    assert vacio.json()["detail"] == "No hay registros en ese periodo."
    assert al_reves.status_code == 422
    assert al_reves.json()["errores"][0]["campo"] == "hasta"
    assert sin_tipo.status_code == 422
    assert await db.scalar(select(func.count()).select_from(RegistroEvento)) == 0


@pytest.fixture
def sin_certificado(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    monkeypatch.setenv("CERTIFICADO_RUTA", str(tmp_path / f"{uuid.uuid4()}.p12"))
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


@pytest.mark.usefixtures("cadena", "sin_certificado")
async def test_sin_certificado_no_se_exporta(client: AsyncClient) -> None:
    dia = hoy().isoformat()

    respuesta = await client.get(URL, params={"tipo": "facturacion", "desde": dia, "hasta": dia})

    assert respuesta.status_code == 409
    assert respuesta.json()["motivo"] == "no_instalado"


async def test_un_empleado_no_exporta(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> None:
    await crear_usuario("empleado.exportacion")
    await iniciar_sesion(client, "empleado.exportacion")
    dia = hoy().isoformat()

    respuesta = await client.get(URL, params={"tipo": "eventos", "desde": dia, "hasta": dia})

    assert respuesta.status_code == 403


# ----------------------------------------------------------------------------------- CLI


async def test_la_cli_exporta_a_un_fichero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    temporal = tmp_path / "temporal.zip"
    temporal.write_bytes(b"PK zip de prueba")

    async def exportado(*_: object, **__: object) -> exportacion.Exportacion:
        return exportacion.Exportacion(
            ruta=temporal, nombre="registros.zip", registros=7, sha256="ab" * 32
        )

    monkeypatch.setattr(exportacion, "export_records", exportado)
    destino = tmp_path / "salida" / "registros.zip"

    resultado = await asyncio.to_thread(
        CliRunner().invoke,
        cli,
        [
            "exportar-registros",
            "--tipo",
            "facturacion",
            "--desde",
            "2026-10-01",
            "--hasta",
            "2026-10-31",
            "--destino",
            str(destino),
        ],
    )

    assert resultado.exit_code == 0, resultado.output
    assert destino.read_bytes() == b"PK zip de prueba"
    assert f"7 registros, SHA-256 {'ab' * 32}" in resultado.output


async def test_la_cli_sin_registros_o_con_fechas_no_validas(tmp_path: Path) -> None:
    destino = tmp_path / "registros.zip"

    def invocar(*argumentos: str) -> Any:
        return CliRunner().invoke(
            cli, ["exportar-registros", *argumentos, "--destino", str(destino)]
        )

    # La BD de test no tiene registros confirmados: cualquier periodo está vacío.
    vacio = await asyncio.to_thread(
        invocar, "--tipo", "facturacion", "--desde", "2026-01-01", "--hasta", "2026-01-31"
    )
    al_reves = await asyncio.to_thread(
        invocar, "--tipo", "eventos", "--desde", "2026-02-01", "--hasta", "2026-01-01"
    )
    tipo = await asyncio.to_thread(
        invocar, "--tipo", "otros", "--desde", "2026-01-01", "--hasta", "2026-01-31"
    )

    assert vacio.exit_code == 1, vacio.output
    assert "No hay registros en ese periodo." in vacio.output
    assert [al_reves.exit_code, tipo.exit_code] == [2, 2]
    assert not destino.exists()

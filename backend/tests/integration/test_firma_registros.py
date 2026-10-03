"""⚖️ US1 de 004 — Cada factura deja su registro firmado (FR-004 a FR-011, SC-001, SC-002).

Constitución VII (2.4.0): los registros en No VERI*FACTU se generan en XML, cumplen
`SuministroInformacion.xsd`, se firman con XAdES-EPES antes de insertarlos y su firma se verifica.
Sin un certificado utilizable no se emite, no se anula ni se rectifica, y no se consume número.
"""

import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient
from lxml import etree
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.tiempo import hoy
from app.domain.tipos import Rol
from app.domain.xml_registro import NS_SUMINISTRO
from app.models import Cliente, Factura, RegistroFacturacion, Usuario
from app.services import firma
from tests.certificados import CONTRASENA_PRUEBAS, escribir_pkcs12
from tests.conftest import CrearUsuario, IniciarSesion
from tests.integration.facturacion_datos import (
    URL_PRESUPUESTOS,
    cabeceras,
    configurar_facturacion,
    crear_cliente,
    cuerpo_factura,
    emitir_presupuesto,
)

URL = "/api/v1/facturas"
AHORA = datetime.now(UTC)

type UsarCertificado = Callable[..., None]


@pytest.fixture
def usar_certificado(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[UsarCertificado]:
    """Cambia el certificado instalado durante el test (`None`: no instalado)."""

    def _usar(ruta: Path | None) -> None:
        monkeypatch.setenv("CERTIFICADO_RUTA", str(ruta or tmp_path / "no-existe.p12"))
        monkeypatch.setenv("CERTIFICADO_CONTRASENA", CONTRASENA_PRUEBAS)
        get_settings.cache_clear()

    yield _usar
    monkeypatch.undo()
    get_settings.cache_clear()


@pytest.fixture
async def admin(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> tuple[Usuario, str]:
    usuario = await crear_usuario("admin.firma", rol=Rol.ADMINISTRADOR)
    return usuario, await iniciar_sesion(client, "admin.firma")


@pytest.fixture
async def maria(db: AsyncSession, admin: tuple[Usuario, str]) -> Cliente:
    await configurar_facturacion(db, modalidad="no_verifactu")
    return await crear_cliente(db, admin[0].id)


async def _emitir(client: AsyncClient, csrf: str, cliente: Cliente) -> Any:
    return await client.post(URL, json=cuerpo_factura(cliente.id), headers=cabeceras(csrf))


async def _emitida(client: AsyncClient, csrf: str, cliente: Cliente) -> dict[str, Any]:
    respuesta = await _emitir(client, csrf, cliente)
    assert respuesta.status_code == 201, respuesta.text
    return dict(respuesta.json())


async def _registros(db: AsyncSession, factura_id: str) -> list[RegistroFacturacion]:
    resultado = await db.execute(
        select(RegistroFacturacion)
        .where(RegistroFacturacion.factura_id == uuid.UUID(factura_id))
        .order_by(RegistroFacturacion.secuencia)
    )
    return list(resultado.scalars())


def _comprobar_firmado(registro: RegistroFacturacion, raiz_esperada: str) -> None:
    assert registro.xml_firmado is not None
    assert registro.estado_remision == "no_aplica"
    assert registro.certificado_titular == "JOYERIA BLANCO (PRUEBAS)"
    raiz = etree.fromstring(registro.xml_firmado)
    assert raiz.tag == f"{{{NS_SUMINISTRO}}}{raiz_esperada}"
    firma.validar(raiz, firma.Esquema.SUMINISTRO)
    verificada = firma.verificar(
        registro.xml_firmado, en=datetime.fromisoformat(registro.fecha_hora_huso_gen)
    )
    assert verificada.huella == registro.certificado_huella
    huella = raiz.find(f"{{{NS_SUMINISTRO}}}Huella")
    assert huella is not None
    assert huella.text == registro.huella


async def test_emitir_deja_el_registro_firmado_y_la_consulta_lo_muestra(
    client: AsyncClient, admin: tuple[Usuario, str], maria: Cliente, db: AsyncSession
) -> None:
    factura = await _emitida(client, admin[1], maria)

    [registro] = await _registros(db, factura["id"])
    _comprobar_firmado(registro, "RegistroAlta")
    detalle = (await client.get(f"{URL}/{factura['id']}")).json()
    assert detalle["registros"] == [
        {
            "tipo": "alta",
            "secuencia": registro.secuencia,
            "huella": registro.huella,
            "fecha_hora_huso_gen": registro.fecha_hora_huso_gen,
            "estado_remision": "no_aplica",
            "firmado": True,
            "certificado_titular": "JOYERIA BLANCO (PRUEBAS)",
            "huella_correcta": True,
            "firma_correcta": True,
        }
    ]


async def test_anular_y_rectificar_dejan_sus_registros_firmados(
    client: AsyncClient, admin: tuple[Usuario, str], maria: Cliente, db: AsyncSession
) -> None:
    anulada = await _emitida(client, admin[1], maria)
    rectificada = await _emitida(client, admin[1], maria)

    anulacion = await client.post(
        f"{URL}/{anulada['id']}/anulacion",
        json={"declaracion_no_debio_emitirse": True, "motivo_texto": "Duplicada"},
        headers=cabeceras(admin[1]),
    )
    modificacion = await client.post(
        f"{URL}/{rectificada['id']}/modificacion",
        json={
            "motivo": "factura_entregada",
            "causa": "error_datos",
            "motivo_texto": "Precio mal puesto",
            "cliente_id": str(maria.id),
            "lineas": [{"unidades": "1", "descripcion": "Anillo", "precio_unitario": "900"}],
            "oro_inversion": False,
        },
        headers=cabeceras(admin[1]),
    )

    assert anulacion.status_code == 200, anulacion.text
    assert modificacion.status_code == 201, modificacion.text
    _, registro_anulacion = await _registros(db, anulada["id"])
    _comprobar_firmado(registro_anulacion, "RegistroAnulacion")
    [registro_rec] = await _registros(db, modificacion.json()["id"])
    _comprobar_firmado(registro_rec, "RegistroAlta")


async def test_convertir_un_presupuesto_deja_el_registro_firmado(
    client: AsyncClient, admin: tuple[Usuario, str], maria: Cliente, db: AsyncSession
) -> None:
    presupuesto = await emitir_presupuesto(client, admin[1], maria.id)
    borrador = (
        await client.post(
            f"{URL_PRESUPUESTOS}/{presupuesto['id']}/conversion",
            headers={"X-CSRF-Token": admin[1]},
        )
    ).json()

    respuesta = await client.post(
        f"/api/v1/borradores-factura/{borrador['id']}/emision",
        json={
            "fecha_expedicion": borrador["fecha_expedicion"],
            "cliente_id": borrador["cliente"]["id"],
            "lineas": [
                {k: linea[k] for k in ("unidades", "descripcion", "precio_unitario")}
                for linea in borrador["lineas"]
            ],
            "oro_inversion": False,
            "version": borrador["version"],
        },
        headers=cabeceras(admin[1]),
    )

    assert respuesta.status_code == 201, respuesta.text
    [registro] = await _registros(db, respuesta.json()["id"])
    _comprobar_firmado(registro, "RegistroAlta")


# ------------------------------------------------------- sin certificado utilizable (FR-004)


async def _numero_de_facturas(db: AsyncSession) -> int:
    return int((await db.execute(select(func.count()).select_from(Factura))).scalar_one())


@pytest.mark.parametrize(
    ("opciones", "motivo"),
    [
        (None, "no_instalado"),
        ({"desde": AHORA - timedelta(days=400), "dias": 365}, "caducado"),
        ({"desde": AHORA + timedelta(days=5)}, "aun_no_valido"),
    ],
    ids=["no-instalado", "caducado", "aun-no-valido"],
)
async def test_sin_certificado_utilizable_no_se_emite_ni_se_consume_numero(
    client: AsyncClient,
    admin: tuple[Usuario, str],
    maria: Cliente,
    db: AsyncSession,
    usar_certificado: UsarCertificado,
    tmp_path: Path,
    opciones: dict[str, Any] | None,
    motivo: str,
) -> None:
    usar_certificado(None if opciones is None else escribir_pkcs12(tmp_path / "c.p12", **opciones))
    antes = await _numero_de_facturas(db)

    respuesta = await _emitir(client, admin[1], maria)
    parametros = (await client.get(f"{URL}/parametros")).json()

    assert respuesta.status_code == 409, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["type"] == "/problemas/emision-no-disponible"
    assert cuerpo["faltan"] == ["certificado"]
    assert cuerpo["motivo"] == motivo
    assert await _numero_de_facturas(db) == antes
    assert parametros["faltan"] == ["certificado"]
    assert parametros["emision_posible"] is False
    assert parametros["proximo_numero"] == f"FAC-{hoy().year}-0001"  # sin consumir


async def test_sin_certificado_no_se_anula_ni_se_rectifica_ni_se_emite_un_borrador(
    client: AsyncClient,
    admin: tuple[Usuario, str],
    maria: Cliente,
    db: AsyncSession,
    usar_certificado: UsarCertificado,
) -> None:
    factura = await _emitida(client, admin[1], maria)
    presupuesto = await emitir_presupuesto(client, admin[1], maria.id)
    borrador = (
        await client.post(
            f"{URL_PRESUPUESTOS}/{presupuesto['id']}/conversion",
            headers={"X-CSRF-Token": admin[1]},
        )
    ).json()
    usar_certificado(None)

    anulacion = await client.post(
        f"{URL}/{factura['id']}/anulacion",
        json={"declaracion_no_debio_emitirse": True, "motivo_texto": "Duplicada"},
        headers=cabeceras(admin[1]),
    )
    rectificacion = await client.post(
        f"{URL}/{factura['id']}/modificacion",
        json={
            "motivo": "factura_entregada",
            "causa": "error_datos",
            "motivo_texto": "Precio",
            "cliente_id": str(maria.id),
            "lineas": [{"unidades": "1", "descripcion": "Anillo", "precio_unitario": "900"}],
            "oro_inversion": False,
        },
        headers=cabeceras(admin[1]),
    )
    reemision = await client.post(
        f"{URL}/{factura['id']}/modificacion",
        json={
            "motivo": "no_debio_emitirse",
            "motivo_texto": "Cliente equivocado",
            "cliente_id": str(maria.id),
            "lineas": [{"unidades": "1", "descripcion": "Anillo", "precio_unitario": "900"}],
            "oro_inversion": False,
        },
        headers=cabeceras(admin[1]),
    )
    conversion = await client.post(
        f"/api/v1/borradores-factura/{borrador['id']}/emision",
        json={
            "fecha_expedicion": borrador["fecha_expedicion"],
            "cliente_id": borrador["cliente"]["id"],
            "lineas": [
                {k: linea[k] for k in ("unidades", "descripcion", "precio_unitario")}
                for linea in borrador["lineas"]
            ],
            "oro_inversion": False,
            "version": borrador["version"],
        },
        headers=cabeceras(admin[1]),
    )

    for respuesta in (anulacion, rectificacion, reemision, conversion):
        assert respuesta.status_code == 409, respuesta.text
        assert respuesta.json()["faltan"] == ["certificado"]
        assert respuesta.json()["motivo"] == "no_instalado"
    assert len(await _registros(db, factura["id"])) == 1  # solo el alta
    detalle = (await client.get(f"{URL}/{factura['id']}")).json()
    assert detalle["estado"] == "vigente"


async def test_avisa_de_la_caducidad_proxima_en_los_parametros(
    client: AsyncClient,
    admin: tuple[Usuario, str],
    maria: Cliente,
    usar_certificado: UsarCertificado,
    tmp_path: Path,
) -> None:
    usar_certificado(
        escribir_pkcs12(tmp_path / "c.p12", desde=AHORA - timedelta(days=340), dias=365)
    )

    parametros = (await client.get(f"{URL}/parametros")).json()
    configuracion = (await client.get("/api/v1/configuracion/facturacion")).json()

    assert parametros["emision_posible"] is True
    caduca = (AHORA + timedelta(days=25)).astimezone(ZoneInfo("Europe/Madrid")).date()
    assert parametros["certificado_caduca_el"] == caduca.isoformat()
    assert configuracion["certificado"]["estado"] == "utilizable"
    assert configuracion["certificado"]["caduca_pronto"] is True
    assert configuracion["certificado"]["titular"] == "JOYERIA BLANCO (PRUEBAS)"
    assert "contrasena" not in str(configuracion["certificado"])


async def test_con_el_certificado_en_regla_no_hay_aviso(
    client: AsyncClient, admin: tuple[Usuario, str], maria: Cliente
) -> None:
    parametros = (await client.get(f"{URL}/parametros")).json()
    configuracion = (await client.get("/api/v1/configuracion/facturacion")).json()

    assert parametros["certificado_caduca_el"] is None
    assert configuracion["certificado"] == {
        "estado": "utilizable",
        "motivo": None,
        "titular": "JOYERIA BLANCO (PRUEBAS)",
        "identificacion": "B12345674",
        "emisor": "JOYERIA BLANCO (PRUEBAS)",
        "valido_desde": configuracion["certificado"]["valido_desde"],
        "valido_hasta": configuracion["certificado"]["valido_hasta"],
        "dias_restantes": configuracion["certificado"]["dias_restantes"],
        "caduca_pronto": False,
    }


# --------------------------------------------------------- VERI*FACTU: el modelo admite ambas


async def test_en_verifactu_el_registro_no_se_firma(
    client: AsyncClient, admin: tuple[Usuario, str], db: AsyncSession
) -> None:
    await configurar_facturacion(db, modalidad="verifactu")
    cliente = await crear_cliente(db, admin[0].id)

    factura = await _emitida(client, admin[1], cliente)

    [registro] = await _registros(db, factura["id"])
    assert registro.xml_firmado is None
    assert registro.estado_remision == "pendiente"
    [resumen] = (await client.get(f"{URL}/{factura['id']}")).json()["registros"]
    assert resumen["firmado"] is False
    assert resumen["certificado_titular"] is None
    assert resumen["huella_correcta"] is True
    assert resumen["firma_correcta"] is None

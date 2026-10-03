"""Presupuesto en PDF, sin QR tributario (005, US2; FR-029 a FR-031, SC-007; research R-10).

Los presupuestos se emiten con la API real y el texto del PDF se extrae con pypdf, como en
`test_pdf_factura.py` (003). Las marcas de los presupuestos cerrados se prueban con sus cierres:
«CONVERTIDO» en la conversión (US3) y «ANULADO» y «SUSTITUIDO» en US4.
"""

import dataclasses
import io
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient, Response
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pdf import render
from app.core.tiempo import hoy
from app.domain.exenciones import MENCION_EXENCION_ORO_INVERSION
from app.domain.formato import format_euros, format_fecha
from app.domain.qr import FRASE_VERIFACTU
from app.domain.tipos import Rol
from app.models import Cliente, Usuario
from app.repositories import configuracion_facturacion
from app.services import impresion_presupuestos
from tests.conftest import CrearUsuario, IniciarSesion
from tests.integration.facturacion_datos import (
    IBAN_DEMO,
    LINGOTE,
    URL_PRESUPUESTOS,
    configurar_facturacion,
    crear_borrador_presupuesto,
    crear_cliente,
    emitir_presupuesto,
)

ANIO = hoy().year
NBSP = "\u00a0"
AVISO = "Documento sin validez fiscal. No es una factura."
CSP_PDF = (
    "default-src 'none'; object-src 'self'; frame-ancestors 'none'; base-uri 'none'; "
    "form-action 'none'"
)
# Nada fiscal: ni QR, ni frase VERI*FACTU, ni dirección de cotejo (FR-029; F-13)
FISCALES = ("QR tributario", FRASE_VERIFACTU, "VERI*FACTU", "aeat.es", "agenciatributaria")


@pytest.fixture
async def admin(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> tuple[Usuario, str]:
    usuario = await crear_usuario("admin.presupuestos.pdf", rol=Rol.ADMINISTRADOR)
    return usuario, await iniciar_sesion(client, "admin.presupuestos.pdf")


@pytest.fixture
def csrf(admin: tuple[Usuario, str]) -> str:
    return admin[1]


@pytest.fixture
async def maria(db: AsyncSession, admin: tuple[Usuario, str]) -> Cliente:
    await configurar_facturacion(db)
    return await crear_cliente(db, admin[0].id)


async def _pdf(client: AsyncClient, presupuesto: dict[str, Any], **parametros: str) -> Response:
    return await client.get(f"{URL_PRESUPUESTOS}/{presupuesto['id']}/pdf", params=parametros)


def _texto(pdf: bytes) -> str:
    """Texto de todas las páginas con los espacios (también los duros) normalizados."""
    lector = PdfReader(io.BytesIO(pdf))
    return " ".join(" ".join(p.extract_text().split()) for p in lector.pages)


async def _texto_de(client: AsyncClient, presupuesto: dict[str, Any], **parametros: str) -> str:
    respuesta = await _pdf(client, presupuesto, **parametros)
    assert respuesta.status_code == 200, respuesta.text
    return _texto(respuesta.content)


def _compacto(texto: str) -> str:
    return "".join(texto.split())


def _euros(importe: str) -> str:
    return format_euros(Decimal(importe)).replace(NBSP, " ")


def _fecha(iso: str) -> str:
    return format_fecha(date.fromisoformat(iso))


# ---------------------------------------------------------------------- contenido


async def test_presupuesto_con_titulo_aviso_validez_y_contenido(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)

    texto = await _texto_de(client, presupuesto)

    numero = presupuesto["num_serie"]
    assert numero == f"PRE-{ANIO}-0001"
    for esperado in (
        "PRESUPUESTO",
        AVISO,
        numero,
        _fecha(presupuesto["fecha"]),
        f"VÁLIDO HASTA {_fecha(presupuesto['valido_hasta'])}",  # etiqueta en print-label
        "Joyería Blanco, S.L.",
        "NIF B12345674",
        "Calle Mayor, 1",
        "39001 Santander",
        "María López García",
        "NIF 12345678Z",
        "Calle Serrano, 45, 2.º A",
        "28001 Madrid",
        "Anillo de oro blanco con diamantes (talla 14)",
        "Ajuste de pulsera y limpieza ultrasonidos",
        _euros("1200.00"),
        _euros("45.00"),
        _euros("90.00"),
        "Base imponible al 21 %",
        _euros("1290.00"),
        "IVA 21 %",
        _euros("270.90"),
        _euros("1560.90"),
        f"{numero} · Página 1 de 1",
    ):
        assert esperado in texto, esperado
    assert texto.count(AVISO) == 1
    for ausente in (*FISCALES, "ANULADO", "SUSTITUIDO", "CONVERTIDO", "IBAN", "Operación exenta"):
        assert ausente not in texto, ausente


async def test_sin_ningun_elemento_fiscal_ni_en_el_modelo_ni_en_el_html(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)

    modelo = await impresion_presupuestos.build_presupuesto_impreso(
        db, uuid.UUID(presupuesto["id"]), iban=False
    )
    # La hoja de estilos común (con las reglas del QR de la factura) va incrustada: solo el cuerpo
    cuerpo = impresion_presupuestos.html_presupuesto(modelo).split("<body", 1)[1]

    # Sin campo `qr`: mypy impide pintarlo (R-10)
    assert "qr" not in {campo.name for campo in dataclasses.fields(modelo)}
    for ausente in ("<svg", 'id="qr"', "qr-bloque", *FISCALES):
        assert ausente not in cuerpo, ausente
    assert modelo.titulo == "PRESUPUESTO"
    assert modelo.aviso_no_fiscal == AVISO


async def test_caducado_sin_marca(client: AsyncClient, csrf: str, maria: Cliente) -> None:
    presupuesto = await emitir_presupuesto(
        client,
        csrf,
        maria.id,
        fecha=hoy() - timedelta(days=10),
        valido_hasta=hoy() - timedelta(days=1),
    )
    assert presupuesto["estado"] == "caducado"

    texto = await _texto_de(client, presupuesto)

    assert AVISO in texto
    assert f"VÁLIDO HASTA {_fecha(presupuesto['valido_hasta'])}" in texto
    for ausente in ("ANULADO", "SUSTITUIDO", "CONVERTIDO", "CADUCADO", "Caducado"):
        assert ausente not in texto, ausente


async def test_oro_de_inversion_lleva_la_mencion(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    presupuesto = await emitir_presupuesto(
        client, csrf, maria.id, lineas=LINGOTE, oro_inversion=True
    )

    texto = await _texto_de(client, presupuesto)

    assert "Base exenta" in texto
    assert _euros("7450.00") in texto
    assert f"IVA {_euros('0.00')}" in texto
    # pypdf puede separar «Uno.» y «1.º» al extraer: se compara sin espacios
    assert _compacto(MENCION_EXENCION_ORO_INVERSION) in _compacto(texto)
    assert "Base imponible al" not in texto


async def test_cliente_sin_domicilio_sin_lineas_vacias(
    client: AsyncClient, csrf: str, admin: tuple[Usuario, str], db: AsyncSession
) -> None:
    await configurar_facturacion(db)
    cliente = await crear_cliente(db, admin[0].id, con_domicilio=False)
    presupuesto = await emitir_presupuesto(client, csrf, cliente.id)

    modelo = await impresion_presupuestos.build_presupuesto_impreso(
        db, uuid.UUID(presupuesto["id"]), iban=False
    )
    texto = await _texto_de(client, presupuesto)

    assert modelo.destinatario.domicilio == ()
    assert "María López García" in texto
    assert "NIF 12345678Z" in texto
    for ausente in ("Calle Serrano", "Madrid", "None"):
        assert ausente not in texto


async def test_datos_de_la_copia_y_contacto_de_la_configuracion(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)
    config = await configuracion_facturacion.get(db, for_update=True)
    config.emisor_nombre = "Otra Razón Social, S.A."
    config.emisor_telefono = "+34 942 000 000"
    config.emisor_correo = "info@joyeriablanco.es"
    config.emisor_web = "https://www.joyeriablanco.es/"
    maria.nombre = "Nombre Cambiado"
    await db.flush()

    texto = await _texto_de(client, presupuesto)

    assert "Joyería Blanco, S.L." in texto  # copia al emitir (FR-010)
    assert "Otra Razón Social" not in texto
    assert "María López García" in texto
    assert "Nombre Cambiado" not in texto
    assert "+34 942 000 000" in texto  # contacto vigente al imprimir (R-9)
    assert "info@joyeriablanco.es" in texto
    assert "www.joyeriablanco.es" in texto


async def test_pie_de_presupuesto_o_el_de_factura_si_esta_vacio(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)
    config = await configuracion_facturacion.get(db, for_update=True)
    config.pie_factura = "Pie de las facturas."
    config.pie_presupuesto = None
    await db.flush()

    assert "Pie de las facturas." in await _texto_de(client, presupuesto)

    config.pie_presupuesto = "El precio del oro puede variar.\nConsulte condiciones."
    await db.flush()
    texto = await _texto_de(client, presupuesto)

    assert "El precio del oro puede variar. Consulte condiciones." in texto
    assert "Pie de las facturas." not in texto


async def test_iban_solo_si_se_pide_y_lo_tiene(
    client: AsyncClient, csrf: str, admin: tuple[Usuario, str], db: AsyncSession
) -> None:
    await configurar_facturacion(db, iban=IBAN_DEMO)
    cliente = await crear_cliente(db, admin[0].id)
    con_iban = await emitir_presupuesto(client, csrf, cliente.id)
    await configurar_facturacion(db, iban=None)
    sin_iban = await emitir_presupuesto(client, csrf, cliente.id)

    assert "ES91 2100 0418 4502 0005 1332" not in await _texto_de(client, con_iban)
    texto = await _texto_de(client, con_iban, iban="true")
    assert "pago por transferencia" in texto.lower()  # encabezado en mayúsculas (print-heading)
    assert "IBAN ES91 2100 0418 4502 0005 1332" in texto
    texto_sin = await _texto_de(client, sin_iban, iban="true")
    assert "IBAN" not in texto_sin
    assert "pago por transferencia" not in texto_sin.lower()


async def test_sesenta_lineas_en_varias_paginas_con_la_cabecera_repetida(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    lineas = [
        {
            "unidades": "1",
            "descripcion": f"Pieza {i} " + "con descripción larga " * 6,
            "precio_unitario": "10",
        }
        for i in range(60)
    ]
    presupuesto = await emitir_presupuesto(client, csrf, maria.id, lineas=lineas)
    modelo = await impresion_presupuestos.build_presupuesto_impreso(
        db, uuid.UUID(presupuesto["id"]), iban=False
    )

    documento = render.html_a_documento(impresion_presupuestos.html_presupuesto(modelo))
    texto = _texto(documento.write_pdf())

    paginas = len(documento.pages)
    numero = presupuesto["num_serie"]
    assert paginas > 1
    assert f"{numero} · Página 1 de {paginas}" in texto
    assert f"{numero} · Página {paginas} de {paginas}" in texto
    assert texto.upper().count("PRECIO UNITARIO") == paginas  # la cabecera de la tabla se repite
    assert texto.count(AVISO) == 1  # la leyenda, solo en la primera
    assert "Pieza 59" in texto


# ---------------------------------------------------------------- respuesta y errores


async def test_respuesta_pdf_con_nombre_cabeceras_y_metadatos(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)

    respuesta = await _pdf(client, presupuesto)

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/pdf"
    assert respuesta.headers["content-disposition"] == (
        f'inline; filename="{presupuesto["num_serie"]}.pdf"'
    )
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.headers["content-security-policy"] == CSP_PDF
    assert respuesta.content.startswith(b"%PDF")
    metadatos = PdfReader(io.BytesIO(respuesta.content)).metadata
    assert metadatos is not None
    assert metadatos.title == f"Presupuesto {presupuesto['num_serie']}"
    assert metadatos.author == "Joyería Blanco, S.L."


async def test_un_empleado_tambien_imprime(
    client: AsyncClient,
    csrf: str,
    maria: Cliente,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
) -> None:
    presupuesto = await emitir_presupuesto(client, csrf, maria.id)
    await crear_usuario("empleado.presupuestos.pdf")
    await iniciar_sesion(client, "empleado.presupuestos.pdf")

    assert (await _pdf(client, presupuesto)).status_code == 200


async def test_borrador_e_inexistente_responden_404(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    borrador = await crear_borrador_presupuesto(client, csrf, maria.id)

    for identificador in (borrador["id"], str(uuid.uuid4())):
        respuesta = await client.get(f"{URL_PRESUPUESTOS}/{identificador}/pdf")
        assert respuesta.status_code == 404
        assert respuesta.json()["type"] == "/problemas/no-encontrado"


async def test_sin_sesion_401_problema_json(client: AsyncClient) -> None:
    respuesta = await client.get(f"{URL_PRESUPUESTOS}/{uuid.uuid4()}/pdf")

    assert respuesta.status_code == 401
    assert respuesta.headers["content-type"].startswith("application/problem+json")
    assert respuesta.headers["content-security-policy"] == CSP_PDF


async def test_navegacion_404_en_html_con_enlace_a_presupuestos(
    client: AsyncClient, csrf: str
) -> None:
    respuesta = await client.get(
        f"{URL_PRESUPUESTOS}/{uuid.uuid4()}/pdf", headers={"Sec-Fetch-Dest": "document"}
    )

    assert respuesta.status_code == 404
    assert respuesta.headers["content-type"].startswith("text/html")
    assert "El presupuesto no existe." in respuesta.text
    assert 'href="/presupuestos"' in respuesta.text
    assert "La factura no existe" not in respuesta.text
    assert "/problemas/" not in respuesta.text

"""Factura en PDF con su QR tributario (US1; FR-001 a FR-017, FR-027 a FR-029, FR-033).

Las facturas se emiten y corrigen con la API real. El texto del PDF se extrae con pypdf y la
geometría del QR se mide en el árbol de cajas de WeasyPrint (research R-2, R-11).
"""

import io
import logging
import uuid
from datetime import date
from decimal import Decimal
from typing import Any, cast

import pytest
from httpx import AsyncClient, Response
from pypdf import PdfReader
from pypdf.generic import DictionaryObject
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.pdf import plantillas, render
from app.core.tiempo import hoy
from app.domain.exenciones import MENCION_EXENCION_ORO_INVERSION
from app.domain.formato import format_euros, format_fecha
from app.domain.qr import build_cotejo_url
from app.domain.tipos import EntornoAeat, Modalidad, Rol
from app.models import Cliente, Usuario
from app.repositories import configuracion_facturacion, registros
from app.services import impresion
from tests.conftest import CrearUsuario, IniciarSesion
from tests.integration.facturacion_datos import (
    IBAN_DEMO,
    LINGOTE,
    cabeceras,
    configurar_facturacion,
    crear_cliente,
    cuerpo_factura,
)

URL = "/api/v1/facturas"
ANIO = hoy().year
NBSP = " "
FRASE = "Factura verificable en la sede electrónica de la AEAT"
CSP_PDF = (
    "default-src 'none'; object-src 'self'; frame-ancestors 'none'; base-uri 'none'; "
    "form-action 'none'"
)
OTRAS_LINEAS = [
    {"unidades": "1", "descripcion": "Anillo de oro blanco (talla 15)", "precio_unitario": "1100"}
]


@pytest.fixture
async def admin(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> tuple[Usuario, str]:
    usuario = await crear_usuario("admin.impresion", rol=Rol.ADMINISTRADOR)
    return usuario, await iniciar_sesion(client, "admin.impresion")


@pytest.fixture
def csrf(admin: tuple[Usuario, str]) -> str:
    return admin[1]


@pytest.fixture
async def maria(db: AsyncSession, admin: tuple[Usuario, str]) -> Cliente:
    await configurar_facturacion(db)
    return await crear_cliente(db, admin[0].id)


async def _emitir(
    client: AsyncClient,
    csrf: str,
    cliente: Cliente,
    *,
    lineas: list[dict[str, str]] | None = None,
    oro_inversion: bool | None = None,
    fecha: date | None = None,
) -> dict[str, Any]:
    respuesta = await client.post(
        URL,
        json=cuerpo_factura(cliente.id, lineas=lineas, oro_inversion=oro_inversion, fecha=fecha),
        headers=cabeceras(csrf),
    )
    assert respuesta.status_code == 201, respuesta.text
    return dict(respuesta.json())


async def _modificar(
    client: AsyncClient,
    csrf: str,
    factura: dict[str, Any],
    cliente: Cliente,
    *,
    motivo: str,
    causa: str | None = None,
    lineas: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    respuesta = await client.post(
        f"{URL}/{factura['id']}/modificacion",
        json={
            "motivo": motivo,
            "causa": causa,
            "motivo_texto": "Corrección de prueba",
            "cliente_id": str(cliente.id),
            "lineas": OTRAS_LINEAS if lineas is None else lineas,
            "oro_inversion": False,
        },
        headers=cabeceras(csrf),
    )
    assert respuesta.status_code == 201, respuesta.text
    return dict(respuesta.json())


async def _anular(client: AsyncClient, csrf: str, factura: dict[str, Any]) -> None:
    respuesta = await client.post(
        f"{URL}/{factura['id']}/anulacion",
        json={"declaracion_no_debio_emitirse": True, "motivo_texto": "Duplicada"},
        headers=cabeceras(csrf),
    )
    assert respuesta.status_code == 200, respuesta.text


async def _pdf(client: AsyncClient, factura: dict[str, Any], **parametros: str) -> Response:
    return await client.get(f"{URL}/{factura['id']}/pdf", params=parametros)


def _texto(pdf: bytes) -> str:
    """Texto de todas las páginas con los espacios (también los duros) normalizados."""
    lector = PdfReader(io.BytesIO(pdf))
    return " ".join(" ".join(p.extract_text().split()) for p in lector.pages)


async def _texto_de(client: AsyncClient, factura: dict[str, Any], **parametros: str) -> str:
    respuesta = await _pdf(client, factura, **parametros)
    assert respuesta.status_code == 200, respuesta.text
    return _texto(respuesta.content)


def _compacto(texto: str) -> str:
    return "".join(texto.split())


def _euros(importe: str) -> str:
    return format_euros(Decimal(importe)).replace(NBSP, " ")


def _fecha(iso: str) -> str:
    return format_fecha(date.fromisoformat(iso))


# ---------------------------------------------------------------------- contenido


async def test_factura_ordinaria_con_todo_el_contenido_obligatorio(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    factura = await _emitir(client, csrf, maria)

    texto = await _texto_de(client, factura)

    numero = factura["num_serie"]
    assert numero == f"FAC-{ANIO}-0001"
    for esperado in (
        "QR tributario:",
        FRASE,
        "Factura",
        numero,  # FR-003.a
        _fecha(factura["fecha_expedicion"]),  # b
        "Joyería Blanco, S.L.",  # c (emisor)
        "NIF B12345674",  # d
        "Calle Mayor, 1",  # e
        "39001 Santander",
        "María López García",  # c (destinatario)
        "NIF 12345678Z",
        "Calle Serrano, 45, 2.º A",
        "28001 Madrid",
        "Anillo de oro blanco con diamantes (talla 14)",  # f
        "Ajuste de pulsera y limpieza ultrasonidos",
        _euros("1200.00"),
        _euros("45.00"),
        _euros("90.00"),
        "Base imponible al 21 %",  # g
        _euros("1290.00"),
        "IVA 21 %",  # h
        _euros("270.90"),
        _euros("1560.90"),
        f"{numero} · Página 1 de 1",  # FR-011
    ):
        assert esperado in texto, esperado
    assert "Factura rectificativa" not in texto
    assert "fecha de la operación" not in texto.lower()  # i: solo si es distinta
    for ausente in ("ANULADA", "RECTIFICADA", "DUPLICADO", "IBAN", "Operación exenta"):
        assert ausente not in texto


async def test_factura_de_oro_de_inversion_lleva_la_mencion(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    factura = await _emitir(client, csrf, maria, lineas=LINGOTE, oro_inversion=True)

    texto = await _texto_de(client, factura)

    assert "Base exenta" in texto
    assert _euros("7450.00") in texto
    assert f"IVA {_euros('0.00')}" in texto
    # pypdf puede separar «Uno.» y «1.º» al extraer: se compara sin espacios
    assert _compacto(MENCION_EXENCION_ORO_INVERSION) in _compacto(texto)
    assert "Base imponible al" not in texto


async def test_rectificativa_identifica_la_rectificada_y_el_importe_de_la_rectificacion(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    original = await _emitir(client, csrf, maria)
    rectificativa = await _modificar(
        client, csrf, original, maria, motivo="factura_entregada", causa="error_datos"
    )

    texto = await _texto_de(client, rectificativa)

    rectifica = rectificativa["rectifica_a"]
    assert rectificativa["num_serie"] == f"REC-{ANIO}-0001"
    assert "Factura rectificativa" in texto
    assert f"Rectifica a {original['num_serie']} de {_fecha(original['fecha_expedicion'])}" in texto
    assert "Causa: Error en datos o importes de la factura" in texto
    assert "Rectificación por sustitución" in texto
    assert (
        f"Importe de la rectificación: base {_euros(rectifica['base_rectificada'])} "
        f"· IVA {_euros(rectifica['cuota_rectificada'])}"
    ) in texto
    assert "Anillo de oro blanco (talla 15)" in texto
    # La fecha de la operación es la de la original (002, FR-018)
    if rectificativa["fecha_operacion"] != rectificativa["fecha_expedicion"]:
        etiqueta = f"fecha de la operación {_fecha(rectificativa['fecha_operacion'])}"
        assert etiqueta in texto.lower()

    texto_original = await _texto_de(client, original)
    assert f"RECTIFICADA por {rectificativa['num_serie']}" in texto_original


async def test_rectificativa_de_devolucion_total_sin_lineas(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    original = await _emitir(client, csrf, maria)
    devolucion = await _modificar(
        client,
        csrf,
        original,
        maria,
        motivo="factura_entregada",
        causa="devolucion_o_precio",
        lineas=[],
    )

    texto = await _texto_de(client, devolucion)

    assert f"Devolución total de la factura {original['num_serie']}" in texto
    assert "Causa: Devolución, descuento o cambio de precio posterior a la venta" in texto
    assert _euros("0.00") in texto
    assert "Precio unitario" not in texto


async def test_anulada_sin_reemision_y_con_reemision(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    sola = await _emitir(client, csrf, maria)
    await _anular(client, csrf, sola)
    reemitida = await _emitir(client, csrf, maria)
    nueva = await _modificar(client, csrf, reemitida, maria, motivo="no_debio_emitirse")

    texto_sola = await _texto_de(client, sola)
    texto_reemitida = await _texto_de(client, reemitida)

    assert "ANULADA" in texto_sola
    assert "Sustituida por" not in texto_sola
    assert "QR tributario:" in texto_sola  # conserva su QR (Clarifications)
    assert "ANULADA" in texto_reemitida
    assert f"Sustituida por {nueva['num_serie']}" in texto_reemitida


async def test_sustituida_por_apunta_a_la_vigente_actual(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    original = await _emitir(client, csrf, maria)
    primera = await _modificar(
        client, csrf, original, maria, motivo="factura_entregada", causa="error_datos"
    )
    segunda = await _modificar(
        client,
        csrf,
        primera,
        maria,
        motivo="factura_entregada",
        causa="error_datos",
        lineas=[{"unidades": "1", "descripcion": "Otra talla", "precio_unitario": "1000"}],
    )

    texto = await _texto_de(client, original)

    assert f"RECTIFICADA por {segunda['num_serie']}" in texto


async def test_destinatario_extranjero_con_su_tipo_y_pais(
    client: AsyncClient, csrf: str, admin: tuple[Usuario, str], db: AsyncSession
) -> None:
    await configurar_facturacion(db)
    cliente = await crear_cliente(
        db,
        admin[0].id,
        nombre="Jean Dupont",
        numero="X1234567",
        tipo_identificacion="03",
        pais="FR",
    )
    factura = await _emitir(client, csrf, cliente)

    texto = await _texto_de(client, factura)

    assert "Pasaporte X1234567 (Francia)" in texto


async def test_datos_fiscales_de_la_copia_y_contacto_y_pie_de_la_configuracion(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    factura = await _emitir(client, csrf, maria)
    config = await configuracion_facturacion.get(db, for_update=True)
    config.emisor_nombre = "Otra Razón Social, S.A."
    config.emisor_telefono = "+34 942 000 000"
    config.emisor_correo = "info@joyeriablanco.es"
    config.emisor_web = "https://www.joyeriablanco.es/"
    config.pie_factura = "Primera línea del pie.\nSegunda línea del pie."
    maria.nombre = "Nombre Cambiado"
    await db.flush()

    texto = await _texto_de(client, factura)

    assert "Joyería Blanco, S.L." in texto  # copia al emitir (FR-004)
    assert "Otra Razón Social" not in texto
    assert "María López García" in texto
    assert "Nombre Cambiado" not in texto
    assert "+34 942 000 000" in texto  # contacto vigente al imprimir (FR-005)
    assert "info@joyeriablanco.es" in texto
    assert "www.joyeriablanco.es" in texto
    assert "https://" not in texto
    assert "Primera línea del pie. Segunda línea del pie." in texto


async def test_sin_contacto_ni_pie_no_quedan_etiquetas_vacias(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    factura = await _emitir(client, csrf, maria)

    texto = await _texto_de(client, factura)

    for ausente in ("Tel.", "Teléfono", "Correo", "Web", "None"):
        assert ausente not in texto


# ---------------------------------------------------------------- IBAN y duplicado


async def test_iban_solo_si_se_pide_y_la_factura_lo_tiene(
    client: AsyncClient, csrf: str, admin: tuple[Usuario, str], db: AsyncSession
) -> None:
    await configurar_facturacion(db, iban=IBAN_DEMO)
    cliente = await crear_cliente(db, admin[0].id)
    con_iban = await _emitir(client, csrf, cliente)
    await configurar_facturacion(db, iban=None)
    sin_iban = await _emitir(client, csrf, cliente)

    assert "ES91 2100 0418 4502 0005 1332" not in await _texto_de(client, con_iban)
    texto = await _texto_de(client, con_iban, iban="true")
    assert "pago por transferencia" in texto.lower()  # encabezado en mayúsculas (print-heading)
    assert "IBAN ES91 2100 0418 4502 0005 1332" in texto
    texto_sin = await _texto_de(client, sin_iban, iban="true")
    assert "IBAN" not in texto_sin
    assert "pago por transferencia" not in texto_sin.lower()


async def test_duplicado_en_vigente_y_rectificada_y_rechazado_en_anulada(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    vigente = await _emitir(client, csrf, maria)
    rectificada = await _emitir(client, csrf, maria)
    await _modificar(
        client, csrf, rectificada, maria, motivo="factura_entregada", causa="error_datos"
    )
    anulada = await _emitir(client, csrf, maria)
    await _anular(client, csrf, anulada)

    assert "DUPLICADO" in await _texto_de(client, vigente, duplicado="true")
    assert "DUPLICADO" not in await _texto_de(client, vigente)
    texto_rectificada = await _texto_de(client, rectificada, duplicado="true", iban="true")
    assert "DUPLICADO" in texto_rectificada
    assert "RECTIFICADA por" in texto_rectificada
    respuesta = await _pdf(client, anulada, duplicado="true")
    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == "/problemas/duplicado-no-disponible"


# ----------------------------------------------------------------------------- QR


async def test_qr_con_los_valores_del_registro_de_alta(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    factura = await _emitir(client, csrf, maria)
    [alta] = await registros.list_by_factura(db, uuid.UUID(factura["id"]))

    modelo = await impresion.build_factura_impresa(
        db, uuid.UUID(factura["id"]), iban=False, duplicado=False
    )

    assert modelo.qr.url == build_cotejo_url(
        Modalidad.VERIFACTU,
        get_settings().entorno_aeat,
        nif=alta.id_emisor,
        num_serie=alta.num_serie,
        fecha_expedicion=alta.fecha_expedicion,
        importe_total=cast(Decimal, alta.importe_total),
    )
    assert get_settings().entorno_aeat is EntornoAeat.PRUEBAS
    assert modelo.qr.url.startswith("https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR?")
    assert "importe=1560.90" in modelo.qr.url
    assert modelo.qr.frase == FRASE


async def test_modalidad_no_verifactu_sin_frase(
    client: AsyncClient, csrf: str, admin: tuple[Usuario, str], db: AsyncSession
) -> None:
    await configurar_facturacion(db, modalidad="no_verifactu")
    cliente = await crear_cliente(db, admin[0].id)
    factura = await _emitir(client, csrf, cliente)

    modelo = await impresion.build_factura_impresa(
        db, uuid.UUID(factura["id"]), iban=False, duplicado=False
    )
    texto = await _texto_de(client, factura)

    assert "/ValidarQRNoVerifactu?" in modelo.qr.url
    assert modelo.qr.frase is None
    assert "QR tributario:" in texto
    assert FRASE not in texto


def _cajas(caja: Any) -> list[Any]:
    cajas = [caja]
    for hija in getattr(caja, "children", None) or []:
        cajas += _cajas(hija)
    return cajas


def _con_id(pagina: Any, identificador: str) -> list[Any]:
    return [
        c
        for c in _cajas(pagina._page_box)
        if getattr(c, "element", None) is not None and c.element.get("id") == identificador
    ]


MM = 25.4 / 96  # px CSS → mm


async def test_geometria_del_qr_y_tamano_de_sus_textos(
    client: AsyncClient, csrf: str, maria: Cliente, db: AsyncSession
) -> None:
    lineas = [
        {
            "unidades": "1",
            "descripcion": f"Pieza {i} " + "con descripción larga " * 15,
            "precio_unitario": "10",
        }
        for i in range(100)
    ]
    factura = await _emitir(client, csrf, maria, lineas=lineas)
    modelo = await impresion.build_factura_impresa(
        db, uuid.UUID(factura["id"]), iban=False, duplicado=False
    )

    documento = render.html_a_documento(impresion.html_factura(modelo))

    assert len(documento.pages) > 1  # FR-011
    [qr] = _con_id(documento.pages[0], "qr")
    assert 30 <= qr.width * MM <= 40  # FR-014, SC-006
    assert 30 <= qr.height * MM <= 40
    for relleno in (qr.padding_top, qr.padding_right, qr.padding_bottom, qr.padding_left):
        assert relleno * MM >= 2
    assert qr.position_y * MM < 40  # arriba, al principio de la factura (FR-013)
    for pagina in documento.pages[1:]:
        assert _con_id(pagina, "qr") == []
    textos_qr = [
        c
        for c in _cajas(documento.pages[0]._page_box)
        if getattr(c, "element", None) is not None and "qr-texto" in (c.element.get("class") or "")
    ]
    datos = [
        c
        for c in _cajas(documento.pages[0]._page_box)
        if getattr(c, "element", None) is not None
        and "emisor-nombre" in (c.element.get("class") or "")
    ]
    assert len(textos_qr) >= 2
    assert min(c.style["font_size"] for c in textos_qr) >= datos[0].style["font_size"]

    texto = _texto(documento.write_pdf())
    paginas = len(documento.pages)
    assert f"{factura['num_serie']} · Página 1 de {paginas}" in texto
    assert f"{factura['num_serie']} · Página {paginas} de {paginas}" in texto
    assert texto.count("QR tributario:") == 1


def _fuentes(pdf: bytes) -> set[str]:
    nombres: set[str] = set()
    for pagina in PdfReader(io.BytesIO(pdf)).pages:
        recursos = cast("DictionaryObject", pagina["/Resources"].get_object())
        fuentes = cast("DictionaryObject", recursos.get("/Font", DictionaryObject()).get_object())
        for fuente in fuentes.values():
            nombres.add(str(fuente.get_object()["/BaseFont"]).split("+", 1)[-1])
    return nombres


# ---------------------------------------------------------------- respuesta y errores


async def test_respuesta_pdf_con_nombre_cabeceras_y_fuentes(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    factura = await _emitir(client, csrf, maria)

    respuesta = await _pdf(client, factura)

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/pdf"
    assert respuesta.headers["content-disposition"] == (
        f'inline; filename="{factura["num_serie"]}.pdf"'
    )
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.headers["content-security-policy"] == CSP_PDF
    assert respuesta.content.startswith(b"%PDF")
    assert {"Manrope", "Bodoni-Moda"} <= _fuentes(respuesta.content)
    metadatos = PdfReader(io.BytesIO(respuesta.content)).metadata
    assert metadatos is not None
    assert metadatos.title == f"Factura {factura['num_serie']}"


async def test_un_empleado_tambien_imprime(
    client: AsyncClient,
    csrf: str,
    maria: Cliente,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
) -> None:
    factura = await _emitir(client, csrf, maria)
    await crear_usuario("empleado.impresion")
    await iniciar_sesion(client, "empleado.impresion")

    assert (await _pdf(client, factura)).status_code == 200


async def test_borrador_e_inexistente_responden_404(
    client: AsyncClient, csrf: str, maria: Cliente
) -> None:
    borrador = await client.post(
        "/api/v1/borradores-factura",
        json={"fecha_expedicion": hoy().isoformat(), "cliente_id": str(maria.id), "lineas": []},
        headers={"X-CSRF-Token": csrf},
    )
    assert borrador.status_code == 201, borrador.text

    for identificador in (borrador.json()["id"], str(uuid.uuid4())):
        respuesta = await client.get(f"{URL}/{identificador}/pdf")
        assert respuesta.status_code == 404
        assert respuesta.json()["type"] == "/problemas/no-encontrado"


async def test_sin_sesion_401_problema_json(client: AsyncClient) -> None:
    respuesta = await client.get(f"{URL}/{uuid.uuid4()}/pdf")

    assert respuesta.status_code == 401
    assert respuesta.headers["content-type"].startswith("application/problem+json")
    # Caddy no pone la CSP de la SPA en las rutas de PDF: la API la trae también en los errores
    assert respuesta.headers["content-security-policy"] == CSP_PDF


@pytest.mark.parametrize(
    "cabeceras_navegacion",
    [{"Sec-Fetch-Dest": "document"}, {"Accept": "text/html,application/xhtml+xml,*/*;q=0.8"}],
)
async def test_en_una_navegacion_los_errores_son_una_pagina_html(
    client: AsyncClient, cabeceras_navegacion: dict[str, str]
) -> None:
    respuesta = await client.get(f"{URL}/{uuid.uuid4()}/pdf", headers=cabeceras_navegacion)

    assert respuesta.status_code == 401
    assert respuesta.headers["content-type"].startswith("text/html")
    assert "Tu sesión ha caducado" in respuesta.text
    assert 'href="/"' in respuesta.text
    assert "no-autenticado" not in respuesta.text
    assert "/problemas/" not in respuesta.text
    csp = respuesta.headers["content-security-policy"]
    assert csp == (
        f"default-src 'none'; style-src {plantillas.hash_estilo_error()}; "
        "frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    )


async def test_navegacion_404_y_409_en_html(client: AsyncClient, csrf: str, maria: Cliente) -> None:
    anulada = await _emitir(client, csrf, maria)
    await _anular(client, csrf, anulada)
    navegacion = {"Sec-Fetch-Dest": "document"}

    no_existe = await client.get(f"{URL}/{uuid.uuid4()}/pdf", headers=navegacion)
    duplicado = await client.get(
        f"{URL}/{anulada['id']}/pdf", params={"duplicado": "true"}, headers=navegacion
    )

    assert no_existe.status_code == 404
    assert "La factura no existe" in no_existe.text
    assert 'href="/facturas"' in no_existe.text
    assert duplicado.status_code == 409
    assert "anulada" in duplicado.text
    assert duplicado.headers["content-type"].startswith("text/html")


async def test_otras_rutas_siguen_con_problema_json_aunque_sean_navegaciones(
    client: AsyncClient,
) -> None:
    respuesta = await client.get(f"{URL}/{uuid.uuid4()}", headers={"Sec-Fetch-Dest": "document"})

    assert respuesta.headers["content-type"].startswith("application/problem+json")


async def test_los_logs_no_contienen_datos_personales_ni_importes(
    client: AsyncClient, csrf: str, maria: Cliente, caplog: pytest.LogCaptureFixture
) -> None:
    factura = await _emitir(client, csrf, maria)

    with caplog.at_level(logging.DEBUG):
        await _pdf(client, factura, iban="true")

    registro = caplog.text
    assert factura["num_serie"] in registro  # FR-029: el número sí
    for dato in ("María", "López", "12345678Z", "1560", "1.560", "Serrano"):
        assert dato not in registro

"""⚖️ Listado impreso de facturas (US2; FR-018 a FR-023, FR-029; research R-7, R-11).

Todas las filas del filtro, de todas las páginas, en el orden de la pantalla, y los totales de las
vigentes desglosados por tipo de IVA, cuadrados al céntimo. La generación por bloques se prueba
con el tamaño de bloque reducido.
"""

import io
import logging
import re
import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.http import Origen
from app.core.pdf import render
from app.core.tiempo import hoy
from app.domain.formato import format_euros, format_porcentaje, nombre_mes
from app.domain.tipos import Rol
from app.models import Cliente, Usuario
from app.models.borrador_factura import BorradorFactura
from app.services import emision, impresion
from tests.conftest import CrearUsuario, IniciarSesion
from tests.integration.facturacion_datos import (
    LINGOTE,
    cabeceras,
    configurar_facturacion,
    crear_cliente,
)

URL = "/api/v1/facturas"
URL_PDF = f"{URL}/listado/pdf"
ORIGEN = Origen(ip=None, agente="pytest")
ANIO = hoy().year
NUMERO = re.compile(r"(?:FAC|REC)-\d{4}-\d{4,}|Borrador")


@pytest.fixture
async def admin(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> tuple[Usuario, str]:
    usuario = await crear_usuario("admin.listado.pdf", rol=Rol.ADMINISTRADOR)
    return usuario, await iniciar_sesion(client, "admin.listado.pdf")


@pytest.fixture
async def maria(db: AsyncSession, admin: tuple[Usuario, str]) -> Cliente:
    await configurar_facturacion(db)
    return await crear_cliente(db, admin[0].id)


async def _emitir(
    db: AsyncSession,
    actor: Usuario,
    cliente: Cliente,
    precio: str,
    *,
    fecha: date | None = None,
    oro_inversion: bool = False,
    descripcion: str = "Anillo",
) -> None:
    await emision.emit_factura(
        db,
        emision.DatosFactura(
            fecha_expedicion=fecha or hoy(),
            cliente_id=cliente.id,
            lineas=(emision.DatosLinea(Decimal(1), descripcion, Decimal(precio)),),
            oro_inversion=oro_inversion,
        ),
        actor=actor,
        origen=ORIGEN,
        clave=uuid.uuid4(),
    )


async def _muchas(db: AsyncSession, actor: Usuario, cliente: Cliente, cuantas: int) -> None:
    for i in range(cuantas):
        await _emitir(db, actor, cliente, str(10 + i * 7 % 101), descripcion=f"Pieza {i}")


def _paginas(pdf: bytes) -> list[str]:
    return [" ".join(p.extract_text().split()) for p in PdfReader(io.BytesIO(pdf)).pages]


def _texto(pdf: bytes) -> str:
    return " ".join(_paginas(pdf))


def _numeros(pdf: bytes) -> list[str]:
    return NUMERO.findall(_texto(pdf))


async def _pdf(client: AsyncClient, **params: Any) -> bytes:
    respuesta = await client.get(URL_PDF, params=params)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["content-type"] == "application/pdf"
    return respuesta.content


async def _pantalla(client: AsyncClient, **params: Any) -> list[dict[str, Any]]:
    """Todas las filas del listado en pantalla, recorriendo sus páginas de 100."""
    filas: list[dict[str, Any]] = []
    pagina = 1
    while True:
        respuesta = await client.get(URL, params={**params, "pagina": pagina, "tamano": 100})
        assert respuesta.status_code == 200, respuesta.text
        cuerpo = respuesta.json()
        filas += cuerpo["elementos"]
        if len(filas) >= cuerpo["total"]:
            return filas
        pagina += 1


def _etiqueta(fila: dict[str, Any]) -> str:
    return str(fila["num_serie"]) if fila["tipo_documento"] == "factura" else "Borrador"


def _euros(importe: Decimal) -> str:
    return format_euros(importe).replace(" ", " ")


# ---------------------------------------------------------------- filas, orden y filtros


@pytest.mark.parametrize("orden", ["recientes", "antiguas", "total_desc", "total_asc"])
async def test_todas_las_filas_del_filtro_en_el_orden_de_la_pantalla(
    client: AsyncClient,
    db: AsyncSession,
    admin: tuple[Usuario, str],
    maria: Cliente,
    orden: str,
) -> None:
    await _muchas(db, admin[0], maria, 105)

    pdf = await _pdf(client, orden=orden)

    pantalla = await _pantalla(client, orden=orden)
    assert len(pantalla) == 105  # más de una página de pantalla (100 como máximo)
    assert _numeros(pdf) == [_etiqueta(f) for f in pantalla]


async def test_filtros_de_busqueda_anio_y_mes(
    client: AsyncClient, db: AsyncSession, admin: tuple[Usuario, str], maria: Cliente
) -> None:
    carlos = await crear_cliente(db, admin[0].id, nombre="Carlós Martín Ruiz", numero="45678901G")
    await _emitir(db, admin[0], maria, "100", fecha=date(ANIO - 1, 11, 10))
    await _emitir(db, admin[0], carlos, "50", fecha=date(ANIO - 1, 12, 5))
    await _emitir(db, admin[0], maria, "1290")
    await _emitir(db, admin[0], carlos, "10")

    for params in (
        {},
        {"anio": "todos"},
        {"anio": ANIO - 1, "mes": 12},
        {"q": "carlos martin", "anio": "todos"},
        {"q": "45678901", "anio": "todos"},
        {"anio": "todos", "mes": 11},
    ):
        pantalla = await _pantalla(client, **params)
        assert _numeros(await _pdf(client, **params)) == [_etiqueta(f) for f in pantalla], params


async def test_cabecera_con_el_filtro_en_palabras(
    client: AsyncClient, db: AsyncSession, admin: tuple[Usuario, str], maria: Cliente
) -> None:
    await _emitir(db, admin[0], maria, "1290")

    texto = _texto(
        await _pdf(client, q="maria lopez", anio="todos", mes=hoy().month, orden="total_desc")
    )
    por_defecto = _texto(await _pdf(client))

    assert "Listado de facturas" in texto
    assert "Joyería Blanco, S.L." in texto
    assert "Búsqueda: “maria lopez”" in texto
    assert "Año: Todos los años" in texto
    assert f"Mes: {nombre_mes(hoy().month)}" in texto
    assert "Orden: Total mayor" in texto
    assert "1 factura · Generado el" in texto
    assert "Sin búsqueda" in por_defecto
    assert f"Año: {ANIO}" in por_defecto
    assert "Mes: Todos los meses" in por_defecto
    assert "Orden: Más recientes" in por_defecto


# ------------------------------------------------------------------ marcas y totales


async def _corregir(
    client: AsyncClient, csrf: str, factura_id: str, cliente: Cliente, *, anular: bool
) -> None:
    if anular:
        respuesta = await client.post(
            f"{URL}/{factura_id}/anulacion",
            json={"declaracion_no_debio_emitirse": True, "motivo_texto": "Duplicada"},
            headers=cabeceras(csrf),
        )
        assert respuesta.status_code == 200, respuesta.text
        return
    respuesta = await client.post(
        f"{URL}/{factura_id}/modificacion",
        json={
            "motivo": "factura_entregada",
            "causa": "error_datos",
            "motivo_texto": "Talla",
            "cliente_id": str(cliente.id),
            "lineas": [{"unidades": "1", "descripcion": "Otra", "precio_unitario": "1100"}],
            "oro_inversion": False,
        },
        headers=cabeceras(csrf),
    )
    assert respuesta.status_code == 201, respuesta.text


async def test_marcas_y_totales_por_tipo_solo_de_las_vigentes(
    client: AsyncClient, db: AsyncSession, admin: tuple[Usuario, str], maria: Cliente
) -> None:
    actor, csrf = admin
    await _emitir(db, actor, maria, "1290")
    await configurar_facturacion(db, iva="10")
    await _emitir(db, actor, maria, "100")
    await _emitir(
        db, actor, maria, "7450", oro_inversion=True, descripcion=LINGOTE[0]["descripcion"]
    )
    await _emitir(db, actor, maria, "300")  # se anulará
    await _emitir(db, actor, maria, "500")  # se rectificará
    db.add(
        BorradorFactura(
            cliente_id=maria.id,
            fecha_expedicion=hoy(),
            tipo_iva_previsto=Decimal("21.00"),
            base_prevista=Decimal("200.00"),
            cuota_prevista=Decimal("42.00"),
            total_previsto=Decimal("242.00"),
            creado_por_id=actor.id,
            actualizado_por_id=actor.id,
        )
    )
    await db.commit()
    filas = await _pantalla(client)
    por_numero = {f["num_serie"]: f for f in filas if f["num_serie"]}
    await _corregir(client, csrf, por_numero[f"FAC-{ANIO}-0004"]["id"], maria, anular=True)
    await _corregir(client, csrf, por_numero[f"FAC-{ANIO}-0005"]["id"], maria, anular=False)

    pdf = await _pdf(client)
    texto = _texto(pdf)

    # Cuadre calculado aparte con el detalle de cada vigente (FR-021, SC-005)
    pantalla = await _pantalla(client)
    base: dict[str | None, Decimal] = defaultdict(Decimal)
    cuota: dict[str | None, Decimal] = defaultdict(Decimal)
    vigentes = [
        f for f in pantalla if f["tipo_documento"] == "factura" and f["estado"] == "vigente"
    ]
    for fila in vigentes:
        detalle = (await client.get(f"{URL}/{fila['id']}")).json()
        for d in detalle["totales"]["desglose"]:
            base[d["tipo_iva"]] += Decimal(d["base"])
            cuota[d["tipo_iva"]] += Decimal(d["cuota"])
    assert set(base) == {"21.00", "10.00", None}
    for tipo in ("21.00", "10.00"):
        etiqueta = f"IVA {format_porcentaje(Decimal(tipo))}"
        linea = f"{etiqueta} {_euros(base[tipo])} {_euros(cuota[tipo])}"
        assert linea in texto, linea
    assert f"Exenta {_euros(base[None])} {_euros(Decimal('0.00'))}" in texto
    totales = texto[texto.lower().index("totales de las facturas vigentes") :]
    assert totales.index("IVA 21 %") < totales.index("IVA 10 %") < totales.index("Exenta ")
    total_base = sum(base.values(), Decimal(0))
    total_cuota = sum(cuota.values(), Decimal(0))
    assert total_base == sum((Decimal(f["base"]) for f in vigentes), Decimal(0))
    assert total_cuota == sum((Decimal(f["cuota"]) for f in vigentes), Decimal(0))
    assert (
        f"Total ({len(vigentes)} facturas) {_euros(total_base)} {_euros(total_cuota)} "
        f"{_euros(total_base + total_cuota)}"
    ) in texto
    assert "No se suman: 1 borrador, 1 anulada y 1 rectificada" in texto
    # Marcas por fila (FR-019)
    assert "Borrador" in _numeros(pdf)
    assert f"FAC-{ANIO}-0004 Anulada" in texto
    assert f"FAC-{ANIO}-0005 Rectificada" in texto
    assert "Exenta" in texto


async def test_filtro_sin_resultados_genera_el_documento_vacio(
    client: AsyncClient, maria: Cliente
) -> None:
    texto = _texto(await _pdf(client, q="zzzz"))

    assert "No hay facturas con este filtro" in texto
    assert f"Total (0 facturas) {_euros(Decimal(0))}" in texto
    assert "No se suman" not in texto


# ------------------------------------------------------------- límite y bloques (R-7)


async def test_limite_de_filas(
    client: AsyncClient,
    db: AsyncSession,
    admin: tuple[Usuario, str],
    maria: Cliente,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _muchas(db, admin[0], maria, 4)
    monkeypatch.setattr(impresion, "LIMITE_LISTADO_IMPRESO", 3)

    respuesta = await client.get(URL_PDF)
    navegacion = await client.get(URL_PDF, headers={"Sec-Fetch-Dest": "document"})

    assert respuesta.status_code == 422
    problema = respuesta.json()
    assert problema["type"] == "/problemas/listado-demasiado-grande"
    assert problema["limite"] == 3
    assert problema["total"] == 4
    assert "acota el filtro" in problema["detail"].lower()
    assert navegacion.status_code == 422
    assert navegacion.headers["content-type"].startswith("text/html")
    assert "acota el filtro" in navegacion.text.lower()
    monkeypatch.setattr(impresion, "LIMITE_LISTADO_IMPRESO", 4)
    assert (await client.get(URL_PDF)).status_code == 200


async def test_generacion_por_bloques_sin_paginas_a_medias(
    client: AsyncClient,
    db: AsyncSession,
    admin: tuple[Usuario, str],
    maria: Cliente,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _muchas(db, admin[0], maria, 105)
    completo = await _pdf(client)
    monkeypatch.setattr(render, "TAMANO_BLOQUE_LISTADO", 40)

    pdf = await _pdf(client)

    numeros = _numeros(pdf)
    assert numeros == _numeros(completo)
    assert len(numeros) == len(set(numeros)) == 105
    paginas = _paginas(pdf)
    total = len(paginas)
    assert total == len(_paginas(completo))
    for indice, pagina in enumerate(paginas, start=1):
        assert f"Listado de facturas · Página {indice} de {total}" in pagina
    filas = [len(NUMERO.findall(p)) for p in paginas]
    assert all(n == filas[1] for n in filas[1:-1])  # ninguna página intermedia a medias


# ------------------------------------------------------------------ respuesta y errores


async def test_nombre_del_fichero_segun_el_filtro(client: AsyncClient, maria: Cliente) -> None:
    casos = {
        (): f"facturas-{ANIO}.pdf",
        (("anio", "todos"),): "facturas-todos.pdf",
        (("anio", "2025"), ("mes", "3")): "facturas-2025-03.pdf",
    }
    for params, nombre in casos.items():
        respuesta = await client.get(URL_PDF, params=dict(params))
        assert respuesta.status_code == 200
        assert respuesta.headers["content-disposition"] == f'inline; filename="{nombre}"'
        assert respuesta.headers["cache-control"] == "no-store"
        assert "object-src 'self'" in respuesta.headers["content-security-policy"]


async def test_errores_de_sesion_y_validacion(client: AsyncClient, maria: Cliente) -> None:
    invalido = await client.get(URL_PDF, params={"mes": 13})
    client.cookies.clear()
    sin_sesion = await client.get(URL_PDF)

    assert invalido.status_code == 422
    assert invalido.json()["type"] == "/problemas/validacion"
    assert sin_sesion.status_code == 401


async def test_los_logs_no_contienen_la_busqueda(
    client: AsyncClient, maria: Cliente, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        await _pdf(client, q="maria lopez")

    assert "listado" in caplog.text.lower()
    assert "maria" not in caplog.text.lower()

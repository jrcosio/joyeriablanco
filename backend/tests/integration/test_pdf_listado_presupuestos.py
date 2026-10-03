"""⚖️ Listado impreso de presupuestos (005, US5; FR-030, SC-011; contracts/documentos-pdf.md).

Como el de facturas de 003 (`test_pdf_listado.py`): todas las filas del filtro, en el orden de la
pantalla, con sus marcas, y los totales de los pendientes, caducados, en facturación y convertidos
por tipo de IVA, cuadrados al céntimo. Los borradores, los sustituidos y los anulados no se suman.
"""

import io
import logging
import re
import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.http import Origen
from app.core.tiempo import hoy
from app.domain.formato import format_euros, format_porcentaje, nombre_mes
from app.domain.tipos import Rol
from app.models import Cliente, Usuario
from app.services import contenido, impresion_presupuestos, presupuestos
from tests.conftest import CrearUsuario, IniciarSesion
from tests.integration.facturacion_datos import (
    LINGOTE,
    URL_PRESUPUESTOS,
    cabeceras,
    configurar_facturacion,
    crear_borrador_presupuesto,
    crear_cliente,
)

URL_PDF = f"{URL_PRESUPUESTOS}/listado/pdf"
ORIGEN = Origen(ip=None, agente="pytest")
ANIO = hoy().year
NUMERO = re.compile(r"PRE-\d{4}-\d{4,}|Borrador")
SUMADOS = {"pendiente", "caducado", "en_facturacion", "convertido"}


@pytest.fixture
async def admin(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> tuple[Usuario, str]:
    usuario = await crear_usuario("admin.listado.pre", rol=Rol.ADMINISTRADOR)
    return usuario, await iniciar_sesion(client, "admin.listado.pre")


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
    valido_hasta: date | None = None,
    oro_inversion: bool = False,
    descripcion: str = "Anillo",
) -> uuid.UUID:
    fecha = fecha or hoy()
    presupuesto, _ = await presupuestos.emit_presupuesto(
        db,
        presupuestos.DatosPresupuesto(
            fecha=fecha,
            valido_hasta=valido_hasta or fecha + timedelta(days=30),
            cliente_id=cliente.id,
            lineas=(contenido.DatosLinea(Decimal(1), descripcion, Decimal(precio)),),
            oro_inversion=oro_inversion,
        ),
        actor=actor,
        origen=ORIGEN,
        clave=uuid.uuid4(),
    )
    return presupuesto.id


async def _muchos(db: AsyncSession, actor: Usuario, cliente: Cliente, cuantos: int) -> None:
    for i in range(cuantos):
        await _emitir(db, actor, cliente, str(10 + i * 7 % 101), descripcion=f"Pieza {i}")


def _texto(pdf: bytes) -> str:
    return " ".join(" ".join(p.extract_text().split()) for p in PdfReader(io.BytesIO(pdf)).pages)


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
        respuesta = await client.get(
            URL_PRESUPUESTOS, params={**params, "pagina": pagina, "tamano": 100}
        )
        assert respuesta.status_code == 200, respuesta.text
        cuerpo = respuesta.json()
        filas += cuerpo["elementos"]
        if len(filas) >= cuerpo["total"]:
            return filas
        pagina += 1


def _etiqueta(fila: dict[str, Any]) -> str:
    return str(fila["num_serie"]) if fila["tipo_documento"] == "presupuesto" else "Borrador"


def _euros(importe: Decimal) -> str:
    return format_euros(importe).replace(" ", " ")


# ---------------------------------------------------------------- filas, orden y filtros


@pytest.mark.parametrize("orden", ["recientes", "antiguas", "total_desc", "total_asc"])
async def test_todas_las_filas_del_filtro_en_el_orden_de_la_pantalla(
    client: AsyncClient, db: AsyncSession, admin: tuple[Usuario, str], maria: Cliente, orden: str
) -> None:
    await _muchos(db, admin[0], maria, 105)

    pdf = await _pdf(client, orden=orden)

    pantalla = await _pantalla(client, orden=orden)
    assert len(pantalla) == 105
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

    assert "Listado de presupuestos" in texto
    assert "Joyería Blanco, S.L." in texto
    assert "Búsqueda: “maria lopez”" in texto
    assert "Año: Todos los años" in texto
    assert f"Mes: {nombre_mes(hoy().month)}" in texto
    assert "Orden: Total mayor" in texto
    assert "1 presupuesto · Generado el" in texto
    assert "Sin búsqueda" in por_defecto
    assert f"Año: {ANIO}" in por_defecto


# ------------------------------------------------------------------ marcas y totales


async def _post(client: AsyncClient, csrf: str, ruta: str, cuerpo: Any = None) -> Any:
    respuesta = await client.post(
        f"{URL_PRESUPUESTOS}/{ruta}", json=cuerpo, headers=cabeceras(csrf)
    )
    assert respuesta.status_code in (200, 201), respuesta.text
    return respuesta.json()


async def test_marcas_y_totales_por_tipo_de_los_que_se_suman(
    client: AsyncClient, db: AsyncSession, admin: tuple[Usuario, str], maria: Cliente
) -> None:
    actor, csrf = admin
    await _emitir(db, actor, maria, "1290")  # pendiente al 21 %
    caducado = await _emitir(
        db, actor, maria, "80", fecha=hoy() - timedelta(20), valido_hasta=hoy() - timedelta(1)
    )
    en_facturacion = await _emitir(db, actor, maria, "300")
    convertido = await _emitir(db, actor, maria, "450")
    sustituido = await _emitir(db, actor, maria, "500")
    anulado = await _emitir(db, actor, maria, "700")
    await configurar_facturacion(db, iva="10")
    await _emitir(db, actor, maria, "100")  # pendiente al 10 %
    await _emitir(
        db, actor, maria, "7450", oro_inversion=True, descripcion=LINGOTE[0]["descripcion"]
    )
    await crear_borrador_presupuesto(client, csrf, maria.id)
    await _post(client, csrf, f"{en_facturacion}/conversion")
    borrador = await _post(client, csrf, f"{convertido}/conversion")
    emision = await client.post(
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
        headers=cabeceras(csrf),
    )
    assert emision.status_code == 201, emision.text
    nuevo = await _post(
        client,
        csrf,
        f"{sustituido}/modificacion",
        {
            "motivo_texto": "Otro precio",
            "fecha": hoy().isoformat(),
            "valido_hasta": (hoy() + timedelta(30)).isoformat(),
            "cliente_id": str(maria.id),
            "lineas": [{"unidades": "1", "descripcion": "Anillo", "precio_unitario": "550"}],
            "oro_inversion": False,
        },
    )
    await _post(client, csrf, f"{anulado}/anulacion", {"motivo_texto": "Rechazado"})

    pdf = await _pdf(client, anio="todos")
    texto = _texto(pdf)

    # Cuadre calculado aparte con el detalle de cada uno de los que se suman (SC-011)
    pantalla = await _pantalla(client, anio="todos")
    sumados = [
        f for f in pantalla if f["tipo_documento"] == "presupuesto" and f["estado"] in SUMADOS
    ]
    assert {f["estado"] for f in pantalla} == SUMADOS | {"borrador", "sustituido", "anulado"}
    base: dict[str | None, Decimal] = defaultdict(Decimal)
    cuota: dict[str | None, Decimal] = defaultdict(Decimal)
    for fila in sumados:
        detalle = (await client.get(f"{URL_PRESUPUESTOS}/{fila['id']}")).json()
        for d in detalle["totales"]["desglose"]:
            base[d["tipo_iva"]] += Decimal(d["base"])
            cuota[d["tipo_iva"]] += Decimal(d["cuota"])
    assert set(base) == {"21.00", "10.00", None}
    for tipo in ("21.00", "10.00"):
        linea = f"IVA {format_porcentaje(Decimal(tipo))} {_euros(base[tipo])} {_euros(cuota[tipo])}"
        assert linea in texto, linea
    assert f"Exenta {_euros(base[None])} {_euros(Decimal('0.00'))}" in texto
    total_base = sum(base.values(), Decimal(0))
    total_cuota = sum(cuota.values(), Decimal(0))
    assert total_base == sum((Decimal(f["base"]) for f in sumados), Decimal(0))
    assert (
        f"Total ({len(sumados)} presupuestos) {_euros(total_base)} {_euros(total_cuota)} "
        f"{_euros(total_base + total_cuota)}"
    ) in texto
    assert (
        "Totales de los presupuestos pendientes, caducados, en facturación y convertidos".lower()
        in texto.lower()
    )
    assert "No se suman: 1 borrador, 1 sustituido y 1 anulado" in texto
    # Marcas por fila, como en la pantalla
    por_id = {f["id"]: f["num_serie"] for f in pantalla}
    for presupuesto_id, marca in (
        (caducado, "Caducado"),
        (en_facturacion, "En facturación"),
        (convertido, "Convertido"),
        (sustituido, "Sustituido"),
        (anulado, "Anulado"),
    ):
        assert f"{por_id[str(presupuesto_id)]} {marca}" in texto, marca
    assert f"{nuevo['num_serie']} Pendiente" not in texto
    assert "Borrador" in _numeros(pdf)


async def test_filtro_sin_resultados_genera_el_documento_vacio(
    client: AsyncClient, maria: Cliente
) -> None:
    texto = _texto(await _pdf(client, q="zzzz"))

    assert "No hay presupuestos con este filtro" in texto
    assert f"Total (0 presupuestos) {_euros(Decimal(0))}" in texto
    assert "No se suman" not in texto


# ------------------------------------------------------------------- límite y respuesta


async def test_limite_de_filas(
    client: AsyncClient,
    db: AsyncSession,
    admin: tuple[Usuario, str],
    maria: Cliente,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _muchos(db, admin[0], maria, 4)
    monkeypatch.setattr(impresion_presupuestos, "LIMITE_LISTADO_IMPRESO", 3)

    respuesta = await client.get(URL_PDF)
    navegacion = await client.get(URL_PDF, headers={"Sec-Fetch-Dest": "document"})

    assert respuesta.status_code == 422
    problema = respuesta.json()
    assert problema["type"] == "/problemas/listado-demasiado-grande"
    assert problema["limite"] == 3
    assert problema["total"] == 4
    assert "4 presupuestos" in problema["detail"]
    assert navegacion.status_code == 422
    assert navegacion.headers["content-type"].startswith("text/html")
    assert "acota el filtro" in navegacion.text.lower()
    assert 'href="/presupuestos"' in navegacion.text
    monkeypatch.setattr(impresion_presupuestos, "LIMITE_LISTADO_IMPRESO", 4)
    assert (await client.get(URL_PDF)).status_code == 200


async def test_nombre_del_fichero_segun_el_filtro(client: AsyncClient, maria: Cliente) -> None:
    casos = {
        (): f"presupuestos-{ANIO}.pdf",
        (("anio", "todos"),): "presupuestos-todos.pdf",
        (("anio", "2025"), ("mes", "3")): "presupuestos-2025-03.pdf",
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
    assert sin_sesion.status_code == 401


async def test_los_logs_no_contienen_la_busqueda(
    client: AsyncClient, maria: Cliente, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        await _pdf(client, q="maria lopez")

    assert "listado de presupuestos" in caplog.text.lower()
    assert "maria" not in caplog.text.lower()

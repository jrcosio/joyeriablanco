"""Rendimiento de los presupuestos (005; SC-008 y plan). Marca `lento`: `uv run pytest -m lento`.

- SC-008: con 20.000 presupuestos, el p95 de las búsquedas y de los cambios de filtro del listado,
  medido por la API real, por debajo de 1 s. Los presupuestos se insertan de una vez con SQL dentro
  de la transacción del test (se revierte al terminar): el listado solo lee la cabecera.
- El PDF de un presupuesto de 20 líneas, por debajo de 3 s (como la factura de 003).
"""

import statistics
import time
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pdf import render
from app.domain.formato import format_euros
from app.domain.tipos import Rol
from app.services import impresion_presupuestos
from app.services.impresion_comun import (
    ContactoImpreso,
    DesgloseImpreso,
    LineaImpresa,
    ParteImpresa,
)
from tests.conftest import CrearUsuario, IniciarSesion
from tests.integration.facturacion_datos import (
    URL_PRESUPUESTOS,
    configurar_facturacion,
    crear_cliente,
)

pytestmark = pytest.mark.lento
TOTAL = 20_000

# 20.000 presupuestos de dos años y medio, con nombres variados para que la búsqueda trabaje.
_SIEMBRA = text(
    """
    INSERT INTO presupuestos (
        serie, anio, numero, num_serie, fecha, valido_hasta,
        emisor_nif, emisor_nombre, emisor_direccion, emisor_codigo_postal, emisor_localidad,
        cliente_id, dest_nombre, dest_identificacion_pais, dest_identificacion_tipo,
        dest_identificacion_numero, dest_pais, oro_inversion,
        base_total, cuota_total, importe_total, emitido_por_id
    )
    SELECT 'PRE', extract(year FROM f)::int,
           row_number() OVER (PARTITION BY extract(year FROM f) ORDER BY f, g),
           'PRE-' || extract(year FROM f)::int || '-' || lpad(
               (row_number() OVER (PARTITION BY extract(year FROM f) ORDER BY f, g))::text, 4, '0'),
           f, f + 30,
           'B12345674', 'Joyería Blanco, S.L.', 'Calle Mayor, 1', '39001', 'Santander',
           :cliente, (ARRAY['María López García', 'José Martín Ruiz', 'Ana Fernández',
                           'Distribuciones Plata, S.L.', 'Carlos Moreno'])[1 + g % 5],
           'ES', 'NIF', lpad((10000000 + g)::text, 8, '0') || 'Z', 'ES', g % 25 = 0,
           100 + g % 900, CASE WHEN g % 25 = 0 THEN 0 ELSE round((100 + g % 900) * 0.21, 2) END,
           100 + g % 900
               + CASE WHEN g % 25 = 0 THEN 0 ELSE round((100 + g % 900) * 0.21, 2) END,
           :usuario
    FROM generate_series(1, :total) AS g,
         LATERAL (SELECT DATE '2024-11-01' + (g * 900 / :total) AS f) AS fechas
    """
)

TERMINOS = ["maria", "lopez", "martin", "ana", "plata", "2025-00", "0042", "1234", "pre-2026"]
FILTROS: list[dict[str, Any]] = [
    {},
    {"anio": "todos"},
    {"mes": 6},
    {"anio": "todos", "mes": 9},
    {"orden": "antiguas"},
    {"orden": "total_desc"},
    {"orden": "total_asc", "pagina": 5},
    {"anio": "todos", "orden": "recientes", "pagina": 40},
]


def _p95(tiempos: list[float]) -> float:
    return statistics.quantiles(tiempos, n=100)[94]


async def test_busquedas_y_filtros_con_20000_presupuestos_p95_por_debajo_de_1_s(
    client: AsyncClient,
    db: AsyncSession,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
) -> None:
    usuario = await crear_usuario("admin.rendimiento.pre", rol=Rol.ADMINISTRADOR)
    await iniciar_sesion(client, "admin.rendimiento.pre")
    await configurar_facturacion(db)
    cliente = await crear_cliente(db, usuario.id)
    await db.execute(_SIEMBRA, {"cliente": cliente.id, "usuario": usuario.id, "total": TOTAL})
    await db.execute(text("ANALYZE presupuestos"))
    total = (await client.get(URL_PRESUPUESTOS, params={"anio": "todos"})).json()["total"]
    assert total == TOTAL

    consultas = [{**f, "q": t} for t in TERMINOS for f in FILTROS[:2]] + FILTROS * 3
    tiempos: list[float] = []
    for params in consultas:
        inicio = time.perf_counter()
        respuesta = await client.get(URL_PRESUPUESTOS, params=params)
        tiempos.append((time.perf_counter() - inicio) * 1000)
        assert respuesta.status_code == 200, respuesta.text

    p95 = _p95(tiempos)
    print(  # noqa: T201 — informe de la medición (quickstart)
        f"\nListado con {TOTAL} presupuestos ({len(tiempos)} consultas): mediana "
        f"{statistics.median(tiempos):.0f} ms, p95 {p95:.0f} ms, máx. {max(tiempos):.0f} ms"
    )
    assert p95 < 1000


def test_presupuesto_de_20_lineas_en_menos_de_3_segundos_p95() -> None:
    euros = format_euros(Decimal("123.45"))
    modelo = impresion_presupuestos.PresupuestoImpreso(
        titulo=impresion_presupuestos.TITULO,
        aviso_no_fiscal=impresion_presupuestos.AVISO_NO_FISCAL,
        num_serie="PRE-2026-0001",
        fecha="01/10/2026",
        valido_hasta="31/10/2026",
        marcas=(),
        emisor=ParteImpresa("Joyería Blanco, S.L.", "NIF B12345674", ("Calle Mayor, 1",)),
        contacto=ContactoImpreso("+34 942 000 000", "info@joyeriablanco.es", None),
        destinatario=ParteImpresa("María López García", "NIF 12345678Z", ("Madrid",)),
        lineas=tuple(
            LineaImpresa("1", f"Pieza de joyería número {i}", euros, euros) for i in range(20)
        ),
        desglose=(DesgloseImpreso("Base imponible al 21 %", euros, "IVA 21 %", euros),),
        base_total=euros,
        cuota_total=euros,
        importe_total=euros,
        mencion_exencion=None,
        iban=None,
        pie="El precio del oro puede variar.",
    )
    tiempos = []
    for _ in range(20):
        inicio = time.perf_counter()
        render.html_a_pdf(impresion_presupuestos.html_presupuesto(modelo))
        tiempos.append(time.perf_counter() - inicio)

    p95 = statistics.quantiles(tiempos, n=20)[-1]
    print(  # noqa: T201
        f"\nPresupuesto de 20 líneas: p95 {p95:.2f} s, mediana {statistics.median(tiempos):.2f} s"
    )
    assert p95 < 3

"""Presupuestos inalterables y cierres únicos EN LA BD (005: FR-004, FR-020, FR-021, SC-006).

Con `jb_app` fallan por privilegios (42501). Con `jb_owner`, dueño de las tablas, los paran los
triggers de `impedir_modificacion_presupuesto()` (research R-2). Las unicidades y los triggers de
validación son la barrera de concurrencia de la conversión (R-6).
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection

from tests.integration.facturacion_sql import (
    PRIVILEGIO_INSUFICIENTE,
    insertar_factura,
    insertar_usuario_y_cliente,
)
from tests.integration.presupuestos_sql import (
    insertar_borrador_factura,
    insertar_cierre,
    insertar_contenido,
    insertar_presupuesto,
)

MENSAJE = "Los presupuestos emitidos son inalterables"


async def _falla(
    conn: AsyncConnection, sql: str, parametros: dict[str, object] | None = None
) -> DBAPIError:
    with pytest.raises(DBAPIError) as info:
        async with conn.begin_nested():
            await conn.execute(text(sql), parametros or {})
    return info.value


def _sqlstate(error: DBAPIError) -> str | None:
    return getattr(error.orig, "sqlstate", None)


def _restriccion(error: DBAPIError) -> str | None:
    """Nombre de la restricción del error (psycopg `diag`): también lo llevan los triggers."""
    return getattr(getattr(error.orig, "diag", None), "constraint_name", None)


async def _documentos(conn: AsyncConnection) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    usuario, cliente = await insertar_usuario_y_cliente(conn)
    presupuesto = await insertar_presupuesto(conn, usuario, cliente, 1)
    await insertar_contenido(conn, presupuesto)
    otro = await insertar_presupuesto(conn, usuario, cliente, 2)
    await insertar_cierre(conn, otro, usuario, "anulacion")
    return usuario, cliente, presupuesto


MODIFICACIONES = [
    "UPDATE presupuestos SET importe_total = 0",
    "DELETE FROM presupuestos",
    "TRUNCATE presupuestos CASCADE",
    "UPDATE lineas_presupuesto SET importe = 0",
    "DELETE FROM lineas_presupuesto",
    "TRUNCATE lineas_presupuesto",
    "UPDATE desgloses_presupuesto SET cuota = 0",
    "DELETE FROM desgloses_presupuesto",
    "UPDATE cierres_presupuesto SET motivo_texto = 'x'",
    "DELETE FROM cierres_presupuesto",
    "TRUNCATE cierres_presupuesto",
]


@pytest.mark.parametrize("sql", MODIFICACIONES)
async def test_el_rol_de_la_aplicacion_no_puede_modificar(
    conexion: AsyncConnection, sql: str
) -> None:
    await _documentos(conexion)

    error = await _falla(conexion, sql)

    assert _sqlstate(error) == PRIVILEGIO_INSUFICIENTE


@pytest.mark.parametrize("sql", MODIFICACIONES)
async def test_ni_siquiera_el_propietario_puede_modificar(
    conexion_owner: AsyncConnection, sql: str
) -> None:
    await _documentos(conexion_owner)

    error = await _falla(conexion_owner, sql)

    assert MENSAJE in str(error.orig)


async def test_el_contador_admite_la_serie_pre_y_solo_sube(conexion: AsyncConnection) -> None:
    await conexion.execute(
        text("INSERT INTO contadores_factura (serie, anio, ultimo_numero) VALUES ('PRE', 2026, 5)")
    )
    await conexion.execute(
        text("UPDATE contadores_factura SET ultimo_numero = 6 WHERE serie = 'PRE' AND anio = 2026")
    )

    baja = await _falla(
        conexion,
        "UPDATE contadores_factura SET ultimo_numero = 1 WHERE serie = 'PRE' AND anio = 2026",
    )
    otra = await _falla(
        conexion,
        "INSERT INTO contadores_factura (serie, anio, ultimo_numero) VALUES ('XYZ', 2026, 0)",
    )

    assert "solo puede avanzar" in str(baja.orig)
    assert "ck_contadores_factura_serie" in str(otra.orig)


async def test_un_segundo_cierre_choca_con_la_unicidad(conexion: AsyncConnection) -> None:
    usuario, _, presupuesto = await _documentos(conexion)
    await insertar_cierre(conexion, presupuesto, usuario, "anulacion")

    with pytest.raises(DBAPIError) as info:
        async with conexion.begin_nested():
            await insertar_cierre(conexion, presupuesto, usuario, "anulacion")

    assert _restriccion(info.value) == "uq_cierres_presupuesto_presupuesto_id"


@pytest.mark.parametrize(
    ("tipo", "extra"),
    [
        ("anulacion", {"motivo_texto": None}),  # la anulación exige motivo
        ("sustitucion", {}),  # sin presupuesto nuevo
        ("conversion", {}),  # sin factura
        ("conversion", {"motivo_texto": "x", "factura_id": "FACTURA"}),  # con motivo
    ],
)
async def test_el_check_por_tipo_rechaza_las_combinaciones_no_validas(
    conexion: AsyncConnection, tipo: str, extra: dict[str, object]
) -> None:
    usuario, cliente, presupuesto = await _documentos(conexion)
    if extra.get("factura_id") == "FACTURA":
        extra = {**extra, "factura_id": await insertar_factura(conexion, usuario, cliente, 900)}

    with pytest.raises(DBAPIError) as info:
        async with conexion.begin_nested():
            await insertar_cierre(conexion, presupuesto, usuario, tipo, **extra)

    assert "ck_cierres_presupuesto" in str(info.value.orig)


@pytest.mark.parametrize("tipo", ["anulacion", "sustitucion"])
async def test_no_se_cierra_con_un_borrador_de_factura_vinculado(
    conexion: AsyncConnection, tipo: str
) -> None:
    usuario, cliente, presupuesto = await _documentos(conexion)
    await insertar_borrador_factura(conexion, usuario, cliente, presupuesto)
    extra: dict[str, object] = {}
    if tipo == "sustitucion":
        extra["presupuesto_nuevo_id"] = await insertar_presupuesto(conexion, usuario, cliente, 3)

    with pytest.raises(DBAPIError) as info:
        async with conexion.begin_nested():
            await insertar_cierre(conexion, presupuesto, usuario, tipo, **extra)

    assert "El presupuesto está en facturación" in str(info.value.orig)
    assert _restriccion(info.value) == "tg_cierres_presupuesto_en_facturacion"


async def test_la_conversion_si_se_cierra_con_el_borrador_vinculado(
    conexion: AsyncConnection,
) -> None:
    usuario, cliente, presupuesto = await _documentos(conexion)
    await insertar_borrador_factura(conexion, usuario, cliente, presupuesto)
    factura = await insertar_factura(conexion, usuario, cliente, 901)

    await insertar_cierre(conexion, presupuesto, usuario, "conversion", factura_id=factura)

    estado = await conexion.scalar(text("SELECT estado_presupuesto(:p)"), {"p": presupuesto})
    assert estado == "convertido"


async def test_no_se_vincula_un_borrador_a_un_presupuesto_cerrado(
    conexion: AsyncConnection,
) -> None:
    usuario, cliente, presupuesto = await _documentos(conexion)
    await insertar_cierre(conexion, presupuesto, usuario, "anulacion")

    with pytest.raises(DBAPIError) as info:
        async with conexion.begin_nested():
            await insertar_borrador_factura(conexion, usuario, cliente, presupuesto)

    assert "El presupuesto ya está cerrado" in str(info.value.orig)
    assert _restriccion(info.value) == "tg_borradores_factura_presupuesto_cerrado"


async def test_como_mucho_un_borrador_vinculado(conexion: AsyncConnection) -> None:
    usuario, cliente, presupuesto = await _documentos(conexion)
    await insertar_borrador_factura(conexion, usuario, cliente, presupuesto)

    with pytest.raises(DBAPIError) as info:
        async with conexion.begin_nested():
            await insertar_borrador_factura(conexion, usuario, cliente, presupuesto)

    assert _restriccion(info.value) == "uq_borradores_factura_presupuesto_id"


async def test_estado_presupuesto(conexion: AsyncConnection) -> None:
    usuario, cliente, pendiente = await _documentos(conexion)
    en_facturacion = await insertar_presupuesto(conexion, usuario, cliente, 10)
    await insertar_borrador_factura(conexion, usuario, cliente, en_facturacion)
    sustituido = await insertar_presupuesto(conexion, usuario, cliente, 11)
    nuevo = await insertar_presupuesto(conexion, usuario, cliente, 12)
    await insertar_cierre(conexion, sustituido, usuario, "sustitucion", presupuesto_nuevo_id=nuevo)
    anulado = await insertar_presupuesto(conexion, usuario, cliente, 13)
    await insertar_cierre(conexion, anulado, usuario, "anulacion")

    estados = {
        p: await conexion.scalar(text("SELECT estado_presupuesto(:p)"), {"p": p})
        for p in (pendiente, en_facturacion, sustituido, nuevo, anulado)
    }

    assert estados == {
        pendiente: "pendiente",
        en_facturacion: "en_facturacion",
        sustituido: "sustituido",
        nuevo: "pendiente",
        anulado: "anulado",
    }


async def test_la_vista_del_listado(conexion: AsyncConnection) -> None:
    await _documentos(conexion)

    columnas = (await conexion.execute(text("SELECT * FROM v_listado_presupuestos LIMIT 0"))).keys()

    assert list(columnas) == [
        "tipo_documento",
        "id",
        "num_serie",
        "numero",
        "fecha",
        "cliente_nombre",
        "identificacion",
        "base",
        "cuota",
        "total",
        "estado",
        "texto_busqueda",
        "oro_inversion",
        "valido_hasta",
    ]


async def test_el_rol_de_la_aplicacion_si_puede_insertar_y_consultar(
    conexion: AsyncConnection,
) -> None:
    _, _, presupuesto = await _documentos(conexion)

    total = await conexion.scalar(
        text("SELECT importe_total FROM presupuestos WHERE id = :p"), {"p": presupuesto}
    )

    assert total == 121

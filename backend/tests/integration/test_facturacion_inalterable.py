"""Facturas y registros son inalterables EN LA BD (FR-022, SC-005, constitución III, research R-8).

Con `jb_app` fallan por privilegios (42501). Con `jb_owner`, dueño de las tablas, los paran los
triggers de `impedir_modificacion_facturacion()`. El contador solo avanza y no se borra (R-7).
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection

from tests.integration.facturacion_sql import (
    PRIVILEGIO_INSUFICIENTE,
    huella_de_prueba,
    insertar_factura,
    insertar_registro,
    insertar_usuario_y_cliente,
)

MENSAJE = "Los documentos de facturación emitidos son inalterables"


async def _falla(conn: AsyncConnection, sql: str) -> DBAPIError:
    with pytest.raises(DBAPIError) as info:
        async with conn.begin_nested():
            await conn.execute(text(sql))
    return info.value


def _sqlstate(error: DBAPIError) -> str | None:
    return getattr(error.orig, "sqlstate", None)


async def _documentos(conn: AsyncConnection) -> uuid.UUID:
    usuario, cliente = await insertar_usuario_y_cliente(conn)
    factura = await insertar_factura(conn, usuario, cliente, 1)
    await conn.execute(
        text(
            "INSERT INTO lineas_factura (factura_id, orden, unidades, descripcion, "
            "precio_unitario, tipo_iva, importe) VALUES (:f, 1, 1, 'Anillo', 100, 21, 100)"
        ),
        {"f": factura},
    )
    await conn.execute(
        text(
            "INSERT INTO desgloses_factura (factura_id, orden, tipo_iva, clave_regimen, "
            "calificacion_operacion, base, cuota) VALUES (:f, 1, 21, '01', 'S1', 100, 21)"
        ),
        {"f": factura},
    )
    await insertar_registro(
        conn, factura, secuencia=1, huella=huella_de_prueba("1"), huella_anterior=None
    )
    await insertar_registro(
        conn,
        factura,
        secuencia=2,
        huella=huella_de_prueba("2"),
        huella_anterior=huella_de_prueba("1"),
        tipo="anulacion",
    )
    await conn.execute(
        text(
            "INSERT INTO correcciones_factura (factura_id, tipo, motivo, motivo_texto, "
            "registro_anulacion_id, creada_por_id) "
            "SELECT :f, 'anulacion', 'no_debio_emitirse', 'Duplicada', r.id, :u "
            "FROM registros_facturacion r WHERE r.secuencia = 2"
        ),
        {"f": factura, "u": usuario},
    )
    return factura


MODIFICACIONES = [
    "UPDATE facturas SET importe_total = 0",
    "DELETE FROM facturas",
    "TRUNCATE facturas CASCADE",
    "UPDATE lineas_factura SET importe = 0",
    "DELETE FROM lineas_factura",
    "UPDATE desgloses_factura SET cuota = 0",
    "UPDATE desgloses_factura SET operacion_exenta = 'E6'",  # columna de la 0006
    "UPDATE facturas SET emisor_iban = 'ES9121000418450200051332'",  # ídem
    "DELETE FROM desgloses_factura",
    "UPDATE registros_facturacion SET estado_remision = 'pendiente'",
    "DELETE FROM registros_facturacion",
    "TRUNCATE registros_facturacion CASCADE",
    "UPDATE correcciones_factura SET motivo_texto = 'x'",
    "DELETE FROM correcciones_factura",
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


async def test_el_rol_de_la_aplicacion_si_puede_insertar_y_consultar(
    conexion: AsyncConnection,
) -> None:
    factura = await _documentos(conexion)

    total: int = (
        await conexion.execute(
            text("SELECT count(*) FROM registros_facturacion WHERE factura_id = :f"), {"f": factura}
        )
    ).scalar_one()

    assert total == 2  # alta y anulación


async def _contador(conn: AsyncConnection, ultimo: int) -> None:
    await conn.execute(
        text(
            "INSERT INTO contadores_factura (serie, anio, ultimo_numero) "
            "VALUES ('FAC', 2030, :u) ON CONFLICT (serie, anio) DO UPDATE SET ultimo_numero = :u"
        ),
        {"u": ultimo},
    )


BAJAR = "UPDATE contadores_factura SET ultimo_numero = 6 WHERE serie = 'FAC' AND anio = 2030"


async def test_el_contador_no_puede_bajar(conexion: AsyncConnection) -> None:
    await _contador(conexion, 7)

    error = await _falla(conexion, BAJAR)

    assert _sqlstate(error) == PRIVILEGIO_INSUFICIENTE
    assert "solo puede avanzar" in str(error.orig)


async def test_ni_el_propietario_puede_bajar_el_contador(conexion_owner: AsyncConnection) -> None:
    await _contador(conexion_owner, 7)

    error = await _falla(conexion_owner, BAJAR)

    assert "solo puede avanzar" in str(error.orig)


async def test_el_contador_si_puede_avanzar(conexion: AsyncConnection) -> None:
    await _contador(conexion, 7)

    await conexion.execute(
        text("UPDATE contadores_factura SET ultimo_numero = 8 WHERE serie = 'FAC' AND anio = 2030")
    )


async def test_el_contador_no_se_puede_borrar(conexion: AsyncConnection) -> None:
    await _contador(conexion, 7)

    error = await _falla(conexion, "DELETE FROM contadores_factura")

    assert _sqlstate(error) == PRIVILEGIO_INSUFICIENTE


async def test_ni_el_propietario_puede_borrar_el_contador(conexion_owner: AsyncConnection) -> None:
    await _contador(conexion_owner, 7)

    error = await _falla(conexion_owner, "DELETE FROM contadores_factura")

    assert MENSAJE in str(error.orig)


# ------------------------------------------- restricciones de la migración 0006 (R-20, R-21)


async def _factura_sin_desglose(conn: AsyncConnection) -> uuid.UUID:
    usuario, cliente = await insertar_usuario_y_cliente(conn)
    return await insertar_factura(conn, usuario, cliente, 1)


DESGLOSE = (
    "INSERT INTO desgloses_factura (factura_id, orden, tipo_iva, clave_regimen, "
    "calificacion_operacion, operacion_exenta, base, cuota) VALUES "
)


@pytest.mark.parametrize(
    "valores",
    [
        "(:f, 1, NULL, '04', NULL, 'E6', 100, 1)",  # exento con cuota
        "(:f, 1, NULL, '01', NULL, 'E6', 100, 0)",  # exento con la clave 01
        "(:f, 1, 21, '01', 'S1', 'E6', 100, 21)",  # S1 y exención a la vez
        "(:f, 1, NULL, '01', 'S1', NULL, 100, 0)",  # S1 sin tipo
        "(:f, 1, NULL, '04', NULL, NULL, 100, 0)",  # ni calificación ni exención
        "(:f, 1, 21, '04', NULL, 'E6', 100, 0)",  # exento con tipo
        "(:f, 13, 21, '01', 'S1', NULL, 100, 21)",  # F-1 admite de 1 a 12 detalles
        "(:f, 1, 100, '01', 'S1', NULL, 100, 100)",  # tipo fuera de rango
    ],
    ids=[
        "exento-con-cuota",
        "exento-clave-01",
        "s1-y-e6",
        "s1-sin-tipo",
        "sin-calificacion-ni-exencion",
        "exento-con-tipo",
        "orden-13",
        "tipo-100",
    ],
)
async def test_el_desglose_es_sujeto_o_exento_y_nada_mas(
    conexion: AsyncConnection, valores: str
) -> None:
    factura = await _factura_sin_desglose(conexion)

    with pytest.raises(DBAPIError) as info:
        async with conexion.begin_nested():
            await conexion.execute(text(DESGLOSE + valores), {"f": factura})

    assert _sqlstate(info.value) == "23514"  # check_violation


async def test_el_detalle_exento_valido_y_solo_uno_por_factura(conexion: AsyncConnection) -> None:
    factura = await _factura_sin_desglose(conexion)
    exento = "(:f, :o, NULL, '04', NULL, 'E6', 100, 0)"

    await conexion.execute(text(DESGLOSE + exento), {"f": factura, "o": 1})
    with pytest.raises(DBAPIError) as info:
        async with conexion.begin_nested():
            await conexion.execute(text(DESGLOSE + exento), {"f": factura, "o": 2})

    assert _sqlstate(info.value) == "23505"  # uq_desgloses_factura_tipo, NULLS NOT DISTINCT


async def test_la_linea_exenta_no_lleva_tipo(conexion: AsyncConnection) -> None:
    factura = await _factura_sin_desglose(conexion)

    await conexion.execute(
        text(
            "INSERT INTO lineas_factura (factura_id, orden, unidades, descripcion, "
            "precio_unitario, tipo_iva, importe) VALUES (:f, 1, 1, 'Lingote', 7450, NULL, 7450)"
        ),
        {"f": factura},
    )


@pytest.mark.parametrize("tipo", ["-1", "100"])
async def test_el_iva_por_defecto_va_de_0_a_99_99(conexion: AsyncConnection, tipo: str) -> None:
    with pytest.raises(DBAPIError) as info:
        async with conexion.begin_nested():
            await conexion.execute(
                text("UPDATE configuracion_facturacion SET iva_por_defecto = :t"), {"t": tipo}
            )

    assert _sqlstate(info.value) == "23514"


async def test_el_iban_guardado_tiene_la_estructura_de_iso_13616(
    conexion: AsyncConnection,
) -> None:
    await conexion.execute(
        text("UPDATE configuracion_facturacion SET emisor_iban = 'ES9121000418450200051332'")
    )
    with pytest.raises(DBAPIError) as info:
        async with conexion.begin_nested():
            await conexion.execute(
                text("UPDATE configuracion_facturacion SET emisor_iban = 'es91 2100'")
            )

    assert _sqlstate(info.value) == "23514"

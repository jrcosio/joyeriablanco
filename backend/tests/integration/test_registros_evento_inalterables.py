"""Registros de evento y comprobaciones son inalterables EN LA BD (004, data-model, FR-014).

Como en `test_facturacion_inalterable.py`: con `jb_app` fallan por privilegios (42501) y con
`jb_owner` los paran los triggers. La cadena de eventos se valida en la BD
(`validar_encadenamiento_eventos`), y en No VERI*FACTU un registro de facturación sin firma o con un
estado de remisión distinto de `no_aplica` no se puede guardar (R-4, R-14).
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection

from tests.integration.facturacion_sql import (
    PRIVILEGIO_INSUFICIENTE,
    huella_de_prueba,
    insertar_evento,
    insertar_factura,
    insertar_registro,
    insertar_usuario_y_cliente,
)

MENSAJE = "Los documentos de facturación emitidos son inalterables"
VIOLACION_CHECK = "23514"
FECHA_1 = "2026-10-03T10:00:00+02:00"


async def _falla(conn: AsyncConnection, sql: str, **parametros: object) -> DBAPIError:
    with pytest.raises(DBAPIError) as info:
        async with conn.begin_nested():
            await conn.execute(text(sql), parametros)
    return info.value


def _sqlstate(error: DBAPIError) -> str | None:
    return getattr(error.orig, "sqlstate", None)


async def _eventos_y_comprobacion(conn: AsyncConnection) -> None:
    usuario, _ = await insertar_usuario_y_cliente(conn)
    await insertar_evento(conn, secuencia=1, huella=huella_de_prueba("e1"), anterior=None)
    await insertar_evento(
        conn,
        secuencia=2,
        huella=huella_de_prueba("e2"),
        anterior=("01", FECHA_1, huella_de_prueba("e1")),
        tipo_evento="03",
    )
    await conn.execute(
        text(
            "INSERT INTO comprobaciones_integridad (origen, actor_id, llega_al_final, registros, "
            "eventos, anomalias, evento_lanzamiento_id) "
            "SELECT 'web', :u, true, 0, 1, 0, id FROM registros_evento WHERE secuencia = 2"
        ),
        {"u": usuario},
    )


MODIFICACIONES = [
    "UPDATE registros_evento SET certificado_titular = 'Otro'",
    "UPDATE registros_evento SET xml_firmado = '<y/>'::bytea",
    "DELETE FROM registros_evento WHERE secuencia = 2",
    "TRUNCATE registros_evento CASCADE",
    "UPDATE comprobaciones_integridad SET anomalias = 0",
    "DELETE FROM comprobaciones_integridad",
    "TRUNCATE comprobaciones_integridad",
]


@pytest.mark.parametrize("sql", MODIFICACIONES)
async def test_el_rol_de_la_aplicacion_no_puede_modificar(
    conexion: AsyncConnection, sql: str
) -> None:
    await _eventos_y_comprobacion(conexion)

    error = await _falla(conexion, sql)

    assert _sqlstate(error) == PRIVILEGIO_INSUFICIENTE


@pytest.mark.parametrize("sql", MODIFICACIONES)
async def test_ni_siquiera_el_propietario_puede_modificar(
    conexion_owner: AsyncConnection, sql: str
) -> None:
    await _eventos_y_comprobacion(conexion_owner)

    error = await _falla(conexion_owner, sql)

    assert MENSAJE in str(error.orig)


async def test_el_rol_de_la_aplicacion_si_puede_insertar_y_consultar(
    conexion: AsyncConnection,
) -> None:
    await _eventos_y_comprobacion(conexion)

    total: int = (
        await conexion.execute(text("SELECT count(*) FROM registros_evento"))
    ).scalar_one()

    assert total == 2


# ⚖️ Constitución VII (2.4.0): la cadena de eventos se valida también en la BD.


async def test_el_primer_evento_debe_ser_el_1_y_marcarse_como_primero(
    conexion: AsyncConnection,
) -> None:
    with pytest.raises(DBAPIError, match="primer evento"):
        async with conexion.begin_nested():
            await insertar_evento(
                conexion, secuencia=2, huella=huella_de_prueba("x"), anterior=None
            )


@pytest.mark.parametrize(
    ("secuencia", "anterior"),
    [
        (3, ("01", FECHA_1, huella_de_prueba("e1"))),  # hueco
        (2, ("01", FECHA_1, huella_de_prueba("otra"))),  # huella anterior incorrecta
        (2, ("02", FECHA_1, huella_de_prueba("e1"))),  # tipo anterior incorrecto
        (2, ("01", "2026-10-03T10:00:01+02:00", huella_de_prueba("e1"))),  # fecha anterior
        (2, None),  # un segundo «primer evento»
    ],
    ids=["hueco", "huella-anterior", "tipo-anterior", "fecha-anterior", "dos-primeros"],
)
async def test_un_evento_que_no_encadena_se_rechaza(
    conexion: AsyncConnection, secuencia: int, anterior: tuple[str, str, str] | None
) -> None:
    await insertar_evento(conexion, secuencia=1, huella=huella_de_prueba("e1"), anterior=None)

    with pytest.raises(DBAPIError, match="no encadena"):
        async with conexion.begin_nested():
            await insertar_evento(
                conexion, secuencia=secuencia, huella=huella_de_prueba("e2"), anterior=anterior
            )


async def test_una_deteccion_lleva_su_tipo_de_anomalia(conexion: AsyncConnection) -> None:
    await insertar_evento(conexion, secuencia=1, huella=huella_de_prueba("e1"), anterior=None)

    with pytest.raises(DBAPIError, match="ck_registros_evento_anomalia"):
        async with conexion.begin_nested():
            await insertar_evento(
                conexion,
                secuencia=2,
                huella=huella_de_prueba("e2"),
                anterior=("01", FECHA_1, huella_de_prueba("e1")),
                tipo_evento="04",
            )


# ------------------------------------------- registros de facturación en No VERI*FACTU (R-4)


async def _factura(conn: AsyncConnection) -> uuid.UUID:
    usuario, cliente = await insertar_usuario_y_cliente(conn)
    return await insertar_factura(conn, usuario, cliente, 1)


async def test_en_no_verifactu_un_registro_sin_firma_no_se_guarda(
    conexion: AsyncConnection,
) -> None:
    factura = await _factura(conexion)

    with pytest.raises(DBAPIError, match="ck_registros_facturacion_firma") as info:
        async with conexion.begin_nested():
            await insertar_registro(
                conexion,
                factura,
                secuencia=1,
                huella=huella_de_prueba("1"),
                huella_anterior=None,
                modalidad="no_verifactu",
                estado_remision="no_aplica",
            )
    assert _sqlstate(info.value) == VIOLACION_CHECK


async def test_en_no_verifactu_el_estado_de_remision_es_no_aplica(
    conexion: AsyncConnection,
) -> None:
    factura = await _factura(conexion)

    with pytest.raises(DBAPIError, match="ck_registros_facturacion_estado_remision"):
        async with conexion.begin_nested():
            await insertar_registro(
                conexion,
                factura,
                secuencia=1,
                huella=huella_de_prueba("1"),
                huella_anterior=None,
                modalidad="no_verifactu",
                xml_firmado=b"<x/>",
            )


async def test_en_no_verifactu_un_registro_firmado_si_se_guarda(
    conexion: AsyncConnection,
) -> None:
    factura = await _factura(conexion)

    await insertar_registro(
        conexion,
        factura,
        secuencia=1,
        huella=huella_de_prueba("1"),
        huella_anterior=None,
        modalidad="no_verifactu",
        estado_remision="no_aplica",
        xml_firmado=b"<x/>",
    )

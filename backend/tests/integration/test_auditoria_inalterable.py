"""La auditoría es inalterable también en la BD (FR-022, FR-047, SC-007, research R-10)."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection

PRIVILEGIO_INSUFICIENTE = "42501"


async def _insertar_evento(conn: AsyncConnection) -> None:
    await conn.execute(text("INSERT INTO eventos_auditoria (tipo) VALUES ('acceso_fallido')"))


async def _falla(conn: AsyncConnection, sql: str) -> DBAPIError:
    with pytest.raises(DBAPIError) as info:
        async with conn.begin_nested():
            await conn.execute(text(sql))
    return info.value


def _sqlstate(error: DBAPIError) -> str | None:
    return getattr(error.orig, "sqlstate", None)


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE eventos_auditoria SET tipo = 'acceso_correcto'",
        "DELETE FROM eventos_auditoria",
        "TRUNCATE eventos_auditoria",
    ],
)
async def test_rol_app_no_puede_modificar_la_auditoria(conexion: AsyncConnection, sql: str) -> None:
    await _insertar_evento(conexion)

    error = await _falla(conexion, sql)

    assert _sqlstate(error) == PRIVILEGIO_INSUFICIENTE


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE eventos_auditoria SET tipo = 'acceso_correcto'",
        "DELETE FROM eventos_auditoria",
        "TRUNCATE eventos_auditoria",
    ],
)
async def test_ni_siquiera_el_propietario_puede_modificar_la_auditoria(
    conexion_owner: AsyncConnection, sql: str
) -> None:
    await _insertar_evento(conexion_owner)

    error = await _falla(conexion_owner, sql)

    assert "La auditoría es inalterable" in str(error.orig)


async def test_rol_app_si_puede_insertar_y_consultar(conexion: AsyncConnection) -> None:
    await _insertar_evento(conexion)

    total: int = (
        await conexion.execute(text("SELECT count(*) FROM eventos_auditoria"))
    ).scalar_one()

    assert total >= 1


@pytest.mark.parametrize(
    "sql",
    [
        "CREATE TABLE intrusa (id int)",
        "ALTER TABLE usuarios ADD COLUMN intrusa int",
        "DROP TABLE sesiones",
    ],
)
async def test_rol_app_no_puede_alterar_la_estructura(conexion: AsyncConnection, sql: str) -> None:
    error = await _falla(conexion, sql)

    assert _sqlstate(error) == PRIVILEGIO_INSUFICIENTE

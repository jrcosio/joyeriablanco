"""Los registros técnicos no contienen secretos ni datos personales de clientes (FR-053)."""

import io
import logging
from collections.abc import Iterator

import pytest
from httpx import AsyncClient
from pythonjsonlogger.json import JsonFormatter

from app.core.logging import RedactionFilter
from tests.conftest import CONTRASENA_VALIDA, CrearUsuario

NIF = "12345678Z"
CORREO = "maria.lopez@example.com"
TELEFONO = "675 432 198"
DIRECCION = "Calle Larios 5"


@pytest.fixture
def salida_logs() -> Iterator[io.StringIO]:
    """Captura los logs con el mismo formateador y filtro que producción."""
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    handler.addFilter(RedactionFilter())
    # El cliente HTTP de las pruebas (httpx) no forma parte del servidor.
    handler.addFilter(lambda registro: not registro.name.startswith(("httpx", "httpcore")))
    raiz = logging.getLogger()
    nivel = raiz.level
    raiz.addHandler(handler)
    raiz.setLevel(logging.DEBUG)
    try:
        yield buffer
    finally:
        raiz.removeHandler(handler)
        raiz.setLevel(nivel)


async def test_login_y_clientes_no_dejan_datos_sensibles_en_los_logs(
    client: AsyncClient, crear_usuario: CrearUsuario, salida_logs: io.StringIO
) -> None:
    await crear_usuario("ana.garcia")
    login = await client.post(
        "/api/v1/sesion", json={"nombre_usuario": "ana.garcia", "contrasena": CONTRASENA_VALIDA}
    )
    csrf = login.json()["csrf_token"]
    cookie = login.cookies.get("__Host-jb_sesion") or ""
    client.headers["X-CSRF-Token"] = csrf
    await client.post(
        "/api/v1/sesion", json={"nombre_usuario": "ana.garcia", "contrasena": "incorrecta-123"}
    )
    creado = await client.post(
        "/api/v1/clientes",
        json={
            "tipo": "particular",
            "nombre": "María López García",
            "identificacion_pais": "ES",
            "identificacion_tipo": "NIF",
            "identificacion_numero": NIF,
            "direccion": DIRECCION,
            "pais_residencia": "ES",
            "telefono": TELEFONO,
            "correo": CORREO,
        },
    )
    await client.get("/api/v1/clientes", params={"q": NIF})
    await client.put(
        f"/api/v1/clientes/{creado.json()['id']}",
        json={
            "tipo": "particular",
            "nombre": "María López García",
            "identificacion_pais": "ES",
            "identificacion_tipo": "NIF",
            "identificacion_numero": NIF,
            "pais_residencia": "ES",
            "correo": "otro@example.com",
            "version": 1,
        },
    )

    registros = salida_logs.getvalue()
    assert registros, "Se esperaba al menos el log de acceso de cada petición"
    for sensible in (
        CONTRASENA_VALIDA,
        "incorrecta-123",
        csrf,
        cookie,
        NIF,
        CORREO,
        "otro@example.com",
        TELEFONO,
        DIRECCION,
        "María López",
    ):
        assert sensible, "El valor sensible de la prueba no puede estar vacío"
        assert sensible not in registros, f"Dato sensible en los logs: {sensible!r}"
    assert "/api/v1/clientes" in registros  # el acceso se registra, sin query string

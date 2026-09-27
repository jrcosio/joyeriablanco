"""GET /api/salud: público y sin detalles internos (FR-049)."""

from httpx import AsyncClient


async def test_salud_responde_ok_sin_autenticacion(client: AsyncClient) -> None:
    respuesta = await client.get("/api/salud")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok"}


async def test_salud_no_expone_versiones(client: AsyncClient) -> None:
    respuesta = await client.get("/api/salud")

    assert "version" not in respuesta.text.lower()
    assert "x-powered-by" not in {c.lower() for c in respuesta.headers}


async def test_ruta_inexistente_devuelve_problema_en_espanol(client: AsyncClient) -> None:
    respuesta = await client.get("/api/v1/no-existe")

    assert respuesta.status_code == 404
    assert respuesta.headers["content-type"].startswith("application/problem+json")
    assert respuesta.json()["type"] == "/problemas/no-encontrado"

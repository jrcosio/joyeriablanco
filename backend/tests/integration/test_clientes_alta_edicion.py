"""Alta y edición de clientes (US2; FR-023 a FR-030, FR-055)."""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.tipos import TipoEvento
from tests.conftest import CrearUsuario, IniciarSesion, eventos

URL = "/api/v1/clientes"


def cliente(**cambios: Any) -> dict[str, Any]:
    datos: dict[str, Any] = {
        "tipo": "particular",
        "nombre": "María López García",
        "identificacion_pais": "ES",
        "identificacion_tipo": "NIF",
        "identificacion_numero": "12345678Z",
        "direccion": "Calle Larios 5",
        "codigo_postal": "29005",
        "localidad": "Málaga",
        "pais_residencia": "ES",
        "telefono": "+34 675 432 198",
        "correo": "Maria.Lopez@Gmail.com",
        "observaciones": "Talla de anillo 14",
    }
    datos.update(cambios)
    return datos


@pytest.fixture
async def csrf(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> str:
    await crear_usuario("ana.garcia", nombre="Ana García")
    token = await iniciar_sesion(client, "ana.garcia")
    client.headers["X-CSRF-Token"] = token
    return token


def errores(respuesta: Any) -> dict[str, str]:
    return {e["campo"]: e["mensaje"] for e in respuesta.json().get("errores", [])}


async def test_alta_de_cliente_valido(client: AsyncClient, csrf: str, db: AsyncSession) -> None:
    respuesta = await client.post(URL, json=cliente())

    assert respuesta.status_code == 201, respuesta.text
    creado = respuesta.json()
    assert creado["activo"] is True
    assert creado["version"] == 1
    assert creado["correo"] == "maria.lopez@gmail.com"  # FR-055: en minúsculas
    assert creado["provincia_codigo"] == "29"  # derivada del CP (FR-028)
    assert creado["provincia_nombre"] == "Málaga"
    assert creado["creado_por"]["nombre"] == "Ana García"
    assert creado["actualizado_por"]["nombre"] == "Ana García"
    (evento,) = await eventos(db, TipoEvento.CLIENTE_CREADO)
    assert str(evento.cliente_id) == creado["id"]

    ficha = await client.get(f"{URL}/{creado['id']}")
    assert ficha.status_code == 200
    assert ficha.json()["nombre"] == "María López García"


async def test_la_identificacion_se_normaliza(client: AsyncClient, csrf: str) -> None:
    respuesta = await client.post(URL, json=cliente(identificacion_numero="12.345.678-z"))

    assert respuesta.status_code == 201
    assert respuesta.json()["identificacion_numero"] == "12345678Z"


@pytest.mark.parametrize(
    ("cambios", "campo", "fragmento"),
    [
        ({"identificacion_numero": "12345678A"}, "identificacion_numero", "letra del NIF"),
        ({"identificacion_numero": "I1234567A"}, "identificacion_numero", "Formato de NIF"),
        ({"identificacion_tipo": "02"}, "identificacion_tipo", "no admitido"),
        ({"nombre": "   "}, "nombre", "obligatorio"),
        ({"nombre": "x" * 121}, "nombre", "120"),
        ({"correo": "no-es-un-correo"}, "correo", "Correo electrónico no válido"),
        ({"telefono": "abc12345"}, "telefono", "Teléfono no válido"),
        ({"telefono": "12 34"}, "telefono", "al menos 6 dígitos"),
        ({"codigo_postal": "2900"}, "codigo_postal", "5 dígitos"),
        ({"codigo_postal": "53001"}, "codigo_postal", "ninguna provincia"),
        (
            {"codigo_postal": "29005", "provincia_codigo": "18"},
            "provincia_codigo",
            "no corresponde",
        ),
        ({"pais_residencia": "XX"}, "pais_residencia", "País no válido"),
        ({"tipo": "autonomo"}, "tipo", "Valor no permitido"),
    ],
)
async def test_validaciones_con_mensajes_en_espanol(
    client: AsyncClient, csrf: str, cambios: dict[str, Any], campo: str, fragmento: str
) -> None:
    respuesta = await client.post(URL, json=cliente(**cambios))

    assert respuesta.status_code == 422, respuesta.text
    assert fragmento in errores(respuesta)[campo]


async def test_identificacion_extranjera(client: AsyncClient, csrf: str) -> None:
    nif_iva = await client.post(
        URL,
        json=cliente(
            tipo="empresa",
            nombre="Bijoux de Provence SARL",
            identificacion_pais="FR",
            identificacion_tipo="02",
            identificacion_numero="AB345678901",
            pais_residencia="FR",
            codigo_postal="13001",
            provincia_texto="Bouches-du-Rhône",
            provincia_codigo="29",  # se descarta: no aplica fuera de España
        ),
    )
    pasaporte = await client.post(
        URL,
        json=cliente(
            nombre="John Smith",
            identificacion_pais="US",
            identificacion_tipo="03",
            identificacion_numero="p 1234-5678",
            pais_residencia="US",
            codigo_postal="10001",
        ),
    )

    assert nif_iva.status_code == 201, nif_iva.text
    assert nif_iva.json()["identificacion_numero"] == "FRAB345678901"
    assert nif_iva.json()["provincia_codigo"] is None
    assert nif_iva.json()["provincia_nombre"] == "Bouches-du-Rhône"
    assert pasaporte.status_code == 201, pasaporte.text
    assert pasaporte.json()["identificacion_numero"] == "P12345678"


async def test_espana_admite_pasaporte(client: AsyncClient, csrf: str) -> None:
    respuesta = await client.post(
        URL, json=cliente(identificacion_tipo="03", identificacion_numero="PAB123456")
    )

    assert respuesta.status_code == 201, respuesta.text


async def test_campos_opcionales_vacios_y_espacios(client: AsyncClient, csrf: str) -> None:
    respuesta = await client.post(
        URL,
        json=cliente(
            nombre="  Joyería Serrano  ",
            direccion="   ",
            telefono="",
            correo="",
            observaciones=None,
            codigo_postal=None,
            provincia_codigo="18",
        ),
    )

    assert respuesta.status_code == 201, respuesta.text
    creado = respuesta.json()
    assert creado["nombre"] == "Joyería Serrano"
    assert creado["direccion"] is None
    assert creado["telefono"] is None
    assert creado["correo"] is None
    assert creado["provincia_nombre"] == "Granada"  # elegida de la lista sin CP


async def test_duplicado_indica_el_cliente_existente(client: AsyncClient, csrf: str) -> None:
    primero = (await client.post(URL, json=cliente())).json()

    respuesta = await client.post(
        URL, json=cliente(nombre="Otra persona", identificacion_numero="12345678-Z")
    )

    assert respuesta.status_code == 409
    cuerpo = respuesta.json()
    assert cuerpo["type"] == "/problemas/duplicado"
    assert cuerpo["cliente_existente"] == {
        "id": primero["id"],
        "nombre": "María López García",
        "activo": True,
    }


async def test_edicion_con_version_y_auditoria_de_cambios(
    client: AsyncClient, csrf: str, db: AsyncSession
) -> None:
    creado = (await client.post(URL, json=cliente())).json()

    respuesta = await client.put(
        f"{URL}/{creado['id']}",
        json=cliente(localidad="Torremolinos", codigo_postal="29620", version=1),
    )

    assert respuesta.status_code == 200, respuesta.text
    editado = respuesta.json()
    assert editado["version"] == 2
    assert editado["localidad"] == "Torremolinos"
    (evento,) = await eventos(db, TipoEvento.CLIENTE_EDITADO)
    assert evento.detalle["cambios"] == {
        "localidad": ["Málaga", "Torremolinos"],
        "codigo_postal": ["29005", "29620"],
    }


async def test_edicion_con_version_desfasada_da_conflicto(client: AsyncClient, csrf: str) -> None:
    creado = (await client.post(URL, json=cliente())).json()
    await client.put(f"{URL}/{creado['id']}", json=cliente(localidad="Ronda", version=1))

    respuesta = await client.put(
        f"{URL}/{creado['id']}", json=cliente(localidad="Marbella", version=1)
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == "/problemas/conflicto-version"
    assert respuesta.json()["detail"] == "El cliente ha cambiado desde que lo abriste."


async def test_edicion_sin_cambios_no_audita_ni_cambia_la_version(
    client: AsyncClient, csrf: str, db: AsyncSession
) -> None:
    creado = (await client.post(URL, json=cliente())).json()

    respuesta = await client.put(f"{URL}/{creado['id']}", json=cliente(version=1))

    assert respuesta.json()["version"] == 1
    assert await eventos(db, TipoEvento.CLIENTE_EDITADO) == []


async def test_edicion_no_puede_duplicar_otra_identificacion(
    client: AsyncClient, csrf: str
) -> None:
    await client.post(URL, json=cliente())
    otro = (
        await client.post(
            URL, json=cliente(nombre="Carlos Martín", identificacion_numero="45678901G")
        )
    ).json()

    respuesta = await client.put(
        f"{URL}/{otro['id']}", json=cliente(nombre="Carlos Martín", version=1)
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == "/problemas/duplicado"


async def test_cliente_inexistente(client: AsyncClient, csrf: str) -> None:
    respuesta = await client.get(f"{URL}/0192f0c0-0000-7000-8000-000000000999")

    assert respuesta.status_code == 404


async def test_sin_sesion_no_se_accede_a_clientes(client: AsyncClient) -> None:
    assert (await client.post(URL, json=cliente())).status_code == 401


async def test_catalogos(client: AsyncClient, csrf: str) -> None:
    respuesta = await client.get("/api/v1/catalogos")

    assert respuesta.status_code == 200
    catalogos = respuesta.json()
    assert len(catalogos["provincias"]) == 52
    coruna = next(p for p in catalogos["provincias"] if p["codigo"] == "15")
    assert coruna == {"codigo": "15", "nombre": "Coruña, A", "nombre_visible": "A Coruña"}
    assert "ES" in catalogos["paises"]
    assert "GR" in catalogos["paises_nif_iva"]
    assert "ES" not in catalogos["paises_nif_iva"]
    ambitos = {t["codigo"]: t["ambito"] for t in catalogos["tipos_identificacion"]}
    assert ambitos == {
        "NIF": "solo_espana",
        "02": "paises_nif_iva",
        "03": "cualquiera",
        "04": "fuera_de_espana",
        "05": "fuera_de_espana",
        "06": "fuera_de_espana",
    }

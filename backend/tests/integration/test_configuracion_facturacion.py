"""US1 — Configuración de facturación (FR-001 a FR-004, FR-010, FR-050; research R-5, R-7, R-19)."""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app.core.tiempo import hoy
from app.domain.tipos import Rol, Serie, TipoEvento
from app.repositories import contadores
from tests.conftest import CrearUsuario, IniciarSesion, eventos
from tests.integration.facturacion_sql import (
    huella_de_prueba,
    insertar_factura,
    insertar_registro,
    insertar_usuario_y_cliente,
)

URL = "/api/v1/configuracion/facturacion"
EMISOR = {
    "nombre": "Joyería Blanco, S.L.",
    "nif": "B12345674",
    "direccion": "Calle Mayor, 1",
    "codigo_postal": "39001",
    "localidad": "Santander",
}


async def _admin(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> dict[str, str]:
    await crear_usuario("admin.facturacion", rol=Rol.ADMINISTRADOR)
    return {"X-CSRF-Token": await iniciar_sesion(client, "admin.facturacion")}


def _cuerpo(actual: dict[str, Any], **cambios: Any) -> dict[str, Any]:
    cuerpo = {
        "version": actual["version"],
        "iva_por_defecto": actual["iva_por_defecto"],
        "clave_regimen": actual["clave_regimen"],
        "modalidad": actual["modalidad"],
        "emisor": {k: actual["emisor"][k] for k in EMISOR},
    }
    cuerpo.update(cambios)
    return cuerpo


async def test_valores_iniciales_y_faltan_los_datos_del_emisor(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> None:
    await _admin(client, crear_usuario, iniciar_sesion)

    respuesta = await client.get(URL)

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["iva_por_defecto"] == "21.00"
    assert datos["clave_regimen"] == "01"
    assert datos["modalidad"] is None
    assert all(v is None for k, v in datos["emisor"].items())
    assert datos["emision_posible"] is False
    assert set(datos["faltan"]) == {
        "modalidad",
        "emisor.nombre",
        "emisor.nif",
        "emisor.direccion",
        "emisor.codigo_postal",
        "emisor.localidad",
    }
    assert datos["tipos_iva_admitidos"] == ["0.00", "4.00", "10.00", "21.00"]
    assert datos["modalidad_bloqueada"] is False
    assert datos["proximo_numero"] == f"FAC-{hoy().year}-0001"


async def test_un_empleado_no_accede(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> None:
    await crear_usuario("empleado.fact")
    csrf = await iniciar_sesion(client, "empleado.fact")

    lectura = await client.get(URL)
    escritura = await client.put(URL, json={}, headers={"X-CSRF-Token": csrf})
    contador = await client.post(
        f"{URL}/contador",
        json={"proximo_numero": 10, "motivo": "x", "simular": True},
        headers={"X-CSRF-Token": csrf},
    )

    assert [lectura.status_code, escritura.status_code, contador.status_code] == [403, 403, 403]


async def test_guardar_la_configuracion_completa_y_auditarla(
    client: AsyncClient,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    db: AsyncSession,
) -> None:
    cabeceras = await _admin(client, crear_usuario, iniciar_sesion)
    actual = (await client.get(URL)).json()

    respuesta = await client.put(
        URL,
        json=_cuerpo(actual, iva_por_defecto="10", modalidad="verifactu", emisor=EMISOR),
        headers=cabeceras,
    )

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["iva_por_defecto"] == "10.00"
    assert datos["emisor"]["provincia"] == "Cantabria"  # derivada del código postal
    assert datos["emision_posible"] is True
    assert datos["faltan"] == []
    assert datos["version"] == actual["version"] + 1
    (evento,) = await eventos(db, TipoEvento.CONFIGURACION_FACTURACION_CAMBIADA)
    assert evento.detalle["cambios"]["iva_por_defecto"] == ["21.00", "10.00"]
    assert evento.detalle["cambios"]["modalidad"] == [None, "verifactu"]


@pytest.mark.parametrize(
    ("cambio", "tipo", "campo"),
    [
        ({"iva_por_defecto": "22"}, "tipo-iva-no-admitido", None),
        ({"iva_por_defecto": "5"}, "tipo-iva-no-admitido", None),  # solo hasta 30/09/2024
        ({"iva_por_defecto": 21}, "validacion", "iva_por_defecto"),  # número JSON
        ({"clave_regimen": "12"}, "validacion", "clave_regimen"),  # no está en L8A
        ({"modalidad": "otra"}, "validacion", "modalidad"),
        ({"emisor": {**EMISOR, "nif": "12345678A"}}, "validacion", "emisor.nif"),
        ({"emisor": {**EMISOR, "codigo_postal": "53000"}}, "validacion", "emisor.codigo_postal"),
    ],
)
async def test_validaciones(
    client: AsyncClient,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    cambio: dict[str, Any],
    tipo: str,
    campo: str | None,
) -> None:
    cabeceras = await _admin(client, crear_usuario, iniciar_sesion)
    actual = (await client.get(URL)).json()

    respuesta = await client.put(URL, json=_cuerpo(actual, **cambio), headers=cabeceras)

    assert respuesta.status_code == 422, respuesta.text
    assert respuesta.json()["type"] == f"/problemas/{tipo}"
    if campo:
        assert campo in {e["campo"] for e in respuesta.json()["errores"]}


async def test_version_desfasada(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> None:
    cabeceras = await _admin(client, crear_usuario, iniciar_sesion)
    actual = (await client.get(URL)).json()
    await client.put(URL, json=_cuerpo(actual, iva_por_defecto="10"), headers=cabeceras)

    respuesta = await client.put(URL, json=_cuerpo(actual, iva_por_defecto="4"), headers=cabeceras)

    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == "/problemas/conflicto-version"


async def test_la_modalidad_se_bloquea_cuando_ya_hay_registros(
    client: AsyncClient,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    conexion: AsyncConnection,
) -> None:
    cabeceras = await _admin(client, crear_usuario, iniciar_sesion)
    actual = (await client.get(URL)).json()
    guardada = (
        await client.put(URL, json=_cuerpo(actual, modalidad="verifactu"), headers=cabeceras)
    ).json()
    usuario, cliente = await insertar_usuario_y_cliente(conexion)
    factura = await insertar_factura(conexion, usuario, cliente, 1)
    await insertar_registro(
        conexion, factura, secuencia=1, huella=huella_de_prueba("m"), huella_anterior=None
    )

    lectura = (await client.get(URL)).json()
    cambio = await client.put(
        URL, json=_cuerpo(guardada, modalidad="no_verifactu"), headers=cabeceras
    )
    otro_campo = await client.put(
        URL, json=_cuerpo(guardada, iva_por_defecto="10"), headers=cabeceras
    )

    assert lectura["modalidad_bloqueada"] is True
    assert cambio.status_code == 409
    assert cambio.json()["type"] == "/problemas/modalidad-bloqueada"
    assert otro_campo.status_code == 200  # el resto sí se puede cambiar


# ---------------------------------------------------------------------- contador (FR-010)


async def test_simular_el_ajuste_no_cambia_nada_ni_audita(
    client: AsyncClient,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    db: AsyncSession,
) -> None:
    cabeceras = await _admin(client, crear_usuario, iniciar_sesion)
    anio = hoy().year
    for _ in range(5):
        await contadores.assign_numero(db, Serie.ORDINARIA, anio)

    respuesta = await client.post(
        f"{URL}/contador",
        json={"proximo_numero": 143, "motivo": "Numeración del programa anterior", "simular": True},
        headers=cabeceras,
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {
        "serie": "FAC",
        "anio": anio,
        "ultimo_usado": 5,
        "proximo_numero": 143,
        "numeros_sin_usar": 137,
        "aplicado": False,
    }
    assert await contadores.last_used(db, Serie.ORDINARIA, anio) == 5
    assert await eventos(db, TipoEvento.CONTADOR_AJUSTADO) == []


async def test_aplicar_el_ajuste_audita_con_su_motivo(
    client: AsyncClient,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    db: AsyncSession,
) -> None:
    cabeceras = await _admin(client, crear_usuario, iniciar_sesion)
    anio = hoy().year
    for _ in range(5):
        await contadores.assign_numero(db, Serie.ORDINARIA, anio)

    respuesta = await client.post(
        f"{URL}/contador",
        json={
            "proximo_numero": 143,
            "motivo": "Numeración del programa anterior",
            "simular": False,
        },
        headers=cabeceras,
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["aplicado"] is True
    assert await contadores.assign_numero(db, Serie.ORDINARIA, anio) == 143
    (evento,) = await eventos(db, TipoEvento.CONTADOR_AJUSTADO)
    assert evento.detalle == {
        "serie": "FAC",
        "anio": anio,
        "ultimo_usado": 5,
        "proximo_numero": 143,
        "numeros_sin_usar": 137,
        "motivo": "Numeración del programa anterior",
    }
    assert (await client.get(URL)).json()["proximo_numero"] == f"FAC-{anio}-0144"


@pytest.mark.parametrize("proximo", [5, 6])
async def test_el_ajuste_debe_saltar_al_menos_un_numero(
    client: AsyncClient,
    crear_usuario: CrearUsuario,
    iniciar_sesion: IniciarSesion,
    db: AsyncSession,
    proximo: int,
) -> None:
    cabeceras = await _admin(client, crear_usuario, iniciar_sesion)
    for _ in range(5):
        await contadores.assign_numero(db, Serie.ORDINARIA, hoy().year)

    respuesta = await client.post(
        f"{URL}/contador",
        json={"proximo_numero": proximo, "motivo": "x", "simular": False},
        headers=cabeceras,
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == "/problemas/contador-no-ajustable"


async def test_el_ajuste_exige_motivo(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> None:
    cabeceras = await _admin(client, crear_usuario, iniciar_sesion)

    respuesta = await client.post(
        f"{URL}/contador",
        json={"proximo_numero": 10, "motivo": "   ", "simular": False},
        headers=cabeceras,
    )

    assert respuesta.status_code == 422


# ------------------------------------------------------------------- parámetros del modal


async def test_parametros_para_cualquier_usuario(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> None:
    await crear_usuario("empleada.param")
    await iniciar_sesion(client, "empleada.param")

    respuesta = await client.get("/api/v1/facturas/parametros")

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {
        "iva_por_defecto": "21.00",
        "emision_posible": False,
        "faltan": [
            "modalidad",
            "emisor.nombre",
            "emisor.nif",
            "emisor.direccion",
            "emisor.codigo_postal",
            "emisor.localidad",
        ],
        "proximo_numero": f"FAC-{hoy().year}-0001",
        "hoy": hoy().isoformat(),
        "fecha_minima": None,
    }

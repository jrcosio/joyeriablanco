"""US5 de 004 — Datos del sistema y declaración responsable (FR-027 a FR-029; Orden, art. 15).

La declaración empieza con el título literal y contiene, en el orden del art. 15.1, las letras a)
a l), cada dato precedido del texto que lo describe. Cualquier usuario la consulta y la descarga.
"""

import io
from collections.abc import Iterator

import pytest
from httpx import AsyncClient
from pypdf import PdfReader

from app import __version__
from app.core.config import get_settings
from app.core.pdf.respuestas import CSP_PDF
from tests.conftest import CrearUsuario, IniciarSesion

URL = "/api/v1/sistema"
TITULO = "DECLARACIÓN RESPONSABLE DEL SISTEMA INFORMÁTICO DE FACTURACIÓN"


@pytest.fixture
async def empleada(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> str:
    await crear_usuario("empleada.sistema")
    return await iniciar_sesion(client, "empleada.sistema")


@pytest.fixture
def productor(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("SIF_PRODUCTOR_NOMBRE", "Joyería Blanco, S.L.")
    monkeypatch.setenv("SIF_PRODUCTOR_NIF", "B12345674")
    monkeypatch.setenv("SIF_PRODUCTOR_DIRECCION", "Calle Mayor, 1, 39001 Santander")
    monkeypatch.setenv("SIF_DECLARACION_FECHA", "2026-10-03")
    monkeypatch.setenv("SIF_DECLARACION_LUGAR", "Santander, España")
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


@pytest.mark.usefixtures("empleada", "productor")
async def test_cualquier_usuario_ve_el_sistema_y_la_declaracion(client: AsyncClient) -> None:
    respuesta = await client.get(URL)

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["nombre"] == "Joyería Blanco Gestión"
    assert datos["id_sistema"] == "JB"
    assert datos["version"] == __version__
    assert datos["numero_instalacion"] == "1"
    assert datos["modalidad"] == "no_verifactu"
    assert datos["productor"] == {
        "nombre": "Joyería Blanco, S.L.",
        "nif": "B12345674",
        "direccion": "Calle Mayor, 1, 39001 Santander",
    }
    declaracion = datos["declaracion"]
    assert declaracion["titulo"] == TITULO
    apartados = {a["letra"]: a for a in declaracion["apartados"]}
    assert [a["letra"] for a in declaracion["apartados"]] == list("abcdefghijkl")
    assert apartados["a"]["texto"] == "Nombre del sistema informático"
    assert apartados["a"]["valor"] == "Joyería Blanco Gestión"
    assert apartados["b"]["valor"] == "JB"
    assert apartados["c"]["valor"] == __version__
    assert apartados["e"]["valor"] == "No"  # no funciona exclusivamente como VERI*FACTU
    assert apartados["f"]["valor"] == "No"  # un único obligado tributario
    assert "«VERI*FACTU»" in apartados["g"]["texto"]
    assert apartados["g"]["valor"].startswith("XAdES Enveloped (ETSI EN 319 132), clase EPES")
    assert apartados["h"]["valor"] == "Joyería Blanco, S.L."
    assert apartados["i"]["valor"] == "B12345674"
    assert apartados["j"]["valor"] == "Calle Mayor, 1, 39001 Santander"
    assert apartados["k"]["valor"].startswith(
        f"Joyería Blanco, S.L. hace constar que el sistema informático, en la versión {__version__}"
    )
    assert "artículo 29.2.j) de la Ley 58/2003" in apartados["k"]["valor"]
    assert apartados["l"]["valor"] == "3 de octubre de 2026, Santander, España"


@pytest.mark.usefixtures("empleada")
async def test_sin_fecha_de_suscripcion_lo_dice(client: AsyncClient) -> None:
    datos = (await client.get(URL)).json()

    [l_] = [a for a in datos["declaracion"]["apartados"] if a["letra"] == "l"]
    assert l_["valor"].startswith("Pendiente de suscribir")


@pytest.mark.usefixtures("empleada", "productor")
async def test_la_declaracion_se_descarga_en_pdf(client: AsyncClient) -> None:
    respuesta = await client.get(f"{URL}/declaracion-responsable/pdf")

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/pdf"
    assert respuesta.headers["content-disposition"] == (
        f'inline; filename="declaracion-responsable-{__version__}.pdf"'
    )
    assert respuesta.headers["content-security-policy"] == CSP_PDF
    # Sin espacios: la extracción parte las líneas y separa algunas letras por el interletraje.
    texto = "".join(
        "".join(p.extract_text() for p in PdfReader(io.BytesIO(respuesta.content)).pages).split()
    )
    assert "".join(TITULO.split()) in texto
    assert "A)NOMBREDELSISTEMAINFORMÁTICO" in texto.upper()
    assert "JoyeríaBlanco,S.L." in texto


async def test_sin_sesion_401(client: AsyncClient) -> None:
    assert (await client.get(URL)).status_code == 401
    assert (await client.get(f"{URL}/declaracion-responsable/pdf")).status_code == 401

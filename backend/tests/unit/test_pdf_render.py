"""Infraestructura de impresión: plantillas, fuentes de la marca y limitador (003, R-4, R-5)."""

import io
import time
from typing import cast

import anyio
import jinja2
import pytest
from pypdf import PdfReader
from pypdf.generic import DictionaryObject

from app.core.pdf import plantillas, render

PRUEBA = """{% extends "base.html" %}
{% block titulo %}Prueba{% endblock %}
{% block contenido %}
<h1 class="titulo">{{ titulo }}</h1>
<p class="cifra">{{ importe }}</p>
{% endblock %}
"""


def _fuentes(pdf: bytes) -> set[str]:
    nombres: set[str] = set()
    for pagina in PdfReader(io.BytesIO(pdf)).pages:
        recursos = cast("DictionaryObject", pagina["/Resources"].get_object())
        fuentes = cast("DictionaryObject", recursos.get("/Font", DictionaryObject()).get_object())
        for fuente in fuentes.values():
            base = str(fuente.get_object()["/BaseFont"])
            nombres.add(base.split("+", 1)[-1])
    return nombres


def test_plantilla_minima_genera_pdf_con_las_fuentes_de_la_marca() -> None:
    pdf = render.html_a_pdf(
        plantillas.render_html_desde_texto(
            PRUEBA,
            {"titulo": "Señora María «López» & Hijos", "importe": "1.560,90 €"},
        )
    )

    texto = PdfReader(io.BytesIO(pdf)).pages[0].extract_text()
    assert pdf.startswith(b"%PDF")
    assert "Señora María «López» & Hijos" in texto
    assert "1.560,90" in texto
    assert "€" in texto
    assert _fuentes(pdf) <= {"Manrope", "Bodoni-Moda", "DejaVuSans"}
    assert {"Manrope", "Bodoni-Moda"} <= _fuentes(pdf)


def test_autoescape_y_variables_obligatorias() -> None:
    html = plantillas.render_html_desde_texto(PRUEBA, {"titulo": "<b>x</b>", "importe": "0"})

    assert "&lt;b&gt;x&lt;/b&gt;" in html
    with pytest.raises(jinja2.UndefinedError, match="importe"):
        plantillas.render_html_desde_texto(PRUEBA, {"titulo": "x"})


async def test_el_limitador_serializa_las_generaciones() -> None:
    activas = 0
    maximo = 0

    def lenta() -> bytes:
        nonlocal activas, maximo
        activas += 1
        maximo = max(maximo, activas)
        time.sleep(0.05)
        activas -= 1
        return b"%PDF"

    limitador = anyio.CapacityLimiter(1)
    async with anyio.create_task_group() as grupo:
        for _ in range(3):
            grupo.start_soon(render.en_hilo, lenta, limitador)

    assert maximo == 1

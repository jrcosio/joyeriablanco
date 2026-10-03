"""Rendimiento de la impresión (003, SC-001 y SC-005; research R-7). Marca `lento`.

Se lanza aparte con `uv run pytest -m lento`. Mide el renderizado, que es el coste dominante, con
modelos de vista sintéticos: la consulta del listado es una sola lectura indexada (002, SC-007).
La memoria del listado de 5.000 filas se mide en un proceso aparte, para no contar la del resto de
la batería.
"""

import json
import statistics
import subprocess
import sys
import time
from decimal import Decimal
from pathlib import Path

import pytest
from markupsafe import Markup

from app.core.pdf import render, tokens
from app.domain.formato import format_euros
from app.domain.qr import FRASE_VERIFACTU, qr_svg
from app.services import impresion

pytestmark = pytest.mark.lento
BACKEND = Path(__file__).resolve().parents[2]


def _factura(lineas: int) -> impresion.FacturaImpresa:
    url = (
        "https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR?nif=B12345674"
        "&numserie=FAC-2026-0001&fecha=01-10-2026&importe=1560.90"
    )
    euros = format_euros(Decimal("123.45"))
    return impresion.FacturaImpresa(
        titulo="Factura",
        num_serie="FAC-2026-0001",
        fecha_expedicion="01/10/2026",
        fecha_operacion=None,
        marcas=(),
        qr=impresion.QrImpreso(
            url=url,
            svg=Markup(qr_svg(url, color=tokens.COLORES["paper-qr"])),  # noqa: S704
            frase=FRASE_VERIFACTU,
        ),
        emisor=impresion.ParteImpresa("Joyería Blanco, S.L.", "NIF B12345674", ("Calle Mayor, 1",)),
        contacto=impresion.ContactoImpreso("+34 942 000 000", "info@joyeriablanco.es", None),
        destinatario=impresion.ParteImpresa("María López García", "NIF 12345678Z", ("Madrid",)),
        lineas=tuple(
            impresion.LineaImpresa("1", f"Pieza de joyería número {i}", euros, euros)
            for i in range(lineas)
        ),
        devolucion_total=None,
        desglose=(impresion.DesgloseImpreso("Base imponible al 21 %", euros, "IVA 21 %", euros),),
        base_total=euros,
        cuota_total=euros,
        importe_total=euros,
        mencion_exencion=None,
        rectificacion=None,
        iban=None,
        pie="Gracias por su confianza.",
    )


def test_factura_de_20_lineas_en_menos_de_3_segundos_p95() -> None:
    modelo = _factura(20)
    tiempos = []
    for _ in range(20):
        inicio = time.perf_counter()
        render.html_a_pdf(impresion.html_factura(modelo))
        tiempos.append(time.perf_counter() - inicio)

    p95 = statistics.quantiles(tiempos, n=20)[-1]
    mediana = statistics.median(tiempos)
    print(f"\nFactura de 20 líneas: p95 {p95:.2f} s, mediana {mediana:.2f} s")  # noqa: T201
    assert p95 < 3


_MEDICION = """
import json, resource, sys, time
from tests.integration.test_pdf_rendimiento import listado_sintetico
from app.services.impresion_comun import pdf_listado
modelo = listado_sintetico(int(sys.argv[1]))
inicio = time.perf_counter()
pdf = pdf_listado(modelo)
segundos = time.perf_counter() - inicio
maximo = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
mb = maximo / 1024 / 1024 if sys.platform == "darwin" else maximo / 1024
print(json.dumps({"segundos": segundos, "mb": mb, "bytes": len(pdf)}))
"""


def listado_sintetico(filas: int) -> impresion.ListadoImpreso:
    euros = format_euros(Decimal("1234.56"))
    return impresion.ListadoImpreso(
        emisor_nombre="Joyería Blanco, S.L.",
        filtro=impresion.FiltroImpreso(
            "Sin búsqueda", "Todos los años", "Todos los meses", "Más recientes"
        ),
        resumen=f"{filas} facturas · Generado el 01/10/2026 a las 18:42",
        filas=tuple(
            impresion.FilaImpresa(
                numero=f"FAC-2026-{i:04d}",
                marca="Anulada" if i % 50 == 0 else None,
                fecha="01/10/2026",
                cliente=(
                    f"Cliente {i} con un nombre muy largo que ocupa dos líneas, S.L."
                    if i % 5 == 0
                    else f"Cliente {i}"
                ),
                identificacion="B12345674",
                base=euros,
                iva=euros,
                total=euros,
            )
            for i in range(filas)
        ),
        desglose=(impresion.ImportesImpresos("IVA 21 %", euros, euros, euros),),
        totales=impresion.ImportesImpresos(f"Total ({filas} facturas)", euros, euros, euros),
        excluidas=None,
        nombre_fichero="facturas-todos.pdf",
        textos=impresion.TEXTOS_LISTADO,
    )


def _medir(filas: int) -> dict[str, float]:
    salida = subprocess.run(  # noqa: S603 — el intérprete del propio entorno y un script fijo
        [sys.executable, "-c", _MEDICION, str(filas)],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=True,
    )
    resultado: dict[str, float] = json.loads(salida.stdout.strip().splitlines()[-1])
    return resultado


@pytest.mark.parametrize(("filas", "limite_s"), [(1000, 15), (5000, 60)])
def test_listado_en_tiempo_y_con_la_memoria_acotada(filas: int, limite_s: int) -> None:
    medicion = _medir(filas)

    print(  # noqa: T201 — informe de la medición (quickstart)
        f"\nListado de {filas} filas: {medicion['segundos']:.1f} s, "
        f"{medicion['mb']:.0f} MB de pico, {medicion['bytes'] / 1e6:.2f} MB de PDF"
    )
    assert medicion["segundos"] < limite_s
    # SC-005 («unos 300 MB») se mide en Linux, como el servidor. En macOS el mismo proceso ocupa
    # bastante más (otro asignador de memoria), así que allí solo se vigila que no se dispare.
    assert medicion["mb"] < (300 if sys.platform == "linux" else 600)

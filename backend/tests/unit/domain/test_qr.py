"""⚖️ Dirección de cotejo y símbolo del QR tributario (003, FR-014 a FR-016; research R-1, R-2).

Vectores de F-12 (AEAT, «Detalle de las especificaciones técnicas del código QR…», v0.5.0,
SHA-256 f86b3c26…49eb): §4 (codificación de `&`) y §8.1 a §8.4 (las cuatro direcciones). Los
ejemplos de §8 escriben `importe=241.4`; el sistema escribe siempre dos decimales (`241.40`),
formato `NNNNNNNNN.DD` de §5 y el que devuelve el propio servicio en §9 (research R-1).
"""

from decimal import Decimal
from urllib.parse import parse_qsl, urlsplit

import numpy as np
import pytest
import zxingcpp

from app.domain.qr import build_cotejo_url, qr_simbolo, qr_svg
from app.domain.tipos import EntornoAeat, Modalidad

NIF = "89890001K"


def _url(
    modalidad: Modalidad = Modalidad.VERIFACTU,
    entorno: EntornoAeat = EntornoAeat.PRUEBAS,
    *,
    nif: str = NIF,
    num_serie: str = "12345678-G33",
    fecha: str = "01-09-2024",
    importe: Decimal = Decimal("241.4"),
) -> str:
    return build_cotejo_url(
        modalidad,
        entorno,
        nif=nif,
        num_serie=num_serie,
        fecha_expedicion=fecha,
        importe_total=importe,
    )


@pytest.mark.parametrize(
    ("modalidad", "entorno", "oficial"),
    [
        (  # F-12 §8.1
            Modalidad.VERIFACTU,
            EntornoAeat.PRUEBAS,
            "https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR?nif=89890001K&numserie=12345678-G33"
            "&fecha=01-09-2024&importe=241.4",
        ),
        (  # F-12 §8.2
            Modalidad.NO_VERIFACTU,
            EntornoAeat.PRUEBAS,
            "https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQRNoVerifactu?nif=89890001K"
            "&numserie=12345678-G33&fecha=01-09-2024&importe=241.4",
        ),
        (  # F-12 §8.3
            Modalidad.VERIFACTU,
            EntornoAeat.PRODUCCION,
            "https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR?nif=89890001K"
            "&numserie=12345678-G33&fecha=01-09-2024&importe=241.4",
        ),
        (  # F-12 §8.4
            Modalidad.NO_VERIFACTU,
            EntornoAeat.PRODUCCION,
            "https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQRNoVerifactu"
            "?nif=89890001K&numserie=12345678-G33&fecha=01-09-2024&importe=241.4",
        ),
    ],
)
def test_direcciones_oficiales_de_f12(
    modalidad: Modalidad, entorno: EntornoAeat, oficial: str
) -> None:
    assert _url(modalidad, entorno) == oficial.replace("importe=241.4", "importe=241.40")


def test_codificacion_de_url_f12_seccion_4() -> None:
    url = _url(num_serie="12345678&G33", fecha="01-01-2024")

    assert url == (
        "https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR?nif=89890001K"
        "&numserie=12345678%26G33&fecha=01-01-2024&importe=241.40"
    )
    # El ejemplo erróneo de §4 (con «&» sin codificar) nunca se produce
    assert "numserie=12345678&G33" not in url


def test_solo_los_cuatro_parametros_obligatorios_en_su_orden() -> None:
    url = _url(num_serie="FAC-2026-0005", fecha="05-03-2026", importe=Decimal("1560.9"))

    pares = parse_qsl(urlsplit(url).query, keep_blank_values=True)
    assert [nombre for nombre, _ in pares] == ["nif", "numserie", "fecha", "importe"]
    assert dict(pares) == {
        "nif": NIF,
        "numserie": "FAC-2026-0005",
        "fecha": "05-03-2026",
        "importe": "1560.90",
    }
    assert "idioma" not in url
    assert "formato" not in url


def test_espacio_se_codifica_como_porcentaje_20() -> None:
    assert "numserie=A%20B" in _url(num_serie="A B")


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("nif", "8989000K"),  # 8 caracteres
        ("nif", "89890001KX"),
        ("num_serie", "F" * 61),
        ("num_serie", "FAC-ñ-1"),  # fuera de ASCII 32-126 (F-12 §4)
        ("num_serie", "FAC\t1"),
        ("fecha", "2024-09-01"),
        ("fecha", "1-9-2024"),
        ("importe", Decimal("1234567890123.00")),  # 13 cifras enteras
        ("importe", Decimal("1.005")),
    ],
)
def test_valores_fuera_de_formato_son_un_fallo_interno(campo: str, valor: object) -> None:
    argumentos: dict[str, object] = {
        "nif": NIF,
        "num_serie": "FAC-2026-0001",
        "fecha": "01-09-2024",
        "importe": Decimal("10.00"),
        campo: valor,
    }
    with pytest.raises(ValueError):  # noqa: PT011 — distintos mensajes según el campo
        build_cotejo_url(
            Modalidad.VERIFACTU,
            EntornoAeat.PRUEBAS,
            nif=str(argumentos["nif"]),
            num_serie=str(argumentos["num_serie"]),
            fecha_expedicion=str(argumentos["fecha"]),
            importe_total=argumentos["importe"],  # type: ignore[arg-type]
        )


def test_doce_cifras_enteras_se_admiten() -> None:
    assert "importe=123456789012.34" in _url(importe=Decimal("123456789012.34"))


def _leer(matriz: list[list[int]] | tuple[bytearray, ...]) -> zxingcpp.Barcode:
    pixeles = np.array([[0 if modulo else 255 for modulo in fila] for fila in matriz], np.uint8)
    pixeles = np.pad(pixeles, 4, constant_values=255).repeat(8, axis=0).repeat(8, axis=1)
    [codigo] = zxingcpp.read_barcodes(pixeles)
    return codigo


@pytest.mark.parametrize(
    "url",
    [
        _url(num_serie="FAC-2026-0005", fecha="05-03-2026", importe=Decimal("1560.90")),
        _url(Modalidad.NO_VERIFACTU, EntornoAeat.PRODUCCION, num_serie="REC-2026-0001"),
        _url(num_serie="12345678&G33"),
    ],
)
def test_el_simbolo_se_lee_con_la_url_exacta_y_nivel_m(url: str) -> None:
    simbolo = qr_simbolo(url)

    codigo = _leer(simbolo.matrix)
    assert codigo.text == url
    assert codigo.ec_level == "M"
    assert simbolo.error == "M"  # sin «boost_error» (F-10, art. 21.1)
    assert not simbolo.is_micro


def test_svg_vectorial_sin_tamano_fijo_y_con_el_color_indicado() -> None:
    svg = qr_svg(_url(), color="#000000")

    assert svg.startswith("<svg")
    assert "viewBox" in svg
    assert 'width="' not in svg.split(">", 1)[0]
    assert "#000" in svg

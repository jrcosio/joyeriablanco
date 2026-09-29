"""⚖️ Test obligatorio (constitución VII): encadenamiento de huellas Verifactu.

Vectores oficiales de F-2: AEAT, «Detalle de las especificaciones técnicas para generación de la
huella o hash de los registros de facturación», v0.1.2 (27/08/2024), pp. 10–12,
SHA-256 del PDF f4334c254bb875b417247b54315199f89d75a8c4814dfd1e86efec562653d7de (research R-2).
"""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain.huella import (
    CamposHuellaAlta,
    CamposHuellaAnulacion,
    compute_huella,
    format_amount,
    format_date,
    format_timestamp,
)

# --- Vectores oficiales (copiados literalmente; la cadena real no lleva saltos de línea) ---

CADENA_1 = (
    "IDEmisorFactura=89890001K&NumSerieFactura=12345678/G33&FechaExpedicionFactura=01-01-2024"
    "&TipoFactura=F1&CuotaTotal=12.35&ImporteTotal=123.45&Huella="
    "&FechaHoraHusoGenRegistro=2024-01-01T19:20:30+01:00"
)
HUELLA_1 = "3C464DAF61ACB827C65FDA19F352A4E3BDC2C640E9E9FC4CC058073F38F12F60"

CADENA_2 = (
    "IDEmisorFactura=89890001K&NumSerieFactura=12345679/G34&FechaExpedicionFactura=01-01-2024"
    "&TipoFactura=F1&CuotaTotal=12.35&ImporteTotal=123.45"
    "&Huella=3C464DAF61ACB827C65FDA19F352A4E3BDC2C640E9E9FC4CC058073F38F12F60"
    "&FechaHoraHusoGenRegistro=2024-01-01T19:20:35+01:00"
)
HUELLA_2 = "F7B94CFD8924EDFF273501B01EE5153E4CE8F259766F88CF6ACB8935802A2B97"

CADENA_3 = (
    "IDEmisorFacturaAnulada=89890001K&NumSerieFacturaAnulada=12345679/G34"
    "&FechaExpedicionFacturaAnulada=01-01-2024"
    "&Huella=F7B94CFD8924EDFF273501B01EE5153E4CE8F259766F88CF6ACB8935802A2B97"
    "&FechaHoraHusoGenRegistro=2024-01-01T19:20:40+01:00"
)
HUELLA_3 = "177547C0D57AC74748561D054A9CEC14B4C4EA23D1BEFD6F2E69E3A388F90C68"


def _alta(num: str, huella_anterior: str, hora: str) -> CamposHuellaAlta:
    return CamposHuellaAlta(
        id_emisor="89890001K",
        num_serie=num,
        fecha_expedicion="01-01-2024",
        tipo_factura="F1",
        cuota_total="12.35",
        importe_total="123.45",
        huella_anterior=huella_anterior,
        fecha_hora_huso_gen=hora,
    )


def test_vector_oficial_primer_registro_de_alta() -> None:
    campos = _alta("12345678/G33", "", "2024-01-01T19:20:30+01:00")

    assert campos.cadena() == CADENA_1
    assert compute_huella(campos.cadena()) == HUELLA_1


def test_vector_oficial_alta_encadenada() -> None:
    campos = _alta("12345679/G34", HUELLA_1, "2024-01-01T19:20:35+01:00")

    assert campos.cadena() == CADENA_2
    assert compute_huella(campos.cadena()) == HUELLA_2


def test_vector_oficial_anulacion_encadenada() -> None:
    campos = CamposHuellaAnulacion(
        id_emisor="89890001K",
        num_serie="12345679/G34",
        fecha_expedicion="01-01-2024",
        huella_anterior=HUELLA_2,
        fecha_hora_huso_gen="2024-01-01T19:20:40+01:00",
    )

    assert campos.cadena() == CADENA_3
    assert compute_huella(campos.cadena()) == HUELLA_3


def test_la_huella_son_64_hexadecimales_en_mayusculas() -> None:
    huella = compute_huella("cualquier cosa")

    assert len(huella) == 64
    assert huella == huella.upper()
    assert all(c in "0123456789ABCDEF" for c in huella)


def test_se_recortan_los_espacios_extremos_y_se_conservan_los_interiores() -> None:
    # F-2 p. 6: «<NumSerieFactura>    12345678 / G33  </NumSerieFactura>» → «12345678 / G33».
    campos = _alta("    12345678 / G33  ", "", "2024-01-01T19:20:30+01:00")

    assert "&NumSerieFactura=12345678 / G33&" in campos.cadena()


def test_campo_vacio_es_solo_el_nombre_y_el_igual_y_no_hay_ampersand_final() -> None:
    cadena = _alta("A/1", "", "2024-01-01T19:20:30+01:00").cadena()

    assert "&Huella=&" in cadena
    assert not cadena.endswith("&")


@pytest.mark.parametrize(
    ("valor", "esperado"), [("123.1", "123.10"), ("0", "0.00"), ("1560.90", "1560.90")]
)
def test_importes_siempre_con_dos_decimales_y_punto(valor: str, esperado: str) -> None:
    assert format_amount(Decimal(valor)) == esperado


def test_un_importe_con_mas_de_dos_decimales_no_se_formatea() -> None:
    with pytest.raises(ValueError, match="dos decimales"):
        format_amount(Decimal("1.005"))


def test_fecha_en_formato_dd_mm_aaaa() -> None:
    assert format_date(date(2024, 1, 1)) == "01-01-2024"


def test_hora_de_generacion_en_madrid_con_desfase() -> None:
    invierno = datetime(2024, 1, 1, 18, 20, 30, tzinfo=UTC)
    verano = datetime(2026, 7, 15, 10, 0, 0, 999_999, tzinfo=UTC)

    assert format_timestamp(invierno) == "2024-01-01T19:20:30+01:00"
    assert format_timestamp(verano) == "2026-07-15T12:00:00+02:00"


def test_una_cadena_de_registros_encadena_cada_huella_con_la_anterior() -> None:
    anterior = ""
    huellas: list[str] = []
    for i in range(1, 6):
        if i % 2:
            campos: CamposHuellaAlta | CamposHuellaAnulacion = _alta(
                f"FAC-2026-{i:04d}", anterior, f"2026-01-0{i}T10:00:00+01:00"
            )
        else:
            campos = CamposHuellaAnulacion(
                id_emisor="89890001K",
                num_serie=f"FAC-2026-{i - 1:04d}",
                fecha_expedicion="01-01-2024",
                huella_anterior=anterior,
                fecha_hora_huso_gen=f"2026-01-0{i}T10:00:00+01:00",
            )
        assert f"&Huella={anterior}&" in campos.cadena()
        anterior = compute_huella(campos.cadena())
        huellas.append(anterior)

    assert len(set(huellas)) == 5


def test_alterar_un_solo_campo_cambia_la_huella() -> None:
    original = _alta("12345678/G33", "", "2024-01-01T19:20:30+01:00")
    alterada = replace(original, importe_total="123.46")

    assert compute_huella(alterada.cadena()) != HUELLA_1

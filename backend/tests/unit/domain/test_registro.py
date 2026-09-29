"""Contenido de los registros de alta y de anulación según F-1 (research R-3, R-4, R-4b).

F-1: AEAT, DsRegistroVeriFactu.xlsx v1.0 (SHA-256 40ce191a…). Hojas 2 (alta), 3 (anulación) y
5 (SistemaInformatico); listas L2, L3, L8A, L9, L12 y L15.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.importes import DesgloseTipo
from app.domain.registro import (
    DatosAlta,
    Destinatario,
    Emisor,
    FacturaRectificada,
    RegistroAnterior,
    SistemaInformatico,
    build_contenido_alta,
    build_contenido_anulacion,
    build_descripcion_operacion,
)
from app.domain.tipos import TipoFactura

D = Decimal
EMISOR = Emisor(nif="B12345674", nombre="Joyería Blanco (demo)")
SISTEMA = SistemaInformatico(
    nombre_razon="Productor de pruebas (ficticio)",
    nif="00000000T",
    nombre_sistema="Joyería Blanco Gestión",
    id_sistema="JB",
    version="0.2.0",
    numero_instalacion="1",
)
MARIA = Destinatario(
    nombre="María López García",
    identificacion_pais="ES",
    identificacion_tipo="NIF",
    identificacion_numero="12345678Z",
)
HORA = "2026-09-29T10:15:00+02:00"
HUELLA = "A" * 64


def _datos(**cambios: object) -> DatosAlta:
    base: dict[str, object] = {
        "emisor": EMISOR,
        "num_serie": "FAC-2026-0001",
        "fecha_expedicion": date(2026, 9, 29),
        "tipo_factura": TipoFactura.COMPLETA,
        "fecha_operacion": None,
        "descripcion": "Anillo de oro blanco; Ajuste de pulsera",
        "destinatario": MARIA,
        "clave_regimen": "01",
        "desglose": (DesgloseTipo(tipo_iva=D("21.00"), base=D("1290.00"), cuota=D("270.90")),),
        "cuota_total": D("270.90"),
        "importe_total": D("1560.90"),
        "rectificada": None,
    }
    base.update(cambios)
    return DatosAlta(**base)  # type: ignore[arg-type]


def _alta(datos: DatosAlta, anterior: RegistroAnterior | None = None) -> dict[str, object]:
    return build_contenido_alta(
        datos, anterior=anterior, sistema=SISTEMA, fecha_hora_huso_gen=HORA, huella=HUELLA
    )


def test_alta_f1_completa() -> None:
    contenido = _alta(_datos())

    assert contenido == {
        "IDVersion": "1.0",
        "IDFactura": {
            "IDEmisorFactura": "B12345674",
            "NumSerieFactura": "FAC-2026-0001",
            "FechaExpedicionFactura": "29-09-2026",
        },
        "NombreRazonEmisor": "Joyería Blanco (demo)",
        "TipoFactura": "F1",
        "DescripcionOperacion": "Anillo de oro blanco; Ajuste de pulsera",
        "Destinatarios": {
            "IDDestinatario": [{"NombreRazon": "María López García", "NIF": "12345678Z"}]
        },
        "Desglose": {
            "DetalleDesglose": [
                {
                    "ClaveRegimen": "01",
                    "CalificacionOperacion": "S1",
                    "TipoImpositivo": "21.00",
                    "BaseImponibleOimporteNoSujeto": "1290.00",
                    "CuotaRepercutida": "270.90",
                }
            ]
        },
        "CuotaTotal": "270.90",
        "ImporteTotal": "1560.90",
        "Encadenamiento": {"PrimerRegistro": "S"},
        "SistemaInformatico": {
            "NombreRazon": "Productor de pruebas (ficticio)",
            "NIF": "00000000T",
            "NombreSistemaInformatico": "Joyería Blanco Gestión",
            "IdSistemaInformatico": "JB",
            "Version": "0.2.0",
            "NumeroInstalacion": "1",
            "TipoUsoPosibleSoloVerifactu": "N",
            "TipoUsoPosibleMultiOT": "N",
            "IndicadorMultiplesOT": "N",
        },
        "FechaHoraHusoGenRegistro": HORA,
        "TipoHuella": "01",
        "Huella": HUELLA,
    }


def test_no_se_informan_impuesto_ni_opcionales_excluidos() -> None:
    contenido = _alta(_datos())
    detalle = contenido["Desglose"]["DetalleDesglose"][0]  # type: ignore[index]

    excluidos = {"Impuesto", "OperacionExenta", "BaseImponibleACoste", "TipoRecargoEquivalencia"}
    assert excluidos.isdisjoint(detalle)
    cabecera = {"Subsanacion", "RechazoPrevio", "RefExterna", "Cupon", "Macrodato", "Tercero"}
    assert cabecera.isdisjoint(contenido)
    assert "FechaOperacion" not in contenido


def test_alta_encadenada_con_el_registro_anterior() -> None:
    anterior = RegistroAnterior(
        id_emisor="B12345674",
        num_serie="FAC-2026-0000X",
        fecha_expedicion="28-09-2026",
        huella="B" * 64,
    )

    contenido = _alta(_datos(), anterior)

    assert contenido["Encadenamiento"] == {
        "RegistroAnterior": {
            "IDEmisorFactura": "B12345674",
            "NumSerieFactura": "FAC-2026-0000X",
            "FechaExpedicionFactura": "28-09-2026",
            "Huella": "B" * 64,
        }
    }


@pytest.mark.parametrize(
    ("tipo", "pais", "numero"),
    [("02", "FR", "FR12345678901"), ("03", "US", "X1234567"), ("06", "MA", "AB-123")],
)
def test_destinatario_con_id_otro(tipo: str, pais: str, numero: str) -> None:
    extranjero = Destinatario(
        nombre="Client étranger",
        identificacion_pais=pais,
        identificacion_tipo=tipo,
        identificacion_numero=numero,
    )

    contenido = _alta(_datos(destinatario=extranjero))

    assert contenido["Destinatarios"] == {
        "IDDestinatario": [
            {
                "NombreRazon": "Client étranger",
                "IDOtro": {"CodigoPais": pais, "IDType": tipo, "ID": numero},
            }
        ]
    }


@pytest.mark.parametrize(
    "tipo", [TipoFactura.RECTIFICATIVA_RESTO, TipoFactura.RECTIFICATIVA_DERECHO_ART80]
)
def test_rectificativa_por_sustitucion(tipo: TipoFactura) -> None:
    rectificada = FacturaRectificada(
        num_serie="FAC-2026-0007",
        fecha_expedicion=date(2026, 9, 1),
        base=D("1000.00"),
        cuota=D("210.00"),
    )
    datos = _datos(
        num_serie="REC-2026-0001",
        tipo_factura=tipo,
        fecha_operacion=date(2026, 9, 1),
        rectificada=rectificada,
        desglose=(DesgloseTipo(tipo_iva=D("21.00"), base=D("800.00"), cuota=D("168.00")),),
        cuota_total=D("168.00"),
        importe_total=D("968.00"),
    )

    contenido = _alta(datos)

    assert contenido["TipoFactura"] == tipo.value
    assert contenido["TipoRectificativa"] == "S"
    assert contenido["FacturasRectificadas"] == {
        "IDFacturaRectificada": [
            {
                "IDEmisorFactura": "B12345674",
                "NumSerieFactura": "FAC-2026-0007",
                "FechaExpedicionFactura": "01-09-2026",
            }
        ]
    }
    # F-9, opción 1: base y cuota rectificadas = las de la original; desglose = importes correctos.
    assert contenido["ImporteRectificacion"] == {
        "BaseRectificada": "1000.00",
        "CuotaRectificada": "210.00",
    }
    assert contenido["FechaOperacion"] == "01-09-2026"
    assert contenido["ImporteTotal"] == "968.00"
    claves = list(contenido)
    # Orden de F-1, hoja 2: TipoFactura, TipoRectificativa, FacturasRectificadas,
    # ImporteRectificacion, FechaOperacion, DescripcionOperacion.
    assert claves.index("TipoRectificativa") < claves.index("FacturasRectificadas")
    assert claves.index("ImporteRectificacion") < claves.index("FechaOperacion")
    assert claves.index("FechaOperacion") < claves.index("DescripcionOperacion")


def test_devolucion_total_con_un_detalle_a_cero() -> None:
    datos = _datos(
        num_serie="REC-2026-0002",
        tipo_factura=TipoFactura.RECTIFICATIVA_DERECHO_ART80,
        fecha_operacion=date(2026, 9, 1),
        rectificada=FacturaRectificada(
            num_serie="FAC-2026-0009",
            fecha_expedicion=date(2026, 9, 1),
            base=D("100.00"),
            cuota=D("21.00"),
        ),
        desglose=(DesgloseTipo(tipo_iva=D("21.00"), base=D("0.00"), cuota=D("0.00")),),
        cuota_total=D("0.00"),
        importe_total=D("0.00"),
    )

    contenido = _alta(datos)

    detalles = contenido["Desglose"]["DetalleDesglose"]  # type: ignore[index]
    assert len(detalles) == 1
    assert detalles[0]["BaseImponibleOimporteNoSujeto"] == "0.00"
    assert contenido["ImporteTotal"] == "0.00"


def test_anulacion() -> None:
    contenido = build_contenido_anulacion(
        emisor_nif="B12345674",
        num_serie="FAC-2026-0007",
        fecha_expedicion=date(2026, 9, 1),
        anterior=RegistroAnterior(
            id_emisor="B12345674",
            num_serie="FAC-2026-0010",
            fecha_expedicion="29-09-2026",
            huella="C" * 64,
        ),
        sistema=SISTEMA,
        fecha_hora_huso_gen=HORA,
        huella=HUELLA,
    )

    assert list(contenido) == [
        "IDVersion",
        "IDFactura",
        "Encadenamiento",
        "SistemaInformatico",
        "FechaHoraHusoGenRegistro",
        "TipoHuella",
        "Huella",
    ]
    assert contenido["IDFactura"] == {
        "IDEmisorFacturaAnulada": "B12345674",
        "NumSerieFacturaAnulada": "FAC-2026-0007",
        "FechaExpedicionFacturaAnulada": "01-09-2026",
    }


# ------------------------------------------------------------- descripción (FR-045)


def test_descripcion_une_las_lineas_con_punto_y_coma() -> None:
    assert build_descripcion_operacion(["Anillo", "  Pulsera "]) == "Anillo; Pulsera"


def test_descripcion_se_recorta_a_500_con_puntos_suspensivos() -> None:
    descripcion = build_descripcion_operacion(["x" * 300, "y" * 300])

    assert len(descripcion) == 500
    assert descripcion.endswith("…")


def test_descripcion_de_una_devolucion_total() -> None:
    assert (
        build_descripcion_operacion([], num_rectificada="FAC-2026-0009")
        == "Devolución total de la factura FAC-2026-0009"
    )


def test_descripcion_sin_lineas_ni_rectificada_es_un_error() -> None:
    with pytest.raises(ValueError, match="devolución total"):
        build_descripcion_operacion([])

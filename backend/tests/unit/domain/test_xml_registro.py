"""⚖️ Test obligatorio (constitución VII, 2.4.0): el XML de los registros cumple los XSD oficiales.

- Altas (ordinaria, rectificativa y de oro de inversión) y anulación contra F-15
  (`SuministroInformacion.xsd`). En ellas la firma es opcional en el esquema: se validan sin firmar.
- Eventos de cada tipo contra F-17 (`EventosSIF.xsd`). En `EventoType` la firma es obligatoria: se
  validan firmados con un certificado de prueba.
- El orden de los elementos es el del esquema aunque el `contenido` llegue desordenado (JSONB).
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from lxml import etree

from app.domain import eventos
from app.domain.huella import compute_huella
from app.domain.importes import DesgloseTipo
from app.domain.registro import (
    Contenido,
    DatosAlta,
    Destinatario,
    Emisor,
    FacturaRectificada,
    RegistroAnterior,
    SistemaInformatico,
    build_contenido_alta,
    build_contenido_anulacion,
    detalle_desde,
)
from app.domain.tipos import TipoAnomalia, TipoEventoSif, TipoFactura
from app.domain.xml_registro import (
    NS_EVENTOS,
    NS_SUMINISTRO,
    build_registro_alta,
    build_registro_anulacion,
    build_registro_evento,
    canonical,
    without_signature,
)
from app.services import firma
from app.services.certificado import CertificadoFirma
from tests.certificados import certificado_firma

D = Decimal
SISTEMA = SistemaInformatico(
    nombre_razon="Joyería Blanco (productora)",
    nif="B12345674",
    nombre_sistema="Joyería Blanco Gestión",
    id_sistema="JB",
    version="0.4.0",
    numero_instalacion="1",
)
EMISOR = Emisor(nif="B12345674", nombre="Joyería Blanco, S.L.")
OBLIGADO = eventos.Obligado(nombre="Joyería Blanco, S.L.", nif="B12345674")
HORA = "2026-10-03T10:15:00+02:00"
HUELLA = "A" * 64
ANTERIOR = RegistroAnterior(
    id_emisor="B12345674", num_serie="FAC-2026-0001", fecha_expedicion="02-10-2026", huella="B" * 64
)


def _datos(**cambios: object) -> DatosAlta:
    base: dict[str, object] = {
        "emisor": EMISOR,
        "num_serie": "FAC-2026-0002",
        "fecha_expedicion": date(2026, 10, 3),
        "tipo_factura": TipoFactura.COMPLETA,
        "fecha_operacion": None,
        "descripcion": "Anillo de oro blanco & <ajuste>",  # caracteres que hay que escapar
        "destinatario": Destinatario(
            nombre="María López García",
            identificacion_pais="ES",
            identificacion_tipo="NIF",
            identificacion_numero="12345678Z",
        ),
        "desglose": (
            detalle_desde(DesgloseTipo(tipo_iva=D("21.00"), base=D("1290.00"), cuota=D("270.90"))),
        ),
        "cuota_total": D("270.90"),
        "importe_total": D("1560.90"),
        "rectificada": None,
    }
    base.update(cambios)
    return DatosAlta(**base)  # type: ignore[arg-type]


def _alta(datos: DatosAlta, anterior: RegistroAnterior | None = ANTERIOR) -> Contenido:
    return build_contenido_alta(
        datos, anterior=anterior, sistema=SISTEMA, fecha_hora_huso_gen=HORA, huella=HUELLA
    )


ALTAS = {
    "ordinaria": _alta(_datos(), anterior=None),
    "encadenada": _alta(_datos()),
    "extranjero": _alta(
        _datos(
            destinatario=Destinatario(
                nombre="John Smith",
                identificacion_pais="GB",
                identificacion_tipo="03",
                identificacion_numero="X1234567",
            )
        )
    ),
    "rectificativa": _alta(
        _datos(
            num_serie="REC-2026-0001",
            tipo_factura=TipoFactura.RECTIFICATIVA_RESTO,
            fecha_operacion=date(2026, 10, 1),
            rectificada=FacturaRectificada(
                num_serie="FAC-2026-0001",
                fecha_expedicion=date(2026, 10, 2),
                base=D("1000.00"),
                cuota=D("210.00"),
            ),
        )
    ),
    "oro-inversion": _alta(
        _datos(
            desglose=(
                detalle_desde(DesgloseTipo(tipo_iva=None, base=D("7450.00"), cuota=D("0.00"))),
            ),
            cuota_total=D("0.00"),
            importe_total=D("7450.00"),
        )
    ),
}


@pytest.mark.parametrize("contenido", ALTAS.values(), ids=ALTAS.keys())
def test_el_alta_cumple_suministro_informacion(contenido: Contenido) -> None:
    firma.validar(build_registro_alta(contenido), firma.Esquema.SUMINISTRO)


def test_la_anulacion_cumple_suministro_informacion() -> None:
    contenido = build_contenido_anulacion(
        emisor_nif="B12345674",
        num_serie="FAC-2026-0001",
        fecha_expedicion=date(2026, 10, 2),
        anterior=ANTERIOR,
        sistema=SISTEMA,
        fecha_hora_huso_gen=HORA,
        huella=HUELLA,
    )

    firma.validar(build_registro_anulacion(contenido), firma.Esquema.SUMINISTRO)


def test_el_orden_es_el_del_esquema_aunque_el_contenido_llegue_desordenado() -> None:
    contenido = ALTAS["rectificativa"]
    al_reves = dict(reversed(list(contenido.items())))

    elemento = build_registro_alta(al_reves)

    assert canonical(elemento) == canonical(build_registro_alta(contenido))
    nombres = [etree.QName(hijo).localname for hijo in elemento]
    assert nombres[:3] == ["IDVersion", "IDFactura", "NombreRazonEmisor"]
    assert nombres[-3:] == ["FechaHoraHusoGenRegistro", "TipoHuella", "Huella"]
    assert elemento.nsmap.get("sum1") == NS_SUMINISTRO


def test_el_primer_registro_lleva_primer_registro_s() -> None:
    elemento = build_registro_alta(ALTAS["ordinaria"])

    primer = elemento.find(f"{{{NS_SUMINISTRO}}}Encadenamiento/{{{NS_SUMINISTRO}}}PrimerRegistro")
    assert primer is not None
    assert primer.text == "S"


def test_una_clave_fuera_del_esquema_es_un_error() -> None:
    with pytest.raises(ValueError, match="no están en el esquema"):
        build_registro_alta(ALTAS["ordinaria"] | {"Inventado": "x"})


# ------------------------------------------------------------------------------- eventos

REGISTRO = eventos.IdFactura("B12345674", "FAC-2026-0002", "03-10-2026")
CON_HUELLA = eventos.RegistroConHuella(REGISTRO, HUELLA)
REFERIDO = eventos.EventoReferido("01", HORA, "C" * 64)
RECUENTOS = eventos.Recuentos(huellas=7, firmas=7, cadena=7, fechas=7)
DATOS_PROPIOS: dict[TipoEventoSif, Contenido | None] = {
    TipoEventoSif.INICIO: None,
    TipoEventoSif.FIN: None,
    TipoEventoSif.LANZAMIENTO_ANOMALIAS_FACTURACION: eventos.lanzamiento(
        TipoEventoSif.LANZAMIENTO_ANOMALIAS_FACTURACION, RECUENTOS
    ),
    TipoEventoSif.ANOMALIA_FACTURACION: eventos.anomalia_facturacion(
        TipoAnomalia.HUELLA, descripcion="La huella no coincide", factura=REGISTRO
    ),
    TipoEventoSif.LANZAMIENTO_ANOMALIAS_EVENTOS: eventos.lanzamiento(
        TipoEventoSif.LANZAMIENTO_ANOMALIAS_EVENTOS, RECUENTOS
    ),
    TipoEventoSif.ANOMALIA_EVENTOS: eventos.anomalia_eventos(
        TipoAnomalia.FIRMA, descripcion="x" * 150, evento=REFERIDO
    ),
    TipoEventoSif.EXPORTACION_FACTURACION: eventos.exportacion_facturacion(
        inicio="2026-10-01T00:00:00+02:00",
        fin="2026-10-31T23:59:59+01:00",
        inicial=CON_HUELLA,
        final=CON_HUELLA,
        altas=3,
        suma_cuota=D("-12.50"),
        suma_importe=D("1560.90"),
        anulaciones=1,
    ),
    TipoEventoSif.EXPORTACION_EVENTOS: eventos.exportacion_eventos(
        inicio="2026-10-01T00:00:00+02:00",
        fin="2026-10-31T23:59:59+01:00",
        inicial=REFERIDO,
        final=REFERIDO,
        numero=12,
    ),
    TipoEventoSif.RESUMEN: eventos.resumen(
        eventos_por_tipo={"01": 1, "03": 2},
        inicial=CON_HUELLA,
        final=CON_HUELLA,
        altas=5,
        suma_cuota=D("270.90"),
        suma_importe=D("1560.90"),
        anulaciones=0,
    ),
}


def _evento(
    tipo: TipoEventoSif,
    datos: Contenido | None,
    anterior: eventos.EventoAnterior | None = None,
) -> Contenido:
    huella = compute_huella(
        eventos.campos_huella(
            sistema=SISTEMA,
            obligado=OBLIGADO,
            tipo=tipo,
            anterior=anterior,
            fecha_hora_huso_gen=HORA,
        ).cadena()
    )
    return eventos.build_contenido_evento(
        sistema=SISTEMA,
        obligado=OBLIGADO,
        tipo=tipo,
        fecha_hora_huso_gen=HORA,
        datos_propios=datos,
        otros_datos="Parada ordenada" if tipo is TipoEventoSif.FIN else None,
        anterior=anterior,
        huella=huella,
    )


@pytest.fixture(scope="module")
def firmante() -> CertificadoFirma:
    return certificado_firma()


@pytest.mark.parametrize("tipo", DATOS_PROPIOS, ids=[t.value for t in DATOS_PROPIOS])
def test_cada_evento_firmado_cumple_eventos_sif(
    tipo: TipoEventoSif, firmante: CertificadoFirma
) -> None:
    anterior = eventos.EventoAnterior("01", HORA, "D" * 64)
    contenido = _evento(tipo, DATOS_PROPIOS[tipo], anterior)

    xml = firma.firmar(
        build_registro_evento(contenido, con_hueco_firma=True), firmante, datetime.now(UTC)
    )

    raiz = etree.fromstring(xml)
    firma.validar(raiz, firma.Esquema.EVENTOS)
    evento = raiz.find(f"{{{NS_EVENTOS}}}Evento")
    assert evento is not None
    assert etree.QName(evento[-1]).localname == "Signature"  # al final de `Evento` (EventoType)


def test_el_primer_evento_lleva_primer_evento_s() -> None:
    elemento = build_registro_evento(_evento(TipoEventoSif.INICIO, None))

    primer = elemento.find(
        f"{{{NS_EVENTOS}}}Evento/{{{NS_EVENTOS}}}Encadenamiento/{{{NS_EVENTOS}}}PrimerEvento"
    )
    assert primer is not None
    assert primer.text == "S"


def test_un_resumen_sin_eventos_informa_el_propio_resumen_con_cero() -> None:
    datos = eventos.resumen(
        eventos_por_tipo={},
        inicial=None,
        final=None,
        altas=0,
        suma_cuota=D(0),
        suma_importe=D(0),
        anulaciones=0,
    )

    assert datos["ResumenEventos"]["TipoEvento"] == [  # type: ignore[index]
        {"TipoEvento": "10", "NumeroDeEventos": "0"}
    ]


def test_sin_firma_se_recupera_el_registro_generado() -> None:
    elemento = build_registro_alta(ALTAS["encadenada"])
    xml = firma.firmar(elemento, certificado_firma(), datetime.now(UTC))

    assert canonical(without_signature(xml)) == canonical(build_registro_alta(ALTAS["encadenada"]))

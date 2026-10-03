"""XML oficial de los registros de facturación y de evento (004, research R-1).

- Alta y anulación: elementos globales `RegistroAlta` y `RegistroAnulacion` de
  `SuministroInformacion.xsd` (F-15).
- Evento: elemento global `RegistroEvento` de `EventosSIF.xsd` (F-17).

El `contenido` de cada registro guarda los valores como texto con los nombres oficiales, pero JSONB
no conserva el orden de las claves. El orden lo imponen estas tablas, sacadas literalmente de las
secuencias de los XSD (los `choice` aparecen en su orden y solo se informa una de las ramas). Una
clave que no figure en la tabla de su tipo es un error de programación.

La firma (`ds:Signature`) no está en las tablas: la añade `services/firma.py`. En el evento va
dentro de `Evento`, en el sitio que marca `con_hueco_firma=True`.
"""

from collections.abc import Mapping, Sequence
from typing import Final

from lxml import etree

NS_SUMINISTRO: Final = (
    "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/"
    "tike/cont/ws/SuministroInformacion.xsd"
)
NS_EVENTOS: Final = (
    "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/"
    "tike/cont/ws/EventosSIF.xsd"
)
NS_DS: Final = "http://www.w3.org/2000/09/xmldsig#"

# Tipo complejo → hijos en orden: (elemento, tipo complejo del hijo o None si es un valor simple).
type Orden = Mapping[str, tuple[tuple[str, str | None], ...]]

_SISTEMA_INFORMATICO: Final = (
    ("NombreRazon", None),
    ("NIF", None),
    ("IDOtro", "IDOtroType"),
    ("NombreSistemaInformatico", None),
    ("IdSistemaInformatico", None),
    ("Version", None),
    ("NumeroInstalacion", None),
    ("TipoUsoPosibleSoloVerifactu", None),
    ("TipoUsoPosibleMultiOT", None),
    ("IndicadorMultiplesOT", None),
)
_ID_OTRO: Final = (("CodigoPais", None), ("IDType", None), ("ID", None))
_PERSONA: Final = (("NombreRazon", None), ("NIF", None), ("IDOtro", "IDOtroType"))
_ID_FACTURA: Final = (
    ("IDEmisorFactura", None),
    ("NumSerieFactura", None),
    ("FechaExpedicionFactura", None),
)
_ID_FACTURA_HUELLA: Final = (*_ID_FACTURA, ("Huella", None))

# F-15, SuministroInformacion.xsd
ORDEN_SUMINISTRO: Final[Orden] = {
    "RegistroFacturacionAltaType": (
        ("IDVersion", None),
        ("IDFactura", "IDFacturaExpedidaType"),
        ("RefExterna", None),
        ("NombreRazonEmisor", None),
        ("Subsanacion", None),
        ("RechazoPrevio", None),
        ("TipoFactura", None),
        ("TipoRectificativa", None),
        ("FacturasRectificadas", "FacturasRectificadas"),
        ("FacturasSustituidas", "FacturasSustituidas"),
        ("ImporteRectificacion", "DesgloseRectificacionType"),
        ("FechaOperacion", None),
        ("DescripcionOperacion", None),
        ("FacturaSimplificadaArt7273", None),
        ("FacturaSinIdentifDestinatarioArt61d", None),
        ("Macrodato", None),
        ("EmitidaPorTerceroODestinatario", None),
        ("Tercero", "PersonaFisicaJuridicaType"),
        ("Destinatarios", "Destinatarios"),
        ("Cupon", None),
        ("Desglose", "DesgloseType"),
        ("CuotaTotal", None),
        ("ImporteTotal", None),
        ("Encadenamiento", "EncadenamientoRegistro"),
        ("SistemaInformatico", "SistemaInformaticoType"),
        ("FechaHoraHusoGenRegistro", None),
        ("NumRegistroAcuerdoFacturacion", None),
        ("IdAcuerdoSistemaInformatico", None),
        ("TipoHuella", None),
        ("Huella", None),
    ),
    "RegistroFacturacionAnulacionType": (
        ("IDVersion", None),
        ("IDFactura", "IDFacturaExpedidaBajaType"),
        ("RefExterna", None),
        ("SinRegistroPrevio", None),
        ("RechazoPrevio", None),
        ("GeneradoPor", None),
        ("Generador", "PersonaFisicaJuridicaType"),
        ("Encadenamiento", "EncadenamientoRegistro"),
        ("SistemaInformatico", "SistemaInformaticoType"),
        ("FechaHoraHusoGenRegistro", None),
        ("TipoHuella", None),
        ("Huella", None),
    ),
    "IDFacturaExpedidaType": _ID_FACTURA,
    "IDFacturaExpedidaBajaType": (
        ("IDEmisorFacturaAnulada", None),
        ("NumSerieFacturaAnulada", None),
        ("FechaExpedicionFacturaAnulada", None),
    ),
    "FacturasRectificadas": (("IDFacturaRectificada", "IDFacturaARType"),),
    "FacturasSustituidas": (("IDFacturaSustituida", "IDFacturaARType"),),
    "IDFacturaARType": _ID_FACTURA,
    "DesgloseRectificacionType": (
        ("BaseRectificada", None),
        ("CuotaRectificada", None),
        ("CuotaRecargoRectificado", None),
    ),
    "PersonaFisicaJuridicaType": _PERSONA,
    "IDOtroType": _ID_OTRO,
    "Destinatarios": (("IDDestinatario", "PersonaFisicaJuridicaType"),),
    "DesgloseType": (("DetalleDesglose", "DetalleType"),),
    "DetalleType": (
        ("Impuesto", None),
        ("ClaveRegimen", None),
        ("CalificacionOperacion", None),
        ("OperacionExenta", None),
        ("TipoImpositivo", None),
        ("BaseImponibleOimporteNoSujeto", None),
        ("BaseImponibleACoste", None),
        ("CuotaRepercutida", None),
        ("TipoRecargoEquivalencia", None),
        ("CuotaRecargoEquivalencia", None),
    ),
    "EncadenamientoRegistro": (
        ("PrimerRegistro", None),
        ("RegistroAnterior", "EncadenamientoFacturaAnteriorType"),
    ),
    "EncadenamientoFacturaAnteriorType": _ID_FACTURA_HUELLA,
    "SistemaInformaticoType": _SISTEMA_INFORMATICO,
}

# F-17, EventosSIF.xsd
ORDEN_EVENTOS: Final[Orden] = {
    "RegistroEvento": (("IDVersion", None), ("Evento", "EventoType")),
    "EventoType": (
        ("SistemaInformatico", "SistemaInformaticoType"),
        ("ObligadoEmision", "PersonaFisicaJuridicaESType"),
        ("EmitidaPorTerceroODestinatario", None),
        ("TerceroODestinatario", "PersonaFisicaJuridicaType"),
        ("FechaHoraHusoGenEvento", None),
        ("TipoEvento", None),
        ("DatosPropiosEvento", "DatosPropiosEventoType"),
        ("OtrosDatosEvento", None),
        ("Encadenamiento", "EncadenamientoType"),
        ("TipoHuella", None),
        ("HuellaEvento", None),
    ),
    "SistemaInformaticoType": _SISTEMA_INFORMATICO,
    "IDOtroType": _ID_OTRO,
    "PersonaFisicaJuridicaESType": (("NombreRazon", None), ("NIF", None)),
    "PersonaFisicaJuridicaType": _PERSONA,
    "DatosPropiosEventoType": (
        (
            "LanzamientoProcesoDeteccionAnomaliasRegFacturacion",
            "LanzamientoProcesoDeteccionAnomaliasRegFacturacionType",
        ),
        ("DeteccionAnomaliasRegFacturacion", "DeteccionAnomaliasRegFacturacionType"),
        (
            "LanzamientoProcesoDeteccionAnomaliasRegEvento",
            "LanzamientoProcesoDeteccionAnomaliasRegEventoType",
        ),
        ("DeteccionAnomaliasRegEvento", "DeteccionAnomaliasRegEventoType"),
        ("ExportacionRegFacturacionPeriodo", "ExportacionRegFacturacionPeriodoType"),
        ("ExportacionRegEventoPeriodo", "ExportacionRegEventoPeriodoType"),
        ("ResumenEventos", "ResumenEventosType"),
    ),
    "LanzamientoProcesoDeteccionAnomaliasRegFacturacionType": (
        ("RealizadoProcesoSobreIntegridadHuellasRegFacturacion", None),
        ("NumeroDeRegistrosFacturacionProcesadosSobreIntegridadHuellas", None),
        ("RealizadoProcesoSobreIntegridadFirmasRegFacturacion", None),
        ("NumeroDeRegistrosFacturacionProcesadosSobreIntegridadFirmas", None),
        ("RealizadoProcesoSobreTrazabilidadCadenaRegFacturacion", None),
        ("NumeroDeRegistrosFacturacionProcesadosSobreTrazabilidadCadena", None),
        ("RealizadoProcesoSobreTrazabilidadFechasRegFacturacion", None),
        ("NumeroDeRegistrosFacturacionProcesadosSobreTrazabilidadFechas", None),
    ),
    "DeteccionAnomaliasRegFacturacionType": (
        ("TipoAnomalia", None),
        ("OtrosDatosAnomalia", None),
        ("RegistroFacturacionAnomalo", "IDFacturaExpedidaType"),
    ),
    "IDFacturaExpedidaType": _ID_FACTURA,
    "LanzamientoProcesoDeteccionAnomaliasRegEventoType": (
        ("RealizadoProcesoSobreIntegridadHuellasRegEvento", None),
        ("NumeroDeRegistrosEventoProcesadosSobreIntegridadHuellas", None),
        ("RealizadoProcesoSobreIntegridadFirmasRegEvento", None),
        ("NumeroDeRegistrosEventoProcesadosSobreIntegridadFirmas", None),
        ("RealizadoProcesoSobreTrazabilidadCadenaRegEvento", None),
        ("NumeroDeRegistrosEventoProcesadosSobreTrazabilidadCadena", None),
        ("RealizadoProcesoSobreTrazabilidadFechasRegEvento", None),
        ("NumeroDeRegistrosEventoProcesadosSobreTrazabilidadFechas", None),
    ),
    "DeteccionAnomaliasRegEventoType": (
        ("TipoAnomalia", None),
        ("OtrosDatosAnomalia", None),
        ("RegEventoAnomalo", "RegEventoType"),
    ),
    "RegEventoType": (
        ("TipoEvento", None),
        ("FechaHoraHusoEvento", None),
        ("HuellaEvento", None),
    ),
    "ExportacionRegFacturacionPeriodoType": (
        ("FechaHoraHusoInicioPeriodoExport", None),
        ("FechaHoraHusoFinPeriodoExport", None),
        ("RegistroFacturacionInicialPeriodo", "IDFacturaExpedidaHuellaType"),
        ("RegistroFacturacionFinalPeriodo", "IDFacturaExpedidaHuellaType"),
        ("NumeroDeRegistrosFacturacionAltaExportados", None),
        ("SumaCuotaTotalAlta", None),
        ("SumaImporteTotalAlta", None),
        ("NumeroDeRegistrosFacturacionAnulacionExportados", None),
        ("RegistrosFacturacionExportadosDejanDeConservarse", None),
    ),
    "IDFacturaExpedidaHuellaType": _ID_FACTURA_HUELLA,
    "ExportacionRegEventoPeriodoType": (
        ("FechaHoraHusoInicioPeriodoExport", None),
        ("FechaHoraHusoFinPeriodoExport", None),
        ("RegistroEventoInicialPeriodo", "RegEventoType"),
        ("RegistroEventoFinalPeriodo", "RegEventoType"),
        ("NumeroDeRegEventoExportados", None),
        ("RegEventoExportadosDejanDeConservarse", None),
    ),
    "ResumenEventosType": (
        ("TipoEvento", "TipoEventoAgrType"),
        ("RegistroFacturacionInicialPeriodo", "IDFacturaExpedidaHuellaType"),
        ("RegistroFacturacionFinalPeriodo", "IDFacturaExpedidaHuellaType"),
        ("NumeroDeRegistrosFacturacionAltaGenerados", None),
        ("SumaCuotaTotalAlta", None),
        ("SumaImporteTotalAlta", None),
        ("NumeroDeRegistrosFacturacionAnulacionGenerados", None),
    ),
    "TipoEventoAgrType": (("TipoEvento", None), ("NumeroDeEventos", None)),
    "EncadenamientoType": (("PrimerEvento", None), ("EventoAnterior", "RegEventoAntType")),
    "RegEventoAntType": (
        ("TipoEvento", None),
        ("FechaHoraHusoGenEvento", None),
        ("HuellaEvento", None),
    ),
}


def _llenar(
    padre: etree._Element, ns: str, orden: Orden, tipo: str, datos: Mapping[str, object]
) -> None:
    hijos = orden[tipo]
    if desconocidos := set(datos) - {nombre for nombre, _ in hijos}:
        msg = f"{tipo}: elementos que no están en el esquema: {sorted(desconocidos)}"
        raise ValueError(msg)
    for nombre, subtipo in hijos:
        if nombre not in datos:
            continue
        valor = datos[nombre]
        repetidos: Sequence[object] = valor if isinstance(valor, list) else [valor]
        for elemento in repetidos:
            hijo = etree.SubElement(padre, f"{{{ns}}}{nombre}")
            if subtipo is None:
                if not isinstance(elemento, str):
                    msg = f"{tipo}/{nombre}: se esperaba texto"
                    raise TypeError(msg)
                hijo.text = elemento
            elif isinstance(elemento, Mapping):
                _llenar(hijo, ns, orden, subtipo, elemento)
            else:
                msg = f"{tipo}/{nombre}: se esperaba un bloque"
                raise TypeError(msg)


def _raiz(nombre: str, ns: str, prefijo: str) -> etree._Element:
    return etree.Element(f"{{{ns}}}{nombre}", nsmap={prefijo: ns})


def build_registro_alta(contenido: Mapping[str, object]) -> etree._Element:
    raiz = _raiz("RegistroAlta", NS_SUMINISTRO, "sum1")
    _llenar(raiz, NS_SUMINISTRO, ORDEN_SUMINISTRO, "RegistroFacturacionAltaType", contenido)
    return raiz


def build_registro_anulacion(contenido: Mapping[str, object]) -> etree._Element:
    raiz = _raiz("RegistroAnulacion", NS_SUMINISTRO, "sum1")
    _llenar(raiz, NS_SUMINISTRO, ORDEN_SUMINISTRO, "RegistroFacturacionAnulacionType", contenido)
    return raiz


def build_registro_evento(
    contenido: Mapping[str, object], *, con_hueco_firma: bool = False
) -> etree._Element:
    """`RegistroEvento` con su `Evento`. La firma es obligatoria en `EventoType` y va al final de
    `Evento`: `con_hueco_firma` deja ahí el `ds:Signature Id="placeholder"` que sustituye signxml.
    """
    raiz = _raiz("RegistroEvento", NS_EVENTOS, "sfe")
    _llenar(raiz, NS_EVENTOS, ORDEN_EVENTOS, "RegistroEvento", contenido)
    if con_hueco_firma:
        evento = raiz.find(f"{{{NS_EVENTOS}}}Evento")
        if evento is None:
            msg = "RegistroEvento sin Evento"
            raise ValueError(msg)
        etree.SubElement(evento, f"{{{NS_DS}}}Signature", nsmap={"ds": NS_DS}, Id="placeholder")
    return raiz


def without_signature(xml: bytes) -> etree._Element:
    """El registro firmado sin su `ds:Signature`: lo que se generó a partir del `contenido`."""
    raiz = etree.fromstring(xml, parser=etree.XMLParser(resolve_entities=False, no_network=True))
    for firma in list(raiz.iter(f"{{{NS_DS}}}Signature")):
        padre = firma.getparent()
        if padre is not None:
            padre.remove(firma)
    return raiz


def canonical(elemento: etree._Element) -> bytes:
    """C14N exclusiva: compara dos registros sin depender de dónde se declaran los prefijos."""
    return etree.tostring(elemento, method="c14n", exclusive=True)

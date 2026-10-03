"""Contenido de los registros de evento (004; F-17 `EventosSIF.xsd`; Orden, art. 9).

Como en `domain/registro.py`, el contenido guarda TODOS los valores como texto con los nombres
oficiales: `{"IDVersion": "1.0", "Evento": {...}}`. `domain/xml_registro.py` lo convierte en XML en
el orden del esquema. La huella se calcula con `domain/huella.CamposHuellaEvento` (F-2 §3.c).

Los datos propios de cada tipo (data-model, «DatosPropiosEvento»):
- 03 y 05: lanzamiento de la detección de anomalías, con los recuentos de las cuatro
  comprobaciones (huellas, firmas, cadena y fechas).
- 04 y 06: una anomalía detectada, con su `TipoAnomalia` y el registro o evento afectado.
- 08 y 09: exportación de un periodo. «Dejan de conservarse» siempre es «N» (FR-024, FR-025).
- 10: resumen de eventos desde el anterior (art. 9.2).
- 01 y 02 no llevan datos propios.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from app.domain.huella import CamposHuellaEvento, format_amount
from app.domain.registro import ID_VERSION, TIPO_HUELLA_SHA256, Contenido, SistemaInformatico
from app.domain.tipos import TipoAnomalia, TipoEventoSif

SI: Final = "S"
NO: Final = "N"
MAX_OTROS_DATOS: Final = 100  # TextMax100Type
MAX_TIPOS_RESUMEN: Final = 20  # ResumenEventos/TipoEvento, maxOccurs="20"


@dataclass(frozen=True, slots=True)
class Obligado:
    """`ObligadoEmision`: el emisor de las facturas (PersonaFisicaJuridicaESType)."""

    nombre: str
    nif: str


@dataclass(frozen=True, slots=True)
class EventoAnterior:
    """`Encadenamiento/EventoAnterior` (RegEventoAntType)."""

    tipo_evento: str
    fecha_hora_huso_gen: str
    huella: str


@dataclass(frozen=True, slots=True)
class IdFactura:
    """Identificación de la factura de un registro de facturación, alta o anulación."""

    id_emisor: str
    num_serie: str
    fecha_expedicion: str  # dd-mm-yyyy, como en el registro

    def bloque(self) -> Contenido:
        return {
            "IDEmisorFactura": self.id_emisor,
            "NumSerieFactura": self.num_serie,
            "FechaExpedicionFactura": self.fecha_expedicion,
        }


@dataclass(frozen=True, slots=True)
class RegistroConHuella:
    """`IDFacturaExpedidaHuellaType`: un registro de facturación con su huella."""

    factura: IdFactura
    huella: str

    def bloque(self) -> Contenido:
        return self.factura.bloque() | {"Huella": self.huella}


@dataclass(frozen=True, slots=True)
class EventoReferido:
    """`RegEventoType`: un evento identificado por su tipo, su fecha y su huella."""

    tipo_evento: str
    fecha_hora_huso_gen: str
    huella: str

    def bloque(self) -> Contenido:
        return {
            "TipoEvento": self.tipo_evento,
            "FechaHoraHusoEvento": self.fecha_hora_huso_gen,
            "HuellaEvento": self.huella,
        }


@dataclass(frozen=True, slots=True)
class Recuentos:
    """Registros procesados en cada una de las cuatro comprobaciones (arts. 6.b, 6.d, 6.e, 7.h)."""

    huellas: int
    firmas: int
    cadena: int
    fechas: int


def _sumas(cuota: Decimal, importe: Decimal) -> Contenido:
    return {
        "SumaCuotaTotalAlta": format_amount(cuota),
        "SumaImporteTotalAlta": format_amount(importe),
    }


def lanzamiento(tipo: TipoEventoSif, recuentos: Recuentos) -> Contenido:
    """Datos propios del 03 (registros de facturación) o del 05 (registros de evento)."""
    if tipo is TipoEventoSif.LANZAMIENTO_ANOMALIAS_FACTURACION:
        grupo, sufijo, numero = (
            "LanzamientoProcesoDeteccionAnomaliasRegFacturacion",
            "RegFacturacion",
            "NumeroDeRegistrosFacturacionProcesadosSobre",
        )
    elif tipo is TipoEventoSif.LANZAMIENTO_ANOMALIAS_EVENTOS:
        grupo, sufijo, numero = (
            "LanzamientoProcesoDeteccionAnomaliasRegEvento",
            "RegEvento",
            "NumeroDeRegistrosEventoProcesadosSobre",
        )
    else:
        msg = f"El evento {tipo} no es de lanzamiento"
        raise ValueError(msg)
    datos: Contenido = {}
    for comprobacion, procesados in (
        ("IntegridadHuellas", recuentos.huellas),
        ("IntegridadFirmas", recuentos.firmas),
        ("TrazabilidadCadena", recuentos.cadena),
        ("TrazabilidadFechas", recuentos.fechas),
    ):
        datos[f"RealizadoProcesoSobre{comprobacion}{sufijo}"] = SI
        datos[f"{numero}{comprobacion}"] = str(procesados)
    return {grupo: datos}


def _otros(texto: str | None) -> Contenido:
    if not texto:
        return {}
    texto = texto.strip()
    if len(texto) > MAX_OTROS_DATOS:
        texto = texto[: MAX_OTROS_DATOS - 1] + "…"
    return {"OtrosDatosAnomalia": texto}


def anomalia_facturacion(
    tipo: TipoAnomalia, *, descripcion: str | None, factura: IdFactura | None
) -> Contenido:
    datos: Contenido = {"TipoAnomalia": tipo.value} | _otros(descripcion)
    if factura is not None:
        datos["RegistroFacturacionAnomalo"] = factura.bloque()
    return {"DeteccionAnomaliasRegFacturacion": datos}


def anomalia_eventos(
    tipo: TipoAnomalia, *, descripcion: str | None, evento: EventoReferido | None
) -> Contenido:
    datos: Contenido = {"TipoAnomalia": tipo.value} | _otros(descripcion)
    if evento is not None:
        datos["RegEventoAnomalo"] = evento.bloque()
    return {"DeteccionAnomaliasRegEvento": datos}


def exportacion_facturacion(
    *,
    inicio: str,
    fin: str,
    inicial: RegistroConHuella,
    final: RegistroConHuella,
    altas: int,
    suma_cuota: Decimal,
    suma_importe: Decimal,
    anulaciones: int,
) -> Contenido:
    return {
        "ExportacionRegFacturacionPeriodo": {
            "FechaHoraHusoInicioPeriodoExport": inicio,
            "FechaHoraHusoFinPeriodoExport": fin,
            "RegistroFacturacionInicialPeriodo": inicial.bloque(),
            "RegistroFacturacionFinalPeriodo": final.bloque(),
            "NumeroDeRegistrosFacturacionAltaExportados": str(altas),
            **_sumas(suma_cuota, suma_importe),
            "NumeroDeRegistrosFacturacionAnulacionExportados": str(anulaciones),
            "RegistrosFacturacionExportadosDejanDeConservarse": NO,
        }
    }


def exportacion_eventos(
    *, inicio: str, fin: str, inicial: EventoReferido, final: EventoReferido, numero: int
) -> Contenido:
    return {
        "ExportacionRegEventoPeriodo": {
            "FechaHoraHusoInicioPeriodoExport": inicio,
            "FechaHoraHusoFinPeriodoExport": fin,
            "RegistroEventoInicialPeriodo": inicial.bloque(),
            "RegistroEventoFinalPeriodo": final.bloque(),
            "NumeroDeRegEventoExportados": str(numero),
            "RegEventoExportadosDejanDeConservarse": NO,
        }
    }


def resumen(
    *,
    eventos_por_tipo: Mapping[str, int],
    inicial: RegistroConHuella | None,
    final: RegistroConHuella | None,
    altas: int,
    suma_cuota: Decimal,
    suma_importe: Decimal,
    anulaciones: int,
) -> Contenido:
    """Resumen de eventos (art. 9.2). El esquema exige al menos un `TipoEvento`: sin eventos en el
    intervalo se informa el propio resumen con 0 (spec, «Edge Cases»)."""
    tipos = sorted(eventos_por_tipo.items()) or [(TipoEventoSif.RESUMEN.value, 0)]
    if len(tipos) > MAX_TIPOS_RESUMEN:  # pragma: no cover — hay 9 tipos posibles
        msg = "Demasiados tipos de evento para un resumen"
        raise ValueError(msg)
    datos: Contenido = {
        "TipoEvento": [{"TipoEvento": t, "NumeroDeEventos": str(n)} for t, n in tipos]
    }
    if inicial is not None and final is not None:
        datos["RegistroFacturacionInicialPeriodo"] = inicial.bloque()
        datos["RegistroFacturacionFinalPeriodo"] = final.bloque()
    datos |= {
        "NumeroDeRegistrosFacturacionAltaGenerados": str(altas),
        **_sumas(suma_cuota, suma_importe),
        "NumeroDeRegistrosFacturacionAnulacionGenerados": str(anulaciones),
    }
    return {"ResumenEventos": datos}


def campos_huella(
    *,
    sistema: SistemaInformatico,
    obligado: Obligado,
    tipo: TipoEventoSif | str,
    anterior: EventoAnterior | None,
    fecha_hora_huso_gen: str,
) -> CamposHuellaEvento:
    return CamposHuellaEvento(
        nif_sistema=sistema.nif,
        id_otro_sistema="",
        id_sistema=sistema.id_sistema,
        version=sistema.version,
        numero_instalacion=sistema.numero_instalacion,
        nif_obligado=obligado.nif,
        tipo_evento=str(tipo),
        huella_anterior=anterior.huella if anterior else "",
        fecha_hora_huso_gen=fecha_hora_huso_gen,
    )


def build_contenido_evento(
    *,
    sistema: SistemaInformatico,
    obligado: Obligado,
    tipo: TipoEventoSif,
    fecha_hora_huso_gen: str,
    datos_propios: Contenido | None,
    otros_datos: str | None,
    anterior: EventoAnterior | None,
    huella: str,
) -> Contenido:
    evento: Contenido = {
        "SistemaInformatico": sistema.bloque(),
        "ObligadoEmision": {"NombreRazon": obligado.nombre, "NIF": obligado.nif},
        "FechaHoraHusoGenEvento": fecha_hora_huso_gen,
        "TipoEvento": tipo.value,
    }
    if datos_propios:
        evento["DatosPropiosEvento"] = datos_propios
    if otros_datos:
        evento["OtrosDatosEvento"] = otros_datos[:MAX_OTROS_DATOS]
    evento["Encadenamiento"] = (
        {"PrimerEvento": SI}
        if anterior is None
        else {
            "EventoAnterior": {
                "TipoEvento": anterior.tipo_evento,
                "FechaHoraHusoGenEvento": anterior.fecha_hora_huso_gen,
                "HuellaEvento": anterior.huella,
            }
        }
    )
    evento |= {"TipoHuella": TIPO_HUELLA_SHA256, "HuellaEvento": huella}
    return {"IDVersion": ID_VERSION, "Evento": evento}

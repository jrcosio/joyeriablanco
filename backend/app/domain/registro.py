"""Contenido de los registros de facturación según F-1 (research R-3, R-4, R-4b).

F-1: AEAT, DsRegistroVeriFactu.xlsx v1.0 (28/10/2024), SHA-256 40ce191a…
- Hoja «2) D. Registro Facturación Alta» (filas 2–60) y hoja «3) D. Reg. Facturación Anulación».
- Hoja «5) Definición SistemaInformatico».
- Listas L2 (TipoFactura), L3 (TipoRectificativa), L8A (ClaveRegimen), L9 (Calificación),
  L12 (TipoHuella) y L15 (IDVersion).

El contenido se guarda en `registros_facturacion.contenido` (JSONB) con TODOS los valores como
texto, en el orden de F-1, y servirá para generar el XML en la feature 004. Los bloques que en el
XML se repiten (destinatarios, desglose, facturas rectificadas) van como listas.

Campos opcionales que esta feature no informa (R-3): RefExterna, Subsanacion, RechazoPrevio,
FacturaSimplificadaArt7273, FacturaSinIdentifDestinatarioArt61d, Macrodato,
EmitidaPorTerceroODestinatario, Tercero, Cupon, Impuesto (su ausencia equivale a IVA, F-3 §15.1),
OperacionExenta, BaseImponibleACoste, recargo de equivalencia, NumRegistroAcuerdoFacturacion,
IdAcuerdoSistemaInformatico y Signature (no VERI*FACTU: feature 004). En la anulación:
SinRegistroPrevio, RechazoPrevio y GeneradoPor (R-4b).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Final

from app.domain.huella import format_amount, format_date
from app.domain.importes import DesgloseTipo
from app.domain.tipos import TipoFactura, TipoIdentificacion

ID_VERSION: Final = "1.0"  # L15
TIPO_HUELLA_SHA256: Final = "01"  # L12
CALIFICACION_SUJETA_NO_EXENTA: Final = "S1"  # L9
# Primera fecha de expedición: entrada en vigor de la Orden HAC/1177/2024 (F-3 §3.1.3.1, 1152).
FECHA_MINIMA_EXPEDICION: Final = date(2024, 10, 28)
RECTIFICATIVA_POR_SUSTITUCION: Final = "S"  # L3
MAX_DESCRIPCION: Final = 500  # DescripcionOperacion, alfanumérico (500)

type Contenido = dict[str, object]


@dataclass(frozen=True, slots=True)
class Emisor:
    nif: str
    nombre: str


@dataclass(frozen=True, slots=True)
class Destinatario:
    """Copia del cliente al emitir. NIF español, o `IDOtro` para los tipos 02–06 de L7."""

    nombre: str
    identificacion_pais: str
    identificacion_tipo: str
    identificacion_numero: str

    def bloque(self) -> Contenido:
        if self.identificacion_tipo == TipoIdentificacion.NIF:
            return {"NombreRazon": self.nombre, "NIF": self.identificacion_numero}
        return {
            "NombreRazon": self.nombre,
            "IDOtro": {
                "CodigoPais": self.identificacion_pais,
                "IDType": self.identificacion_tipo,
                "ID": self.identificacion_numero,
            },
        }


@dataclass(frozen=True, slots=True)
class SistemaInformatico:
    """Bloque de F-1, hoja 5, a partir de `Settings.sif_*` (research R-5)."""

    nombre_razon: str
    nif: str
    nombre_sistema: str
    id_sistema: str
    version: str
    numero_instalacion: str
    tipo_uso_solo_verifactu: str = "N"  # el diseño admite las dos modalidades (constitución IV)
    tipo_uso_multi_ot: str = "N"
    indicador_multiples_ot: str = "N"  # un único obligado: el emisor

    def bloque(self) -> Contenido:
        return {
            "NombreRazon": self.nombre_razon,
            "NIF": self.nif,
            "NombreSistemaInformatico": self.nombre_sistema,
            "IdSistemaInformatico": self.id_sistema,
            "Version": self.version,
            "NumeroInstalacion": self.numero_instalacion,
            "TipoUsoPosibleSoloVerifactu": self.tipo_uso_solo_verifactu,
            "TipoUsoPosibleMultiOT": self.tipo_uso_multi_ot,
            "IndicadorMultiplesOT": self.indicador_multiples_ot,
        }

    @classmethod
    def from_bloque(cls, bloque: Contenido) -> "SistemaInformatico":
        return cls(
            nombre_razon=str(bloque["NombreRazon"]),
            nif=str(bloque["NIF"]),
            nombre_sistema=str(bloque["NombreSistemaInformatico"]),
            id_sistema=str(bloque["IdSistemaInformatico"]),
            version=str(bloque["Version"]),
            numero_instalacion=str(bloque["NumeroInstalacion"]),
            tipo_uso_solo_verifactu=str(bloque["TipoUsoPosibleSoloVerifactu"]),
            tipo_uso_multi_ot=str(bloque["TipoUsoPosibleMultiOT"]),
            indicador_multiples_ot=str(bloque["IndicadorMultiplesOT"]),
        )


@dataclass(frozen=True, slots=True)
class RegistroAnterior:
    """Bloque `Encadenamiento/RegistroAnterior`: del inmediato anterior, sea alta o anulación."""

    id_emisor: str
    num_serie: str
    fecha_expedicion: str  # dd-mm-yyyy, tal como figura en el registro anterior
    huella: str


@dataclass(frozen=True, slots=True)
class FacturaRectificada:
    """Factura que sustituye una rectificativa «S», con sus importes (F-9, opción 1)."""

    num_serie: str
    fecha_expedicion: date
    base: Decimal
    cuota: Decimal


@dataclass(frozen=True, slots=True)
class DatosAlta:
    emisor: Emisor
    num_serie: str
    fecha_expedicion: date
    tipo_factura: TipoFactura
    fecha_operacion: date | None
    descripcion: str
    destinatario: Destinatario
    clave_regimen: str
    desglose: tuple[DesgloseTipo, ...]
    cuota_total: Decimal
    importe_total: Decimal
    rectificada: FacturaRectificada | None


def _encadenamiento(anterior: RegistroAnterior | None) -> Contenido:
    if anterior is None:
        return {"PrimerRegistro": "S"}
    return {
        "RegistroAnterior": {
            "IDEmisorFactura": anterior.id_emisor,
            "NumSerieFactura": anterior.num_serie,
            "FechaExpedicionFactura": anterior.fecha_expedicion,
            "Huella": anterior.huella,
        }
    }


def _detalle(desglose: DesgloseTipo, clave_regimen: str) -> Contenido:
    return {
        "ClaveRegimen": clave_regimen,
        "CalificacionOperacion": CALIFICACION_SUJETA_NO_EXENTA,
        "TipoImpositivo": format_amount(desglose.tipo_iva),
        "BaseImponibleOimporteNoSujeto": format_amount(desglose.base),
        "CuotaRepercutida": format_amount(desglose.cuota),
    }


def build_contenido_alta(
    datos: DatosAlta,
    *,
    anterior: RegistroAnterior | None,
    sistema: SistemaInformatico,
    fecha_hora_huso_gen: str,
    huella: str,
) -> Contenido:
    contenido: Contenido = {
        "IDVersion": ID_VERSION,
        "IDFactura": {
            "IDEmisorFactura": datos.emisor.nif,
            "NumSerieFactura": datos.num_serie,
            "FechaExpedicionFactura": format_date(datos.fecha_expedicion),
        },
        "NombreRazonEmisor": datos.emisor.nombre,
        "TipoFactura": datos.tipo_factura.value,
    }
    if datos.rectificada is not None:
        # F-3 §3.1.3.3–6: TipoRectificativa obligatorio con R1–R5; ImporteRectificacion con «S».
        # FacturasRectificadas es opcional, pero el ROF (art. 15.4) exige identificarla.
        contenido["TipoRectificativa"] = RECTIFICATIVA_POR_SUSTITUCION
        contenido["FacturasRectificadas"] = {
            "IDFacturaRectificada": [
                {
                    "IDEmisorFactura": datos.emisor.nif,
                    "NumSerieFactura": datos.rectificada.num_serie,
                    "FechaExpedicionFactura": format_date(datos.rectificada.fecha_expedicion),
                }
            ]
        }
        contenido["ImporteRectificacion"] = {
            "BaseRectificada": format_amount(datos.rectificada.base),
            "CuotaRectificada": format_amount(datos.rectificada.cuota),
        }
    if datos.fecha_operacion is not None:
        contenido["FechaOperacion"] = format_date(datos.fecha_operacion)
    contenido |= {
        "DescripcionOperacion": datos.descripcion,
        "Destinatarios": {"IDDestinatario": [datos.destinatario.bloque()]},
        "Desglose": {"DetalleDesglose": [_detalle(d, datos.clave_regimen) for d in datos.desglose]},
        "CuotaTotal": format_amount(datos.cuota_total),
        "ImporteTotal": format_amount(datos.importe_total),
        "Encadenamiento": _encadenamiento(anterior),
        "SistemaInformatico": sistema.bloque(),
        "FechaHoraHusoGenRegistro": fecha_hora_huso_gen,
        "TipoHuella": TIPO_HUELLA_SHA256,
        "Huella": huella,
    }
    return contenido


def build_contenido_anulacion(
    *,
    emisor_nif: str,
    num_serie: str,
    fecha_expedicion: date,
    anterior: RegistroAnterior | None,
    sistema: SistemaInformatico,
    fecha_hora_huso_gen: str,
    huella: str,
) -> Contenido:
    return {
        "IDVersion": ID_VERSION,
        "IDFactura": {
            "IDEmisorFacturaAnulada": emisor_nif,
            "NumSerieFacturaAnulada": num_serie,
            "FechaExpedicionFacturaAnulada": format_date(fecha_expedicion),
        },
        "Encadenamiento": _encadenamiento(anterior),
        "SistemaInformatico": sistema.bloque(),
        "FechaHoraHusoGenRegistro": fecha_hora_huso_gen,
        "TipoHuella": TIPO_HUELLA_SHA256,
        "Huella": huella,
    }


def build_descripcion_operacion(
    descripciones: Sequence[str], *, num_rectificada: str | None = None
) -> str:
    """Descripción del objeto de la factura (FR-045): líneas unidas con «; », hasta 500."""
    partes = [d.strip() for d in descripciones if d.strip()]
    if not partes:
        if num_rectificada is None:
            msg = "Una factura sin líneas solo puede ser una devolución total"
            raise ValueError(msg)
        return f"Devolución total de la factura {num_rectificada}"
    texto = "; ".join(partes)
    if len(texto) > MAX_DESCRIPCION:
        texto = texto[: MAX_DESCRIPCION - 1] + "…"
    return texto

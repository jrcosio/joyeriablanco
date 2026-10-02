"""Enumeraciones de dominio compartidas por modelos, esquemas y servicios."""

from enum import StrEnum
from typing import Final


class Rol(StrEnum):
    ADMINISTRADOR = "administrador"
    EMPLEADO = "empleado"


class TipoCliente(StrEnum):
    PARTICULAR = "particular"
    EMPRESA = "empresa"


class TipoIdentificacion(StrEnum):
    """`NIF` o clave de la lista L7 de DsRegistroVeriFactu.xlsx v1.0 (spec F-2).

    El 07 ("No censado") no se guarda en la ficha: se decide al generar el registro de
    facturación (research R-20.1).
    """

    NIF = "NIF"
    NIF_IVA = "02"
    PASAPORTE = "03"
    DOCUMENTO_OFICIAL = "04"
    CERTIFICADO_RESIDENCIA = "05"
    OTRO_DOCUMENTO = "06"


class TipoEvento(StrEnum):
    ACCESO_CORRECTO = "acceso_correcto"
    ACCESO_FALLIDO = "acceso_fallido"
    ACCESO_BLOQUEADO = "acceso_bloqueado"
    ACCESO_LIMITADO = "acceso_limitado"
    CIERRE_SESION = "cierre_sesion"
    CONTRASENA_CAMBIADA = "contrasena_cambiada"
    CONTRASENA_RESTABLECIDA = "contrasena_restablecida"
    USUARIO_CREADO = "usuario_creado"
    USUARIO_ROL_CAMBIADO = "usuario_rol_cambiado"
    USUARIO_DESACTIVADO = "usuario_desactivado"
    USUARIO_REACTIVADO = "usuario_reactivado"
    USUARIO_ELIMINADO = "usuario_eliminado"
    CLIENTE_CREADO = "cliente_creado"
    CLIENTE_EDITADO = "cliente_editado"
    CLIENTE_DESACTIVADO = "cliente_desactivado"
    CLIENTE_REACTIVADO = "cliente_reactivado"
    CLIENTE_BORRADO = "cliente_borrado"
    # Facturación (feature 002, research R-15)
    BORRADOR_FACTURA_CREADO = "borrador_factura_creado"
    BORRADOR_FACTURA_EDITADO = "borrador_factura_editado"
    BORRADOR_FACTURA_ELIMINADO = "borrador_factura_eliminado"
    FACTURA_EMITIDA = "factura_emitida"
    FACTURA_ANULADA = "factura_anulada"
    FACTURA_RECTIFICADA = "factura_rectificada"
    CONFIGURACION_FACTURACION_CAMBIADA = "configuracion_facturacion_cambiada"
    CONTADOR_AJUSTADO = "contador_ajustado"
    CADENA_VERIFICADA = "cadena_verificada"
    CADENA_INCONSISTENTE = "cadena_inconsistente"


# ------------------------------------------------------------------------- facturación (002)


class Serie(StrEnum):
    """Series de facturas (constitución 2.2.0, «Numeración»; ROF art. 6.1.a, 2.º)."""

    ORDINARIA = "FAC"
    RECTIFICATIVA = "REC"


class TipoFactura(StrEnum):
    """Lista L2 de DsRegistroVeriFactu.xlsx v1.0 (research R-3, R-4). Solo las de esta feature."""

    COMPLETA = "F1"
    RECTIFICATIVA_DERECHO_ART80 = "R1"  # «Error fundado en derecho y Art. 80 Uno Dos y Seis LIVA»
    RECTIFICATIVA_RESTO = "R4"  # «Factura Rectificativa (Resto)»


class TipoRectificativa(StrEnum):
    """Lista L3 (research R-4). Esta feature solo emite rectificativas por sustitución."""

    SUSTITUCION = "S"


class CausaRectificacion(StrEnum):
    """Causa declarada al rectificar una factura entregada (FR-024; F-9 → R1 o R4)."""

    DEVOLUCION_O_PRECIO = "devolucion_o_precio"
    ERROR_DATOS = "error_datos"

    @property
    def tipo_factura(self) -> TipoFactura:
        return (
            TipoFactura.RECTIFICATIVA_DERECHO_ART80
            if self is CausaRectificacion.DEVOLUCION_O_PRECIO
            else TipoFactura.RECTIFICATIVA_RESTO
        )


# Texto de cada causa, el mismo que muestra la web (`lib/facturacion.ts`, CAUSAS_RECTIFICACION) y
# que imprime la rectificativa (003, FR-008, research R-6).
TEXTO_CAUSA_RECTIFICACION: Final[dict[CausaRectificacion, str]] = {
    CausaRectificacion.DEVOLUCION_O_PRECIO: (
        "Devolución, descuento o cambio de precio posterior a la venta, o IVA mal aplicado"
    ),
    CausaRectificacion.ERROR_DATOS: "Error en datos o importes de la factura",
}


class MotivoModificacion(StrEnum):
    """Motivo declarado al modificar o anular una factura emitida (FR-024, FR-025)."""

    NO_DEBIO_EMITIRSE = "no_debio_emitirse"
    FACTURA_ENTREGADA = "factura_entregada"


class TipoCorreccion(StrEnum):
    ANULACION = "anulacion"
    ANULACION_Y_REEMISION = "anulacion_y_reemision"
    RECTIFICACION_SUSTITUCION = "rectificacion_sustitucion"


class TipoRegistro(StrEnum):
    ALTA = "alta"
    ANULACION = "anulacion"


class Modalidad(StrEnum):
    """Modalidad (constitución IV): opción de configuración y campo de cada registro."""

    VERIFACTU = "verifactu"
    NO_VERIFACTU = "no_verifactu"


class EntornoAeat(StrEnum):
    """Entorno de la AEAT de la dirección de cotejo del QR (003, FR-017, research R-3)."""

    PRUEBAS = "pruebas"
    PRODUCCION = "produccion"


class EstadoRemision(StrEnum):
    """Estado de remisión a la AEAT. La remisión llega con la feature 004 (FR-030)."""

    PENDIENTE = "pendiente"


class EstadoFactura(StrEnum):
    """Estado de un documento en el listado. El de una emitida se deriva (research R-8)."""

    BORRADOR = "borrador"
    VIGENTE = "vigente"
    ANULADA = "anulada"
    RECTIFICADA = "rectificada"


# Lista L8A de DsRegistroVeriFactu.xlsx v1.0, hoja «6) Listas» (F-1): «01 Operación de régimen
# general». No se configura: la fija el sistema, salvo en el oro de inversión, que lleva la 04
# (`domain/exenciones.py`; research R-21 y R-23).
CLAVE_REGIMEN_GENERAL: Final = "01"


class OperacionIdempotente(StrEnum):
    """Ámbito de una `Idempotency-Key` (research R-18)."""

    EMITIR = "emitir"
    EMITIR_BORRADOR = "emitir_borrador"
    MODIFICAR = "modificar"
    ANULAR = "anular"


def sql_in(enum: type[StrEnum]) -> str:
    """Lista SQL `('a','b',…)` para restricciones CHECK a partir de una enumeración."""
    return "(" + ", ".join(f"'{m.value}'" for m in enum) + ")"

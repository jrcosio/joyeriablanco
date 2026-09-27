"""Enumeraciones de dominio compartidas por modelos, esquemas y servicios."""

from enum import StrEnum


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
    CLIENTE_CREADO = "cliente_creado"
    CLIENTE_EDITADO = "cliente_editado"
    CLIENTE_DESACTIVADO = "cliente_desactivado"
    CLIENTE_REACTIVADO = "cliente_reactivado"
    CLIENTE_BORRADO = "cliente_borrado"


def sql_in(enum: type[StrEnum]) -> str:
    """Lista SQL `('a','b',…)` para restricciones CHECK a partir de una enumeración."""
    return "(" + ", ".join(f"'{m.value}'" for m in enum) + ")"

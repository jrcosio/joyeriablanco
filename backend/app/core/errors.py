"""Errores de dominio y respuesta RFC 9457 `application/problem+json` (research R-13).

El catálogo de `type` coincide con `contracts/openapi.yaml`. Los mensajes están en español y nunca
incluyen detalles internos (FR-049).
"""

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, ClassVar

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

MEDIA_TYPE = "application/problem+json"


@dataclass(frozen=True, slots=True)
class CampoError:
    campo: str
    mensaje: str


class ProblemaError(Exception):
    """Error de negocio que se traduce a una respuesta RFC 9457."""

    status: ClassVar[int] = 400
    tipo: ClassVar[str] = "error"
    titulo: ClassVar[str] = "Error"
    detalle_por_defecto: ClassVar[str | None] = None

    def __init__(
        self,
        detalle: str | None = None,
        *,
        errores: Sequence[CampoError] = (),
        extra: Mapping[str, Any] | None = None,
    ) -> None:
        self.detalle = detalle if detalle is not None else self.detalle_por_defecto
        self.errores = list(errores)
        self.extra = dict(extra or {})
        super().__init__(self.detalle or self.titulo)

    def body(self) -> dict[str, Any]:
        cuerpo: dict[str, Any] = {
            "type": f"/problemas/{self.tipo}",
            "title": self.titulo,
            "status": self.status,
        }
        if self.detalle:
            cuerpo["detail"] = self.detalle
        if self.errores:
            cuerpo["errores"] = [{"campo": e.campo, "mensaje": e.mensaje} for e in self.errores]
        cuerpo.update(self.extra)
        return cuerpo


class DatosNoValidos(ProblemaError):
    status, tipo, titulo = 422, "validacion", "Datos no válidos"
    detalle_por_defecto = "Revisa los campos indicados."


class NoAutenticado(ProblemaError):
    status, tipo, titulo = 401, "no-autenticado", "Sesión no válida"
    detalle_por_defecto = "Tu sesión no es válida o ha caducado. Vuelve a identificarte."


class CredencialesNoValidas(ProblemaError):
    status, tipo, titulo = 401, "credenciales", "No se ha podido iniciar sesión"
    detalle_por_defecto = "Usuario o contraseña incorrectos."


class SinPermiso(ProblemaError):
    status, tipo, titulo = 403, "sin-permiso", "Acceso denegado"
    detalle_por_defecto = "No tienes permiso para realizar esta operación."


class CsrfNoValido(ProblemaError):
    status, tipo, titulo = 403, "csrf", "Petición rechazada"
    detalle_por_defecto = "La petición no es válida. Vuelve a identificarte."


class OrigenNoPermitido(ProblemaError):
    status, tipo, titulo = 403, "origen", "Petición rechazada"
    detalle_por_defecto = "Origen de la petición no permitido."


class ContrasenaTemporalPendiente(ProblemaError):
    status, tipo, titulo = 403, "contrasena-temporal", "Cambio de contraseña obligatorio"
    detalle_por_defecto = "Debes cambiar tu contraseña temporal antes de continuar."


class NoEncontrado(ProblemaError):
    status, tipo, titulo = 404, "no-encontrado", "No encontrado"
    detalle_por_defecto = "El recurso solicitado no existe."


class ConflictoVersion(ProblemaError):
    status, tipo, titulo = 409, "conflicto-version", "Datos desactualizados"
    detalle_por_defecto = "El cliente ha cambiado desde que lo abriste."


class Duplicado(ProblemaError):
    status, tipo, titulo = 409, "duplicado", "Ya existe"


class UltimoAdministrador(ProblemaError):
    status, tipo, titulo = 409, "ultimo-administrador", "Operación no permitida"
    detalle_por_defecto = "El sistema no puede quedarse sin ningún administrador activo."


class Autogestion(ProblemaError):
    status, tipo, titulo = 409, "autogestion", "Operación no permitida"
    detalle_por_defecto = "No puedes realizar esta operación sobre tu propia cuenta."


class UsuarioActivo(ProblemaError):
    status, tipo, titulo = 409, "usuario-activo", "No se puede eliminar"
    detalle_por_defecto = "Desactiva el usuario antes de eliminarlo."


class ClienteConDocumentos(ProblemaError):
    status, tipo, titulo = 409, "cliente-con-documentos", "No se puede borrar"
    detalle_por_defecto = (
        "El cliente tiene facturas o presupuestos. Desactívalo en lugar de borrarlo."
    )


# ------------------------------------------------------------------ facturación (002, R-14)


class EmisionNoDisponible(ProblemaError):
    """Falta el emisor o la modalidad. `extra={"faltan": [...]}` (FR-004)."""

    status, tipo, titulo = 409, "emision-no-disponible", "No se puede emitir"
    detalle_por_defecto = (
        "Faltan datos de la configuración de facturación. Un administrador debe completarlos."
    )


class ClienteNoFacturable(ProblemaError):
    """Cliente inactivo o sin domicilio completo. `extra={"faltan": [...]}` (FR-017)."""

    status, tipo, titulo = 422, "cliente-no-facturable", "El cliente no se puede facturar"
    detalle_por_defecto = "Completa los datos del cliente antes de emitir."


class FechaExpedicionNoValida(ProblemaError):
    status, tipo, titulo = 422, "fecha-expedicion", "Fecha de expedición no válida"


class TipoIvaSinConfirmar(ProblemaError):
    """IVA por defecto fuera de la lista oficial de hoy sin confirmar (research R-20).
    `extra={"tipos_oficiales": [...]}`."""

    status, tipo, titulo = 422, "tipo-iva-sin-confirmar", "Confirma el tipo de IVA"
    detalle_por_defecto = (
        "Ese tipo de IVA no está entre los que la AEAT admite hoy. Guárdalo solo si ha cambiado "
        "la ley: la AEAT podría rechazar los registros de las facturas hasta que lo admita."
    )


class FacturaNoModificable(ProblemaError):
    status, tipo, titulo = 409, "factura-no-modificable", "La factura no se puede corregir"
    detalle_por_defecto = (
        "Solo se puede corregir la factura vigente: esta ya está anulada o rectificada."
    )


class ContadorNoAjustable(ProblemaError):
    status, tipo, titulo = 409, "contador-no-ajustable", "Ajuste no permitido"
    detalle_por_defecto = (
        "El próximo número debe ser mayor que el que ya corresponde a la siguiente factura."
    )


class CadenaInconsistente(ProblemaError):
    status, tipo, titulo = 409, "cadena-inconsistente", "Registro de facturación bloqueado"
    detalle_por_defecto = (
        "La cadena de registros de facturación no supera la comprobación de integridad. "
        "No se ha emitido nada. Avisa al responsable técnico."
    )


class SinCambios(ProblemaError):
    status, tipo, titulo = 422, "sin-cambios", "No hay cambios"
    detalle_por_defecto = "La rectificativa sería idéntica a la factura vigente."


class ModalidadBloqueada(ProblemaError):
    status, tipo, titulo = 409, "modalidad-bloqueada", "Modalidad bloqueada"
    detalle_por_defecto = (
        "Ya hay registros de facturación: el cambio de modalidad llega con la remisión a la AEAT."
    )


class IdempotenciaConflicto(ProblemaError):
    status, tipo, titulo = 409, "idempotencia-conflicto", "Clave de operación reutilizada"
    detalle_por_defecto = "Esa clave de operación ya se usó en otra operación o documento."


class LimiteOrigen(ProblemaError):
    status, tipo, titulo = 429, "limite-origen", "Demasiados intentos"
    detalle_por_defecto = (
        "Demasiados intentos desde este equipo. Inténtalo de nuevo en unos minutos."
    )


# --------------------------------------------------------------------------- validación

_MENSAJES: dict[str, str] = {
    "missing": "Campo obligatorio.",
    "string_too_short": "Debe tener al menos {min_length} caracteres.",
    "string_too_long": "No puede superar {max_length} caracteres.",
    "string_pattern_mismatch": "Formato no válido.",
    "string_type": "Debe ser un texto.",
    "enum": "Valor no permitido.",
    "literal_error": "Valor no permitido.",
    "int_parsing": "Debe ser un número entero.",
    "int_type": "Debe ser un número entero.",
    "greater_than_equal": "Debe ser mayor o igual que {ge}.",
    "less_than_equal": "Debe ser menor o igual que {le}.",
    "uuid_parsing": "Identificador no válido.",
    "uuid_type": "Identificador no válido.",
    "datetime_parsing": "Fecha y hora no válidas.",
    "datetime_from_date_parsing": "Fecha y hora no válidas.",
    "bool_parsing": "Debe ser verdadero o falso.",
    "extra_forbidden": "Campo no permitido.",
    "json_invalid": "El cuerpo de la petición no es JSON válido.",
    "model_attributes_type": "Formato de datos no válido.",
    "dict_type": "Formato de datos no válido.",
    "too_short": "Faltan datos.",
}


def _mensaje(error: Mapping[str, Any]) -> str:
    tipo = str(error.get("type", ""))
    if tipo == "value_error":
        # Mensajes propios de los validadores (ya en español); quitamos el prefijo de pydantic.
        return str(error.get("msg", "Valor no válido.")).removeprefix("Value error, ")
    plantilla = _MENSAJES.get(tipo, "Valor no válido.")
    try:
        return plantilla.format(**(error.get("ctx") or {}))
    except (KeyError, IndexError):
        return plantilla


def _campo(loc: Sequence[Any]) -> str:
    partes = [str(p) for p in loc if p not in ("body", "query", "path", "header")]
    return ".".join(partes) or "peticion"


def errores_de_validacion(errores: Sequence[Mapping[str, Any]]) -> list[CampoError]:
    return [CampoError(_campo(e.get("loc", ())), _mensaje(e)) for e in errores]


# --------------------------------------------------------------------------- manejadores


def _respuesta(cuerpo: Mapping[str, Any], status: int) -> JSONResponse:
    return JSONResponse(dict(cuerpo), status_code=status, media_type=MEDIA_TYPE)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProblemaError)
    async def _problema(_: Request, exc: ProblemaError) -> JSONResponse:
        return _respuesta(exc.body(), exc.status)

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        problema = DatosNoValidos(errores=errores_de_validacion(exc.errors()))
        return _respuesta(problema.body(), problema.status)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            problema: ProblemaError = NoEncontrado()
            return _respuesta(problema.body(), 404)
        cuerpo = {
            "type": "/problemas/http",
            "title": "Petición no válida" if exc.status_code < 500 else "Error del servidor",
            "status": exc.status_code,
        }
        return _respuesta(cuerpo, exc.status_code)

    @app.exception_handler(Exception)
    async def _interno(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Error no controlado: %s", type(exc).__name__)
        cuerpo = {
            "type": "/problemas/interno",
            "title": "Error del servidor",
            "status": 500,
            "detail": "Se ha producido un error inesperado. Inténtalo de nuevo.",
        }
        return _respuesta(cuerpo, 500)

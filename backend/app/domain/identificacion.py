"""Identificación fiscal del cliente (FR-024 a FR-026).

Fuentes (spec F-1 a F-5, research R-20):
- Composición del NIF: RD 1065/2007, arts. 19, 20 y 22; Orden EHA/451/2008, arts. 2–5 (redacción
  de la Orden HAP/5/2016); Orden INT/2058/2008.
- Letra del DNI y del NIE: Ministerio del Interior y DGOJ (web oficial). El algoritmo del carácter
  de control de entidades y de los NIF K/L/M NO está publicado: se valida solo su estructura
  (decisión del responsable, 2026-09-27).
- Combinaciones país/tipo y tabla de estructuras NIF-IVA: AEAT, "Validaciones y errores
  VERI*FACTU" v1.2.2, apartado 3.1.3 punto 13 (p. 10) y nota (1) (pp. 17–18).
"""

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from app.core.errors import CampoError
from app.domain.paises import es_codigo_pais
from app.domain.tipos import TipoIdentificacion

LONGITUD_MAXIMA_ID: Final = 20  # IDOtro/ID: alfanumérico (20), DsRegistroVeriFactu.xlsx v1.0
_SEPARADORES: Final = re.compile(r"[\s\-./]")
_ALFANUMERICO: Final = re.compile(r"[0-9A-Z]+")
_LETRAS_DNI: Final = "TRWAGMYFPDXBNJZSQVHLCKE"
_PREFIJO_NIE: Final = {"X": "0", "Y": "1", "Z": "2"}


class ClaseNif(StrEnum):
    DNI = "dni"
    NIE = "nie"
    ENTIDAD = "entidad"  # personas jurídicas y entidades sin personalidad (A–W)
    ESPECIAL = "especial"  # K, L y M (RD 1065/2007, arts. 19.2 y 20.2)


_CLASES: Final = (
    (ClaseNif.DNI, re.compile(r"[0-9]{8}[A-Z]")),
    (ClaseNif.NIE, re.compile(r"[XYZ][0-9]{7}[A-Z]")),
    (ClaseNif.ENTIDAD, re.compile(r"[ABCDEFGHJNPQRSUVW][0-9]{7}[0-9A-Z]")),
    (ClaseNif.ESPECIAL, re.compile(r"[KLM][0-9A-Z]{7}[A-Z]")),
)


def normalize_identificacion(texto: str) -> str:
    """Mayúsculas y sin espacios, guiones, puntos ni barras (FR-026)."""
    return _SEPARADORES.sub("", texto).upper()


def classify_nif(nif: str) -> ClaseNif | None:
    for clase, patron in _CLASES:
        if patron.fullmatch(nif):
            return clase
    return None


def validate_nif(nif: str) -> str | None:
    """Devuelve el motivo de rechazo o `None` si el NIF (ya normalizado) es válido."""
    clase = classify_nif(nif)
    if clase is None:
        return "Formato de NIF no válido."
    if clase in (ClaseNif.DNI, ClaseNif.NIE):
        digitos = nif[:-1] if clase is ClaseNif.DNI else _PREFIJO_NIE[nif[0]] + nif[1:-1]
        if _LETRAS_DNI[int(digitos) % 23] != nif[-1]:
            return "La letra del NIF no es correcta."
    return None


# --------------------------------------------------------------------------- NIF-IVA


@dataclass(frozen=True, slots=True)
class EstructuraNifIva:
    prefijo: str
    longitudes: tuple[int, ...]
    numerico: bool
    sin_ceros_izquierda: bool = False


# Tabla "Estructura NIF-IVA" (nota 1 de Validaciones y errores v1.2.2), indexada por ISO 3166-1.
NIF_IVA_ESTRUCTURAS: Final[dict[str, EstructuraNifIva]] = {
    "DE": EstructuraNifIva("DE", (9,), numerico=True),
    "AT": EstructuraNifIva("AT", (9,), numerico=False),
    "BE": EstructuraNifIva("BE", (10,), numerico=True),
    "BG": EstructuraNifIva("BG", (9, 10), numerico=True),
    "CY": EstructuraNifIva("CY", (9,), numerico=False),
    "CZ": EstructuraNifIva("CZ", (8, 9, 10), numerico=True),
    "HR": EstructuraNifIva("HR", (11,), numerico=True),
    "DK": EstructuraNifIva("DK", (8,), numerico=True),
    "SK": EstructuraNifIva("SK", (10,), numerico=True),
    "SI": EstructuraNifIva("SI", (8,), numerico=True),
    "EE": EstructuraNifIva("EE", (9,), numerico=True),
    "FI": EstructuraNifIva("FI", (8,), numerico=True),
    "FR": EstructuraNifIva("FR", (11,), numerico=False),
    "GR": EstructuraNifIva("EL", (9,), numerico=True),
    "GB": EstructuraNifIva("XI", (5, 9, 12), numerico=False),  # Irlanda del Norte
    "NL": EstructuraNifIva("NL", (12,), numerico=False),
    "HU": EstructuraNifIva("HU", (8,), numerico=True),
    "IT": EstructuraNifIva("IT", (11,), numerico=True),
    "IE": EstructuraNifIva("IE", (8, 9), numerico=False),
    "LV": EstructuraNifIva("LV", (11,), numerico=True),
    "LT": EstructuraNifIva("LT", (9, 12), numerico=True),
    "LU": EstructuraNifIva("LU", (8,), numerico=True),
    "MT": EstructuraNifIva("MT", (8,), numerico=True),
    "PL": EstructuraNifIva("PL", (10,), numerico=True),
    "PT": EstructuraNifIva("PT", (9,), numerico=True),
    "SE": EstructuraNifIva("SE", (12,), numerico=True),
    "RO": EstructuraNifIva("RO", tuple(range(2, 11)), numerico=True, sin_ceros_izquierda=True),
}


def validate_nif_iva(pais: str, numero: str) -> str:
    """Valida la estructura oficial y devuelve la forma canónica (prefijo + número).

    Lanza `ValueError` con el motivo si no es válido.
    """
    estructura = NIF_IVA_ESTRUCTURAS.get(pais.upper())
    if estructura is None:
        msg = "El NIF-IVA solo se admite para Estados de la UE (e Irlanda del Norte)."
        raise ValueError(msg)
    normalizado = normalize_identificacion(numero)
    cuerpo = normalizado.removeprefix(estructura.prefijo)
    tipo_caracteres = "numéricos" if estructura.numerico else "alfanuméricos"
    longitudes = " o ".join(str(n) for n in estructura.longitudes)
    if len(estructura.longitudes) > 3:
        longitudes = f"de {estructura.longitudes[0]} a {estructura.longitudes[-1]}"
    motivo = (
        f"NIF-IVA no válido: tras el prefijo {estructura.prefijo} debe tener "
        f"{longitudes} caracteres {tipo_caracteres}."
    )
    if len(cuerpo) not in estructura.longitudes:
        raise ValueError(motivo)
    if estructura.numerico and not (cuerpo.isascii() and cuerpo.isdigit()):
        raise ValueError(motivo)
    if not estructura.numerico and not _ALFANUMERICO.fullmatch(cuerpo):
        raise ValueError(motivo)
    if estructura.sin_ceros_izquierda and cuerpo.startswith("0"):
        msg = "NIF-IVA no válido: no puede empezar por cero tras el prefijo."
        raise ValueError(msg)
    return estructura.prefijo + cuerpo


# --------------------------------------------------------------------------- combinaciones

_EXTRANJEROS: Final = (
    TipoIdentificacion.PASAPORTE,
    TipoIdentificacion.DOCUMENTO_OFICIAL,
    TipoIdentificacion.CERTIFICADO_RESIDENCIA,
    TipoIdentificacion.OTRO_DOCUMENTO,
)


def allowed_identificacion_tipos(pais: str) -> tuple[TipoIdentificacion, ...]:
    """Tipos admitidos según el país (Validaciones y errores v1.2.2, p. 10)."""
    pais = pais.upper()
    if pais == "ES":
        return (TipoIdentificacion.NIF, TipoIdentificacion.PASAPORTE)
    if pais in NIF_IVA_ESTRUCTURAS:
        return (TipoIdentificacion.NIF_IVA, *_EXTRANJEROS)
    return _EXTRANJEROS


def validate_identificacion(
    pais: str, tipo: TipoIdentificacion, numero: str
) -> tuple[str, list[CampoError]]:
    """Normaliza y valida una identificación completa; devuelve (canónica, errores por campo)."""
    pais = pais.upper()
    if not es_codigo_pais(pais):
        return numero, [CampoError("identificacion_pais", "País no válido.")]
    if tipo not in allowed_identificacion_tipos(pais):
        motivo = "Tipo de identificación no admitido para este país."
        return numero, [CampoError("identificacion_tipo", motivo)]

    normalizado = normalize_identificacion(numero)
    campo = "identificacion_numero"
    if not normalizado:
        return normalizado, [CampoError(campo, "Campo obligatorio.")]
    if tipo is TipoIdentificacion.NIF:
        motivo_nif = validate_nif(normalizado)
        return normalizado, [CampoError(campo, motivo_nif)] if motivo_nif else []
    if tipo is TipoIdentificacion.NIF_IVA:
        try:
            return validate_nif_iva(pais, normalizado), []
        except ValueError as exc:
            return normalizado, [CampoError(campo, str(exc))]
    if len(normalizado) > LONGITUD_MAXIMA_ID:
        return normalizado, [
            CampoError(campo, f"No puede superar {LONGITUD_MAXIMA_ID} caracteres.")
        ]
    if not _ALFANUMERICO.fullmatch(normalizado):
        return normalizado, [CampoError(campo, "Solo se admiten letras sin tildes y números.")]
    return normalizado, []

"""Formato en español de los documentos impresos (003, FR-006, research R-6).

Funciones puras, sin `locale` del sistema ni `float`. Las cadenas coinciden con las de la web
(`lib/dinero.ts`, `lib/facturacion.ts` y `lib/fechas.ts`):
- Euros con separador de miles «.», coma decimal y espacio duro antes de «€» («1.560,90 €»), como
  `Intl.NumberFormat('es-ES', {style: 'currency', useGrouping: 'always'})`.
- Porcentaje «21 %», «12,5 %».
- Fecha `DD/MM/AAAA` e IBAN en grupos de cuatro.

Las unidades siguen FR-006: decimales solo si los tienen («2», «1,50»).
"""

import gettext
import re
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from typing import Final
from zoneinfo import ZoneInfo

import pycountry

NBSP: Final = " "
ZONA_MADRID: Final = ZoneInfo("Europe/Madrid")
_CENTIMO: Final = Decimal("0.01")
_ESPACIOS: Final = re.compile(r"\s+")

MESES: Final = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)

# Etiquetas impresas de la identificación del destinatario: `NIF` o lista L7 de
# DsRegistroVeriFactu.xlsx v1.0 (las descripciones largas están en `services/catalogos.py`).
ETIQUETAS_IDENTIFICACION: Final = {
    "NIF": "NIF",
    "02": "NIF-IVA",
    "03": "Pasaporte",
    "04": "Documento oficial de identificación",
    "05": "Certificado de residencia",
    "06": "Otro documento probatorio",
}


def _exigir_decimal(valor: object) -> Decimal:
    if not isinstance(valor, Decimal):
        msg = f"Se esperaba Decimal, no {type(valor).__name__} (constitución II)"
        raise TypeError(msg)
    return valor


def _agrupar(entero: str) -> str:
    grupos: list[str] = []
    while len(entero) > 3:
        grupos.insert(0, entero[-3:])
        entero = entero[:-3]
    grupos.insert(0, entero)
    return ".".join(grupos)


def _numero(valor: Decimal, decimales: int) -> str:
    texto = format(valor.quantize(Decimal(1).scaleb(-decimales)), "f")
    signo = "-" if texto.startswith("-") else ""
    entero, _, fraccion = texto.lstrip("-").partition(".")
    resultado = signo + _agrupar(entero)
    return f"{resultado},{fraccion}" if fraccion else resultado


def format_euros(valor: Decimal) -> str:
    """«1.560,90 €». El importe debe tener como mucho dos decimales."""
    importe = _exigir_decimal(valor)
    if importe != importe.quantize(_CENTIMO):
        msg = f"El importe {importe} debe tener como mucho dos decimales"
        raise ValueError(msg)
    return f"{_numero(importe, 2)}{NBSP}€"


def format_unidades(valor: Decimal) -> str:
    """«2» si es entero; «1,50» si tiene decimales (FR-006)."""
    unidades = _exigir_decimal(valor)
    decimales = 0 if unidades == unidades.to_integral_value() else 2
    return _numero(unidades, decimales)


def format_porcentaje(valor: Decimal) -> str:
    """«21 %», «10,5 %» (como `textoTipoIva` de la web)."""
    texto = format(_exigir_decimal(valor).quantize(_CENTIMO), "f")
    texto = texto.rstrip("0").rstrip(".") if "." in texto else texto
    return f"{texto.replace('.', ',')} %"


def format_fecha(fecha: date) -> str:
    return fecha.strftime("%d/%m/%Y")


def format_fecha_hora(momento: datetime) -> str:
    """«01/10/2026 a las 18:42», en hora de Madrid."""
    local = momento.astimezone(ZONA_MADRID)
    return f"{local.strftime('%d/%m/%Y')} a las {local.strftime('%H:%M')}"


def format_iban(iban: str) -> str:
    compacto = _ESPACIOS.sub("", iban).upper()
    return " ".join(compacto[i : i + 4] for i in range(0, len(compacto), 4))


def nombre_mes(mes: int) -> str:
    return MESES[mes - 1]


@lru_cache(maxsize=1)
def _traduccion_paises() -> gettext.NullTranslations:
    return gettext.translation("iso3166-1", pycountry.LOCALES_DIR, languages=["es"], fallback=True)


def nombre_pais(codigo: str) -> str:
    """Nombre del país en español (datos iso-codes de pycountry), o el código si no se conoce."""
    pais = pycountry.countries.get(alpha_2=codigo.upper())
    if pais is None:
        return codigo
    return _traduccion_paises().gettext(str(pais.name))


def format_identificacion(tipo: str, pais: str, numero: str) -> str:
    """«NIF 52364897H» o «Pasaporte X1234567 (Francia)»: el país solo si no es España."""
    texto = f"{ETIQUETAS_IDENTIFICACION.get(tipo, tipo)} {numero}"
    return texto if pais.upper() == "ES" else f"{texto} ({nombre_pais(pais)})"

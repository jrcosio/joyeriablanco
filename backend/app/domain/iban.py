"""IBAN de la cuenta del emisor (ajuste de cierre de 002; FR-001, research R-22).

- Estructura de ISO 13616: código de país, dos dígitos de control y de 11 a 30 letras o cifras
  (de 15 a 34 caracteres en total).
- España: 24 caracteres, `ES`, los dos dígitos de control y los 20 del código cuenta cliente.
- Dígito de control ISO 7064 MOD 97-10: con los cuatro primeros caracteres al final y cada
  letra sustituida por su número (A = 10 … Z = 35), el resto de dividir entre 97 es 1.

La longitud de los demás países la publica el registro IBAN de SWIFT, que no se pudo descargar
(research R-22): para ellos basta la estructura y el dígito de control.
"""

import re
from typing import Final

_ESTRUCTURA: Final = re.compile(r"[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}")
_ESPACIOS: Final = re.compile(r"\s+")
LONGITUD_ES: Final = 24
LONGITUD_MAXIMA: Final = 34


def normalize_iban(texto: str) -> str:
    return _ESPACIOS.sub("", texto).upper()


def validate_iban(iban: str) -> str | None:
    """Motivo por el que el IBAN (ya normalizado) no es válido, o `None`."""
    if not _ESTRUCTURA.fullmatch(iban):
        return (
            "El IBAN empieza por el código del país y dos dígitos de control, y tiene entre 15 "
            "y 34 letras o cifras."
        )
    if iban.startswith("ES") and (len(iban) != LONGITUD_ES or not iban[2:].isdigit()):
        return "Un IBAN español tiene 24 caracteres: ES seguido de 22 cifras."
    reordenado = iban[4:] + iban[:4]
    if int("".join(str(int(caracter, 36)) for caracter in reordenado)) % 97 != 1:
        return "El dígito de control del IBAN no es correcto: revisa que esté bien escrito."
    return None

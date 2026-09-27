"""Política de contraseñas (FR-008, NIST SP 800-63B) y contraseñas temporales (FR-015).

- Entre 12 y 128 caracteres, sin reglas de composición.
- Se rechazan las que figuran en la lista de contraseñas comunes (research R-7) y las que
  contienen el nombre de usuario, sin distinguir mayúsculas.
"""

import secrets
from functools import lru_cache
from importlib import resources
from typing import Final

LONGITUD_MINIMA: Final = 12
LONGITUD_MAXIMA: Final = 128

# Sin caracteres ambiguos (0/O, 1/l/I) para dictarla en persona.
_ALFABETO_TEMPORAL: Final = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"


@lru_cache(maxsize=1)
def _contrasenas_comunes() -> frozenset[str]:
    texto = (resources.files("app.resources") / "contrasenas_comunes.txt").read_text("utf-8")
    return frozenset(
        linea.strip() for linea in texto.splitlines() if linea.strip() and not linea.startswith("#")
    )


def validate_password(contrasena: str, nombre_usuario: str | None = None) -> list[str]:
    """Devuelve los motivos de rechazo (vacío si la contraseña es válida)."""
    errores: list[str] = []
    if len(contrasena) < LONGITUD_MINIMA:
        errores.append(f"Debe tener al menos {LONGITUD_MINIMA} caracteres.")
    if len(contrasena) > LONGITUD_MAXIMA:
        errores.append(f"No puede superar {LONGITUD_MAXIMA} caracteres.")
    if contrasena.lower() in _contrasenas_comunes():
        errores.append("Es una contraseña demasiado común. Elige otra.")
    if nombre_usuario and nombre_usuario.lower() in contrasena.lower():
        errores.append("No puede contener tu nombre de usuario.")
    return errores


def generate_temporary_password() -> str:
    """16 caracteres aleatorios agrupados de 4 en 4 (p. ej. `aB3d-Ef5h-Jk7m-Np9q`)."""
    while True:
        caracteres = "".join(secrets.choice(_ALFABETO_TEMPORAL) for _ in range(16))
        temporal = "-".join(caracteres[i : i + 4] for i in range(0, 16, 4))
        if not validate_password(temporal):
            return temporal

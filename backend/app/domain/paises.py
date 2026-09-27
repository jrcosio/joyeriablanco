"""Países según ISO 3166-1 alfa-2 (pycountry, datos iso-codes)."""

from functools import lru_cache

import pycountry


@lru_cache(maxsize=1)
def codigos_pais() -> tuple[str, ...]:
    return tuple(sorted(str(pais.alpha_2) for pais in pycountry.countries))


def es_codigo_pais(codigo: str) -> bool:
    return codigo.upper() in codigos_pais()

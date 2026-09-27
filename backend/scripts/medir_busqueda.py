"""Mide SC-003 (p95 de búsquedas y filtros) y el tiempo de acceso sobre una API en marcha.

Uso (sobre la pila E2E con 10.000 clientes cargados):
    uv run python scripts/medir_busqueda.py --base http://localhost:8001 \\
        --origen http://localhost:5174 --usuario admin.demo --contrasena '...'
"""

import argparse
import itertools
import statistics
import time
from typing import Any

import httpx

TERMINOS = [
    "maria", "lopez", "garcia", "martin", "jose", "ana", "joyeria", "relojeria", "plateria",
    "granada", "malaga", "sevilla", "madrid", "cordoba", "marbella", "cadiz", "bilbao",
    "12", "345", "x1", "b12", "sl", "fernandez", "ruiz", "moreno",
]  # fmt: skip
FILTROS: list[dict[str, Any]] = [
    {},
    {"provincia": "29"},
    {"provincia": "18", "tipo": "empresa"},
    {"tipo": "particular"},
    {"estado": "todos"},
    {"estado": "inactivos"},
    {"orden": "recientes"},
    {"orden": "nombre_desc", "pagina": 3},
]


def consultas(total: int) -> list[dict[str, Any]]:
    combinaciones = itertools.cycle(
        [{**f, "q": t} for t in TERMINOS for f in FILTROS[:2]] + FILTROS
    )
    return [next(combinaciones) for _ in range(total)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://localhost:8001")
    parser.add_argument("--origen", default="http://localhost:5174")
    parser.add_argument("--usuario", default="admin.demo")
    parser.add_argument("--contrasena", required=True)
    parser.add_argument("--peticiones", type=int, default=100)
    args = parser.parse_args()

    with httpx.Client(base_url=args.base, headers={"Origin": args.origen}, timeout=30) as cliente:
        inicio = time.perf_counter()
        respuesta = cliente.post(
            "/api/v1/sesion", json={"nombre_usuario": args.usuario, "contrasena": args.contrasena}
        )
        respuesta.raise_for_status()
        acceso_ms = (time.perf_counter() - inicio) * 1000
        total = cliente.get("/api/v1/clientes", params={"estado": "todos"}).json()["total"]

        tiempos: list[float] = []
        for params in consultas(args.peticiones):
            inicio = time.perf_counter()
            cliente.get("/api/v1/clientes", params=params).raise_for_status()
            tiempos.append((time.perf_counter() - inicio) * 1000)

    p95 = statistics.quantiles(tiempos, n=100)[94]
    print(f"Clientes en la BD: {total}")  # noqa: T201
    print(f"Acceso (login con Argon2id): {acceso_ms:.0f} ms (objetivo < 1000 ms)")  # noqa: T201
    print(  # noqa: T201
        f"Búsquedas y filtros ({len(tiempos)}): mediana {statistics.median(tiempos):.0f} ms, "
        f"p95 {p95:.0f} ms, máx. {max(tiempos):.0f} ms (objetivo p95 < 1000 ms)"
    )


if __name__ == "__main__":
    main()

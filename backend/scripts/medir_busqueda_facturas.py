"""Mide SC-007 (p95 de búsquedas y filtros del listado de facturas) y el p95 de la emisión.

Uso, sobre la pila E2E con 20.000 facturas generadas por los servicios (encadenadas):
    docker compose --profile e2e exec -T api-e2e joyeria reiniciar-bd-e2e
    docker compose --profile e2e exec -T api-e2e joyeria cargar-datos-ejemplo \\
        --clientes 500 --facturas 20000 --contrasena-demo '...'
    uv run python scripts/medir_busqueda_facturas.py --base http://localhost:8001 \\
        --origen http://localhost:5174 --usuario admin.demo --contrasena '...'

Las emisiones de la medida son facturas reales de la BD de E2E (se añaden a la cadena).
"""

import argparse
import itertools
import random
import statistics
import time
import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

TERMINOS = [
    "maria", "lopez", "garcia", "martin", "jose", "ana", "joyeria", "relojeria", "plateria",
    "distribuciones", "fernandez", "ruiz", "moreno", "2026-00", "2026-01", "0042", "12", "345",
    "x1", "b1", "sl", "sa", "rec-", "fac-2026-19", "anillo",
]  # fmt: skip
FILTROS: list[dict[str, Any]] = [
    {},
    {"anio": "todos"},
    {"mes": 6},
    {"anio": "todos", "mes": 9},
    {"orden": "antiguas"},
    {"orden": "total_desc"},
    {"orden": "total_asc", "pagina": 5},
    {"anio": "todos", "orden": "recientes", "pagina": 40},
]


def consultas(total: int) -> list[dict[str, Any]]:
    combinaciones = itertools.cycle(
        [{**f, "q": t} for t in TERMINOS for f in FILTROS[:2]] + FILTROS
    )
    return [next(combinaciones) for _ in range(total)]


def p95(tiempos: list[float]) -> float:
    return statistics.quantiles(tiempos, n=100)[94]


def resumen(nombre: str, tiempos: list[float]) -> str:
    return (
        f"{nombre} ({len(tiempos)}): mediana {statistics.median(tiempos):.0f} ms, "
        f"p95 {p95(tiempos):.0f} ms, máx. {max(tiempos):.0f} ms (objetivo p95 < 1000 ms)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://localhost:8001")
    parser.add_argument("--origen", default="http://localhost:5174")
    parser.add_argument("--usuario", default="admin.demo")
    parser.add_argument("--contrasena", required=True)
    parser.add_argument("--peticiones", type=int, default=100)
    parser.add_argument("--emisiones", type=int, default=100)
    args = parser.parse_args()
    rng = random.Random(2026)  # noqa: S311 — datos de medida, no criptográficos

    with httpx.Client(base_url=args.base, headers={"Origin": args.origen}, timeout=30) as cliente:
        sesion = cliente.post(
            "/api/v1/sesion", json={"nombre_usuario": args.usuario, "contrasena": args.contrasena}
        )
        sesion.raise_for_status()
        cliente.headers["X-CSRF-Token"] = sesion.json()["csrf_token"]
        total = cliente.get("/api/v1/facturas", params={"anio": "todos"}).json()["total"]

        busquedas: list[float] = []
        for params in consultas(args.peticiones):
            inicio = time.perf_counter()
            cliente.get("/api/v1/facturas", params=params).raise_for_status()
            busquedas.append((time.perf_counter() - inicio) * 1000)

        activos = cliente.get(
            "/api/v1/clientes", params={"estado": "activos", "tamano": 100}
        ).json()["elementos"]
        # Los de ejemplo de España llevan domicilio completo (los extranjeros, no).
        facturables = [c for c in activos if c["identificacion_pais"] == "ES" and c["localidad"]]
        hoy = datetime.now(ZoneInfo("Europe/Madrid")).date().isoformat()
        emisiones: list[float] = []
        for _ in range(args.emisiones):
            cuerpo = {
                "fecha_expedicion": hoy,
                "cliente_id": rng.choice(facturables)["id"],
                "lineas": [
                    {
                        "unidades": "1",
                        "descripcion": "Anillo de medida",
                        "precio_unitario": f"{rng.randrange(10, 2000)}.00",
                    }
                ],
            }
            inicio = time.perf_counter()
            respuesta = cliente.post(
                "/api/v1/facturas", json=cuerpo, headers={"Idempotency-Key": str(uuid.uuid4())}
            )
            emisiones.append((time.perf_counter() - inicio) * 1000)
            if respuesta.status_code == 422:  # cliente sin domicilio: no cuenta
                emisiones.pop()
                continue
            respuesta.raise_for_status()

    print(f"Facturas y borradores en la BD: {total}")  # noqa: T201
    print(resumen("Búsquedas y cambios de filtro", busquedas))  # noqa: T201
    print(resumen("Emisiones", emisiones))  # noqa: T201


if __name__ == "__main__":
    main()

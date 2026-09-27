"""La API implementa exactamente el contrato `specs/001-cimientos-clientes/contracts/openapi.yaml`.

- Cada operación (ruta + método) del contrato existe en la aplicación y viceversa.
- El código de éxito (2xx) coincide. Los códigos de error de cada operación están documentados
  en el contrato, que es la referencia para los consumidores (FastAPI solo publica el de éxito
  y el 422).
"""

import re
from pathlib import Path
from typing import Any

import yaml

from app.main import create_app

CONTRATO = (
    Path(__file__).resolve().parents[3] / "specs/001-cimientos-clientes/contracts/openapi.yaml"
)
METODOS = {"get", "post", "put", "patch", "delete"}


def _normalizar(ruta: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", ruta)


def _operaciones(documento: dict[str, Any], prefijo: str) -> dict[tuple[str, str], set[str]]:
    operaciones: dict[tuple[str, str], set[str]] = {}
    for ruta, elementos in documento["paths"].items():
        for metodo, operacion in elementos.items():
            if metodo in METODOS:
                exitos = {c for c in operacion.get("responses", {}) if str(c).startswith("2")}
                operaciones[(_normalizar(prefijo + ruta), metodo)] = {str(c) for c in exitos}
    return operaciones


def test_la_api_implementa_exactamente_el_contrato() -> None:
    contrato = yaml.safe_load(CONTRATO.read_text(encoding="utf-8"))
    prefijo = contrato["servers"][0]["url"]  # /api
    esperadas = _operaciones(contrato, prefijo)
    reales = _operaciones(create_app().openapi(), "")

    assert set(reales) == set(esperadas), (
        f"Solo en la API: {sorted(set(reales) - set(esperadas))}; "
        f"solo en el contrato: {sorted(set(esperadas) - set(reales))}"
    )
    for operacion, exitos in esperadas.items():
        assert reales[operacion] == exitos, (
            f"{operacion}: API {reales[operacion]} ≠ contrato {exitos}"
        )

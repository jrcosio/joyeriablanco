"""La API implementa exactamente la unión de los contratos `specs/*/contracts/openapi.yaml`.

Cada feature es dueña de su contrato (research R-14 de 002):
- Cada operación (ruta + método) de algún contrato existe en la aplicación y viceversa.
- El código de éxito (2xx) coincide. Los códigos de error de cada operación están documentados
  en el contrato, que es la referencia para los consumidores (FastAPI solo publica el de éxito
  y el 422).
"""

import re
from pathlib import Path
from typing import Any

import yaml

from app.main import create_app

SPECS = Path(__file__).resolve().parents[3] / "specs"
CONTRATOS = sorted(SPECS.glob("*/contracts/openapi.yaml"))
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


def _contratos() -> dict[tuple[str, str], set[str]]:
    esperadas: dict[tuple[str, str], set[str]] = {}
    for fichero in CONTRATOS:
        contrato = yaml.safe_load(fichero.read_text(encoding="utf-8"))
        prefijo = contrato["servers"][0]["url"]  # /api
        propias = _operaciones(contrato, prefijo)
        repetidas = set(propias) & set(esperadas)
        assert not repetidas, f"{fichero}: operaciones ya definidas en otro contrato: {repetidas}"
        esperadas |= propias
    return esperadas


def test_hay_un_contrato_por_feature() -> None:
    assert [f.parents[1].name for f in CONTRATOS][:4] == [
        "001-cimientos-clientes",
        "002-facturas",
        "003-pdf-impresion",
        "005-presupuestos",
    ]


def test_la_api_implementa_exactamente_el_contrato() -> None:
    esperadas = _contratos()
    reales = _operaciones(create_app().openapi(), "")

    solo_en_api = set(reales) - set(esperadas)
    assert not solo_en_api, f"Operaciones sin contrato: {sorted(solo_en_api)}"
    solo_en_contrato = set(esperadas) - set(reales)
    assert not solo_en_contrato, f"Operaciones del contrato sin implementar: {solo_en_contrato}"
    for operacion, exitos in reales.items():
        assert exitos == esperadas[operacion], (
            f"{operacion}: API {exitos} ≠ contrato {esperadas[operacion]}"
        )

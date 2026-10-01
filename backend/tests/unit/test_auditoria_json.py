"""La auditoría guarda los importes como texto decimal exacto (FR-043, constitución II)."""

import json
from decimal import Decimal

from app.services.auditoria import diff, to_json


def test_decimal_como_texto_exacto() -> None:
    assert to_json(Decimal("1560.90")) == "1560.90"
    assert to_json(Decimal("0.10")) == "0.10"
    assert to_json({"total": Decimal("21.00")}) == {"total": "21.00"}


def test_el_diff_de_importes_no_usa_float() -> None:
    cambios = diff({"iva_por_defecto": Decimal("21.00")}, {"iva_por_defecto": Decimal("10.00")})

    assert cambios == {"iva_por_defecto": ["21.00", "10.00"]}
    assert "21.0," not in json.dumps(cambios)
